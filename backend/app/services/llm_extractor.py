import json
import re
import time
from typing import Dict, List, Optional, Tuple
import httpx

from app.core.config import settings
from app.schemas.patch_contracts import (
    PatchPayload,
    ChampionPatchDiff,
    StatDelta,
    StatName,
    AbilityDelta,
    AbilitySlot,
    DamageType,
    ScalingDelta,
    ScalingStat,
)
from app.services.normalizer import PatchNormalizer


SYSTEM_PROMPT = """
You are a senior League of Legends game engine and mathematical data engineer.
Your task is to parse raw patch note text into the EXACT REQUIRED JSON FORMAT with zero hallucination.

STRICT MATHEMATICAL RULES:
1. Always convert percentage scaling ratios into decimals (e.g., '90% -> 105%' or '%90 -> %105' becomes old_ratio: 0.90, new_ratio: 1.05).
2. Parse per-rank ability base damage arrays (e.g., 80/130/180/230/280) as float lists [80.0, 130.0, 180.0, 230.0, 280.0].
3. Expand scalar cooldowns (e.g., '7s -> 6.5s') into 5-element arrays [7.0, 7.0, 7.0, 7.0, 7.0] -> [6.5, 6.5, 6.5, 6.5, 6.5] (or 3 elements for R).
4. Only extract changes explicitly stated in the text; never invent or infer unmentioned stats.
5. Return ONLY a valid JSON object matching the schema with no extra commentary.
""".strip()


def turkish_lower(text: str) -> str:
    """Normalizes Turkish dotted/dotless uppercase letters (U+0130 / I) before calling .lower()."""
    return text.replace("İ", "i").replace("I", "ı").lower()


class PatchExtractorService:
    """
    Converts raw patch notes into a structured PatchPayload via a 2-layer architecture:
    Layer 1: Universal OpenAI-Compatible LLM API (Default: Groq LPU - <1s)
    Layer 2: Deterministic Math & Regex Parser (Offline Fallback - <5 ms)
    """

    @classmethod
    def extract_patch_payload(
        cls,
        raw_text: str,
        patch_version: str = "14.23",
        known_champions: Optional[Dict[str, str]] = None,
    ) -> Tuple[PatchPayload, str, float]:
        start_time = time.perf_counter()
        chunks = PatchNormalizer.split_by_champion(raw_text, known_champions=known_champions)

        if not chunks:
            elapsed = round((time.perf_counter() - start_time) * 1000, 1)
            return PatchPayload(patch_version=patch_version, champions=[]), "empty", elapsed

        provider = settings.LLM_PROVIDER.lower().strip()

        # Layer 1: Universal OpenAI-Compatible API (Groq / OpenAI / DeepSeek)
        if provider != "offline" and settings.LLM_API_KEY.strip():
            formatted_input = "\n\n".join(
                [f"### CHAMPION: {champ}\n{text}" for champ, text in chunks.items()]
            )
            try:
                payload = cls._call_openai_compatible(formatted_input, patch_version)
                elapsed = round((time.perf_counter() - start_time) * 1000, 1)
                engine_label = f"{provider} ({settings.LLM_MODEL.strip()})"
                print(f"⚡ [Layer 1] Parsed via {engine_label} in {elapsed} ms.")
                return payload, engine_label, elapsed
            except httpx.HTTPStatusError as exc:
                print(f"⚠️ LLM HTTP Error ({exc.response.status_code}): {exc.response.text}")
                print("⚙️ [Layer 2] Deterministic Math Parser activated!")
            except Exception as exc:
                print(f"⚠️ LLM API warning ({provider}): {exc}")
                print("⚙️ [Layer 2] Deterministic Math Parser activated!")

        # Layer 2: Deterministic Regex & Rule Engine (zero external dependencies)
        payload = cls._deterministic_fallback(chunks, patch_version)
        elapsed = round((time.perf_counter() - start_time) * 1000, 1)
        return payload, "deterministic-offline", elapsed

    @classmethod
    def _call_openai_compatible(cls, prompt_text: str, patch_version: str) -> PatchPayload:
        schema_json = json.dumps(PatchPayload.model_json_schema(), ensure_ascii=False)
        url = f"{settings.LLM_BASE_URL.strip().rstrip('/')}/chat/completions"

        headers = {
            "Authorization": f"Bearer {settings.LLM_API_KEY.strip()}",
            "Content-Type": "application/json",
        }
        body = {
            "model": settings.LLM_MODEL.strip(),
            "temperature": 0.0,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": f"{SYSTEM_PROMPT}\n\nStrict JSON Schema:\n{schema_json}",
                },
                {
                    "role": "user",
                    "content": f"Patch Version: {patch_version}\n\n{prompt_text}",
                },
            ],
        }

        with httpx.Client(timeout=settings.LLM_TIMEOUT_SECONDS) as client:
            resp = client.post(url, headers=headers, json=body)
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            return PatchPayload.model_validate_json(content)

    @classmethod
    def _deterministic_fallback(cls, chunks: Dict[str, str], patch_version: str) -> PatchPayload:
        """Deterministically parses numeric 'old -> new' transitions from bilingual (EN/TR) patch notes."""
        champions_list: List[ChampionPatchDiff] = []

        # Bilingual stat keywords (check longer/more specific phrases first via ordering)
        stat_mapping = {
            "base armor": StatName.BASE_ARMOR,
            "taban zırh": StatName.BASE_ARMOR,
            "armor": StatName.BASE_ARMOR,
            "zırh": StatName.BASE_ARMOR,
            "base attack damage": StatName.BASE_AD,
            "taban saldırı gücü": StatName.BASE_AD,
            "attack damage": StatName.BASE_AD,
            "saldırı gücü": StatName.BASE_AD,
            "base health": StatName.BASE_HP,
            "taban can": StatName.BASE_HP,
            "magic resist": StatName.BASE_MR,
            "büyü direnci": StatName.BASE_MR,
            "movement speed": StatName.MOVE_SPEED,
            "move speed": StatName.MOVE_SPEED,
            "hareket hızı": StatName.MOVE_SPEED,
        }

        for champ_key, block in chunks.items():
            stat_deltas: List[StatDelta] = []
            ability_map: Dict[AbilitySlot, AbilityDelta] = {}
            summary_lines: List[str] = []

            for line in block.splitlines():
                lower_line = turkish_lower(line)

                if "->" not in line:
                    summary_lines.append(line)
                    continue

                ability_match = re.match(r"^([QWERP])\s*[-:]\s*(.+)$", line, flags=re.IGNORECASE)
                if ability_match:
                    slot_char = ability_match.group(1).upper()
                    slot_enum = AbilitySlot(slot_char)
                    rest = ability_match.group(2)

                    if slot_enum not in ability_map:
                        name_part = rest.split(":")[0].strip() if ":" in rest else f"{slot_char} Ability"
                        dmg_type = DamageType.PHYSICAL if champ_key in ["Zed", "Jinx"] else DamageType.MAGIC
                        ability_map[slot_enum] = AbilityDelta(
                            slot=slot_enum,
                            ability_name=name_part,
                            damage_type=dmg_type,
                        )

                    ab_obj = ability_map[slot_enum]

                    arr_match = re.search(
                        r"(\d+(?:\.\d+)?(?:/\d+(?:\.\d+)?)+)\s*->\s*(\d+(?:\.\d+)?(?:/\d+(?:\.\d+)?)+)",
                        rest,
                    )
                    if arr_match:
                        ab_obj.old_base_damage = [float(x) for x in arr_match.group(1).split("/")]
                        ab_obj.new_base_damage = [float(x) for x in arr_match.group(2).split("/")]
                        continue

                    if "ratio" in lower_line or "oran" in lower_line or "ap" in lower_line or "ad" in lower_line or "sg" in lower_line or "%" in lower_line:
                        pct_prefix_match = re.search(r"%(\d+(?:\.\d+)?)\s*->\s*%(\d+(?:\.\d+)?)", rest)
                        pct_suffix_match = re.search(r"(\d+(?:\.\d+)?)%\s*->\s*(\d+(?:\.\d+)?)%", rest)
                        dec_match = re.search(r"(\d+\.\d+)\s*->\s*(\d+\.\d+)", rest)

                        old_r, new_r = 0.0, 0.0
                        if pct_prefix_match:
                            old_r = round(float(pct_prefix_match.group(1)) / 100.0, 4)
                            new_r = round(float(pct_prefix_match.group(2)) / 100.0, 4)
                        elif pct_suffix_match:
                            old_r = round(float(pct_suffix_match.group(1)) / 100.0, 4)
                            new_r = round(float(pct_suffix_match.group(2)) / 100.0, 4)
                        elif dec_match:
                            old_r = float(dec_match.group(1))
                            new_r = float(dec_match.group(2))

                        if old_r or new_r:
                            stat_type = ScalingStat.AP
                            if "ilave sg" in lower_line or "bonus ad" in lower_line:
                                stat_type = ScalingStat.BONUS_AD
                            elif "toplam sg" in lower_line or "total ad" in lower_line or "sg" in lower_line:
                                stat_type = ScalingStat.TOTAL_AD

                            ab_obj.scaling_changes.append(
                                ScalingDelta(scaling_stat=stat_type, old_ratio=old_r, new_ratio=new_r)
                            )
                        continue

                    if "cooldown" in lower_line or "bekleme" in lower_line or "second" in lower_line or "sec" in lower_line or "saniye" in lower_line:
                        cd_match = re.search(
                            r"(\d+(?:\.\d+)?)\s*(?:seconds|second|saniye|sec|sn|s)?\s*->\s*(\d+(?:\.\d+)?)",
                            rest,
                            flags=re.IGNORECASE,
                        )
                        if cd_match:
                            old_cd = float(cd_match.group(1))
                            new_cd = float(cd_match.group(2))
                            ranks = 3 if slot_enum == AbilitySlot.R else 5
                            ab_obj.old_cooldown = [old_cd] * ranks
                            ab_obj.new_cooldown = [new_cd] * ranks
                        continue

                num_match = re.search(r"(\d+(?:\.\d+)?)\s*->\s*(\d+(?:\.\d+)?)", line)
                if num_match:
                    old_val = float(num_match.group(1))
                    new_val = float(num_match.group(2))
                    matched_stat = None
                    for keyword, st_enum in stat_mapping.items():
                        if keyword in lower_line:
                            matched_stat = st_enum
                            break

                    if matched_stat:
                        stat_deltas.append(
                            StatDelta(stat_name=matched_stat, old_value=old_val, new_value=new_val)
                        )

            final_abilities = [
                AbilityDelta.model_validate(ab.model_dump()) for ab in ability_map.values()
            ]

            champions_list.append(
                ChampionPatchDiff(
                    champion_key=champ_key,
                    summary=" ".join(summary_lines) if summary_lines else f"{champ_key} patch adjustments.",
                    stat_deltas=stat_deltas,
                    ability_deltas=final_abilities,
                )
            )

        return PatchPayload(patch_version=patch_version, champions=champions_list)
