from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from typing import Any, Dict, List, Optional, Tuple

import httpx
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.entities import Champion, ChampionSnapshot, ItemSnapshot, PatchVersion, Rune
from app.seed_data import CHAMPION_SEED_DATA

CDRAGON_BASE = "https://raw.communitydragon.org"
SLOTS = ["Q", "W", "E", "R"]

# Tokens used to exclude secondary/non-damage calculations from primary spell damage curves
# (Note: shields, heals, summons, and alternate forms remain preserved inside _raw_spells.)
EXCLUDED_CALC_TOKENS = (
    "minion",
    "monster",
    "jungle",
    "heal",
    "shield",
    "slow",
    "stun",
    "root",
    "duration",
    "cap",
    "mana",
    "energy",
    "armor",
    "resist",
    "movespeed",
    "attackspeed",
    "reduction",
    "threshold",
)

PREFERRED_CALC_TOKENS = (
    "totaldamage",
    "calculateddamage",
    "damagecalc",
    "basedamage",
    "damage",
    "dmg",
)


def version_to_cdragon_branch(patch_version: str) -> str:
    """Converts a DDragon version like '16.23.1' to a CommunityDragon branch ('16.23')."""
    parts = patch_version.strip().split(".")
    if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
        return f"{parts[0]}.{parts[1]}"
    return "latest"


def _map_cdragon_stat(m_stat: Optional[int], m_stat_formula: Optional[int]) -> Optional[str]:
    """Maps CommunityDragon mStat and mStatFormula enums to CombatSimulator scaling keys."""
    stat_code = 0 if m_stat is None else int(m_stat)
    is_bonus = m_stat_formula == 2

    if stat_code == 0:
        return "ap"
    if stat_code == 1:
        return "armor"
    if stat_code == 2:
        return "bonus_ad" if is_bonus else "total_ad"
    if stat_code == 6:
        return "mr"
    if stat_code in (11, 12):
        return "bonus_hp"
    return None


def _slice_rank_values(values: List[Any], ranks: int) -> List[float]:
    """Slices ranks 1..N from Riot's 7-element [rank0, rank1..rank5, rank6] array."""
    if not values:
        return [0.0] * ranks
    nums = [round(float(v), 2) for v in values]
    if len(nums) >= 1 + ranks:
        sliced = nums[1 : 1 + ranks]
        if any(v != 0 for v in sliced):
            return sliced
    if len(nums) >= ranks:
        return nums[:ranks]
    return nums + [nums[-1]] * (ranks - len(nums))


def _pick_damage_calculation(calcs: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Selects the primary champion-damage formula from mSpellCalculations."""
    if not calcs:
        return None

    scored: List[Tuple[int, str, Dict[str, Any]]] = []
    for key, calc_obj in calcs.items():
        if not isinstance(calc_obj, dict):
            continue
        if calc_obj.get("__type") != "GameCalculation":
            continue
        parts = calc_obj.get("mFormulaParts") or []
        if not parts:
            continue

        kl = key.lower()
        if any(tok in kl for tok in EXCLUDED_CALC_TOKENS):
            continue

        score = 0
        for idx, pref in enumerate(PREFERRED_CALC_TOKENS):
            if pref in kl:
                score = 100 - idx * 10
                break
        if score == 0:
            score = 10
        scored.append((score, key, calc_obj))

    if not scored:
        return None
    scored.sort(key=lambda item: item[0], reverse=True)
    return scored[0][2]


def _extract_scaling_ratio(values: List[Any]) -> float:
    """Extracts a positive scaling ratio from a CDragon DataValues list."""
    if not values:
        return 0.0
    if len(values) > 1 and float(values[1]) > 0:
        return round(float(values[1]), 4)
    for v in values:
        fv = float(v)
        if fv > 0:
            return round(fv, 4)
    return 0.0


def _extract_numeric_signature(obj: Any, prefix: str = "", out: Optional[Dict[str, float]] = None) -> Dict[str, float]:
    """
    Flattens all numeric coefficients, per-rank arrays, and constants beneath
    mSpellCalculations (including damage, shields, heals, summons, and alternate forms).
    """
    if out is None:
        out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in ("__type", "mSimpleTooltipCalculationDisplay", "mDisplayAsPercent", "mPrecision"):
                continue
            next_p = f"{prefix}.{k}" if prefix else k
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                out[next_p] = round(float(v), 4)
            elif isinstance(v, (dict, list)):
                _extract_numeric_signature(v, next_p, out)
    elif isinstance(obj, list):
        for idx, item in enumerate(obj):
            next_p = f"{prefix}[{idx}]"
            if isinstance(item, (int, float)) and not isinstance(item, bool):
                out[next_p] = round(float(item), 4)
            elif isinstance(item, (dict, list)):
                _extract_numeric_signature(item, next_p, out)
    return out


def _extract_all_raw_spells(bin_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extracts full DataValues and mSpellCalculations numeric snapshots for ALL spells
    in bin.json (including Q/W/E/R, Passives, and alternate forms like Mega/Cougar/Hammer/AllOut)
    to power patch-agnostic diff detection.
    """
    raw_spells: Dict[str, Any] = {}
    for key, val in bin_data.items():
        if not isinstance(val, dict) or "mSpell" not in val:
            continue
        m_spell = val["mSpell"]
        if not isinstance(m_spell, dict):
            continue

        spell_name = key.split("/")[-1]
        dv_map: Dict[str, List[float]] = {}
        for dv in m_spell.get("DataValues") or []:
            name = dv.get("name") or dv.get("mName")
            vals = dv.get("values") or dv.get("mValues")
            if name and isinstance(vals, list) and vals:
                rounded = [round(float(x), 4) for x in vals[:7]]
                if any(x != 0.0 for x in rounded):
                    dv_map[str(name)] = rounded

        calc_map: Dict[str, Dict[str, float]] = {}
        for c_name, c_obj in (m_spell.get("mSpellCalculations") or {}).items():
            if isinstance(c_obj, dict):
                sig = _extract_numeric_signature(c_obj)
                if sig:
                    calc_map[str(c_name)] = sig

        if dv_map or calc_map:
            raw_spells[spell_name] = {
                "data_values": dv_map,
                "calculations": calc_map,
            }

    return raw_spells


class CDragonEnricherService:
    """
    Fetches CommunityDragon bin.json + champions/{id}.json with resilient retries to extract:
    - Exact Q/W/E/R base damage, cooldowns, mana costs, and scaling ratios,
    - Complete _raw_spells snapshots covering passives, shields, heals, summons, and alternate forms.
    """

    @staticmethod
    def _get_json_strict_branch(
        client: httpx.Client,
        branch: str,
        rel_path: str,
        max_retries: int = 3,
    ) -> Optional[Dict[str, Any]]:
        """
        Fetches from the exact patch branch (e.g., '16.22') with exponential backoff retries.
        Only falls back to 'latest' on a definitive HTTP 404 so transient errors never mix versions.
        """
        primary_url = f"{CDRAGON_BASE}/{branch}/{rel_path}"
        fallback_404 = False

        for attempt in range(max_retries):
            try:
                resp = client.get(primary_url)
                if resp.status_code == 200:
                    return resp.json()
                if resp.status_code == 404:
                    fallback_404 = True
                    break
            except Exception:
                pass
            if attempt < max_retries - 1:
                time.sleep(0.4 * (2**attempt))

        if fallback_404 and branch != "latest":
            latest_url = f"{CDRAGON_BASE}/latest/{rel_path}"
            for attempt in range(2):
                try:
                    resp = client.get(latest_url)
                    if resp.status_code == 200:
                        return resp.json()
                except Exception:
                    pass
                time.sleep(0.4)

        return None

    @staticmethod
    def parse_champion_bin(
        bin_data: Dict[str, Any],
        champion_key: str,
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Parses Q/W/E/R abilities and complete _raw_spells data from a champion bin.json payload."""
        root = next(
            (
                v
                for k, v in bin_data.items()
                if k.lower().endswith("/characterrecords/root") and isinstance(v, dict)
            ),
            {},
        )
        spell_names: List[str] = root.get("spellNames") or []
        if not spell_names:
            return {}

        lower_key_map = {k.lower(): k for k in bin_data.keys()}
        tags_set = set(tags or [])
        default_phys = bool(tags_set & {"Marksman", "Fighter", "Assassin"}) and "Mage" not in tags_set

        abilities: Dict[str, Any] = {}
        for idx, slot in enumerate(SLOTS):
            if idx >= len(spell_names):
                break

            raw_spell_ref = spell_names[idx]
            spell_short_name = raw_spell_ref.split("/")[-1]
            ranks = 3 if slot == "R" else 5

            matched_key = None
            target_suffix = f"/{spell_short_name.lower()}"
            for lk, orig_k in lower_key_map.items():
                if lk.endswith(target_suffix) and isinstance(bin_data.get(orig_k), dict):
                    if "mSpell" in bin_data[orig_k]:
                        matched_key = orig_k
                        break

            if not matched_key:
                continue

            m_spell = bin_data[matched_key]["mSpell"]

            # 1. Cooldown and mana cost from bin.json
            raw_cd = m_spell.get("cooldownTime") or []
            cooldown = _slice_rank_values(raw_cd, ranks)
            raw_mana = m_spell.get("mana") or []
            mana_cost = _slice_rank_values(raw_mana, ranks) if raw_mana else [0.0] * ranks

            # 2. DataValues and mEffectAmount lookup maps
            data_values: Dict[str, List[Any]] = {}
            for dv in m_spell.get("DataValues") or []:
                name = dv.get("name") or dv.get("mName")
                vals = dv.get("values") or dv.get("mValues")
                if name and isinstance(vals, list):
                    data_values[name.lower()] = vals

            if all(c <= 0 for c in cooldown):
                for cd_key in ("cooldown", "cooldowntime", "basecooldown"):
                    if cd_key in data_values:
                        cooldown = _slice_rank_values(data_values[cd_key], ranks)
                        break

            effect_amounts: List[List[Any]] = []
            for eff in m_spell.get("mEffectAmount") or []:
                if isinstance(eff, dict) and isinstance(eff.get("value"), list):
                    effect_amounts.append(eff["value"])

            # 3. Resolve primary damage calculation formula
            base_damage = [0.0] * ranks
            scaling: Dict[str, float] = {}
            calc_obj = _pick_damage_calculation(m_spell.get("mSpellCalculations") or {})

            if calc_obj:
                for part in calc_obj.get("mFormulaParts") or []:
                    ptype = part.get("__type", "")

                    if ptype == "NamedDataValueCalculationPart":
                        dv_name = str(part.get("mDataValue", "")).lower()
                        if dv_name in data_values:
                            vals = _slice_rank_values(data_values[dv_name], ranks)
                            base_damage = [round(a + b, 2) for a, b in zip(base_damage, vals)]

                    elif ptype == "EffectValueCalculationPart":
                        e_idx = int(part.get("mEffectIndex", 1)) - 1
                        if 0 <= e_idx < len(effect_amounts):
                            vals = _slice_rank_values(effect_amounts[e_idx], ranks)
                            base_damage = [round(a + b, 2) for a, b in zip(base_damage, vals)]

                    elif ptype == "NumberCalculationPart":
                        num = float(part.get("mNumber", 0.0))
                        if num > 0:
                            base_damage = [round(a + num, 2) for a in base_damage]

                    elif ptype == "StatByCoefficientCalculationPart":
                        stat_key = _map_cdragon_stat(part.get("mStat"), part.get("mStatFormula"))
                        coeff = round(float(part.get("mCoefficient", 0.0)), 4)
                        if stat_key and coeff > 0:
                            scaling[stat_key] = round(scaling.get(stat_key, 0.0) + coeff, 4)

                    elif ptype == "StatByNamedDataValueCalculationPart":
                        stat_key = _map_cdragon_stat(part.get("mStat"), part.get("mStatFormula"))
                        dv_name = str(part.get("mDataValue", "")).lower()
                        if stat_key and dv_name in data_values:
                            coeff = _extract_scaling_ratio(data_values[dv_name])
                            if coeff > 0:
                                scaling[stat_key] = round(scaling.get(stat_key, 0.0) + coeff, 4)

            # 4. Infer damage type from scalings and champion tags
            if "ap" in scaling and "total_ad" not in scaling and "bonus_ad" not in scaling:
                dmg_type = "magic"
            elif "total_ad" in scaling or "bonus_ad" in scaling:
                dmg_type = "physical"
            else:
                dmg_type = "physical" if default_phys else "magic"

            abilities[slot] = {
                "name": spell_short_name,
                "damage_type": dmg_type,
                "base_damage": base_damage,
                "cooldown": cooldown,
                "mana_cost": mana_cost,
                "scaling": scaling,
            }

        # Attach full numeric snapshot across all spells and alternate forms
        raw_spells = _extract_all_raw_spells(bin_data)
        if raw_spells:
            abilities["_raw_spells"] = raw_spells

        return abilities

    @classmethod
    def _merge_summary_spell_metadata(
        cls,
        summary_data: Optional[Dict[str, Any]],
        abilities: Dict[str, Any],
    ) -> None:
        """
        Merges exact cooldownCoefficients, costCoefficients (mana cost), and official
        spell names from CDragon's summary JSON (champions/{riot_id}.json).
        """
        if not summary_data or not abilities:
            return
        for sp in summary_data.get("spells") or []:
            slot = str(sp.get("spellKey", "")).upper()
            if slot not in abilities or not isinstance(abilities[slot], dict):
                continue
            ranks = 3 if slot == "R" else 5
            cds = [round(float(x), 2) for x in (sp.get("cooldownCoefficients") or [])[:ranks]]
            if cds and any(c > 0 for c in cds):
                abilities[slot]["cooldown"] = cds
            costs = [round(float(x), 2) for x in (sp.get("costCoefficients") or [])[:ranks]]
            if costs:
                abilities[slot]["mana_cost"] = costs
            if sp.get("name"):
                abilities[slot]["name"] = sp["name"]

    @classmethod
    def fetch_champion_abilities(
        cls,
        client: httpx.Client,
        branch: str,
        champion_key: str,
        tags: Optional[List[str]] = None,
        riot_id: Optional[int] = None,
    ) -> Tuple[str, Dict[str, Any], str]:
        """Downloads and merges bin.json + champions/{id}.json for a single champion."""
        champ_lower = champion_key.lower()
        bin_data = cls._get_json_strict_branch(
            client, branch, f"game/data/characters/{champ_lower}/{champ_lower}.bin.json"
        )
        if bin_data:
            parsed = cls.parse_champion_bin(bin_data, champion_key, tags=tags)
            if parsed:
                if riot_id:
                    summary_data = cls._get_json_strict_branch(
                        client,
                        branch,
                        f"plugins/rcp-be-lol-game-data/global/default/v1/champions/{riot_id}.json",
                    )
                    cls._merge_summary_spell_metadata(summary_data, parsed)
                return champion_key, parsed, "cdragon"

        fallback = CHAMPION_SEED_DATA.get(champion_key, {}).get("abilities", {})
        return champion_key, fallback, "seed" if fallback else "ddragon"

    @classmethod
    def enrich_patch_champions(
        cls,
        db: Session,
        patch_version: str,
        champion_keys: Optional[List[str]] = None,
        max_workers: int = 8,
        update_legacy_tables: bool = False,
        timeout: float = 20.0,
    ) -> Dict[str, int]:
        """Enriches ChampionSnapshot records for a patch version with CDragon ability math."""
        query = db.query(ChampionSnapshot).filter(ChampionSnapshot.patch_version == patch_version)
        if champion_keys:
            query = query.filter(ChampionSnapshot.champion_key.in_(champion_keys))
        snapshots = query.all()
        if not snapshots:
            return {"total": 0, "cdragon": 0, "fallback": 0}

        branch = version_to_cdragon_branch(patch_version)
        snap_map = {s.champion_key: s for s in snapshots}

        cdragon_ok = 0
        fallback_cnt = 0

        with httpx.Client(timeout=timeout) as client:
            with ThreadPoolExecutor(max_workers=max_workers) as pool:
                futures = {
                    pool.submit(
                        cls.fetch_champion_abilities,
                        client,
                        branch,
                        s.champion_key,
                        s.tags,
                        s.riot_id,
                    ): s.champion_key
                    for s in snapshots
                }

                for fut in as_completed(futures):
                    champ_key, abilities, source = fut.result()
                    snap = snap_map[champ_key]
                    if abilities:
                        snap.abilities = abilities
                        snap.abilities_source = source
                    if source == "cdragon":
                        cdragon_ok += 1
                    else:
                        fallback_cnt += 1

                    if update_legacy_tables and abilities:
                        legacy = db.query(Champion).filter(Champion.key == champ_key).first()
                        if legacy:
                            legacy.abilities = abilities

        db.commit()
        return {"total": len(snapshots), "cdragon": cdragon_ok, "fallback": fallback_cnt}

    @classmethod
    def enrich_patch_items_and_runes(
        cls,
        db: Session,
        patch_version: str,
        timeout: float = 25.0,
    ) -> Dict[str, int]:
        """
        Extracts exact engine values from CDragon items.cdtb.bin.json and perks.cdtb.bin.json:
        - Completed item passive numeric parameters (stored in stats['_passive_values']),
        - Rune script effect coefficients (stored in Rune.effect_values).
        """
        branch = version_to_cdragon_branch(patch_version)
        items_enriched = 0
        runes_enriched = 0

        with httpx.Client(timeout=timeout) as client:
            # 1. Item passive parameters (items.cdtb.bin.json)
            items_bin = cls._get_json_strict_branch(client, branch, "game/items.cdtb.bin.json")
            if items_bin:
                item_rows = (
                    db.query(ItemSnapshot)
                    .filter_by(patch_version=patch_version, is_completed=True)
                    .all()
                )
                for row in item_rows:
                    entry = items_bin.get(f"Items/{row.item_id}")
                    if not isinstance(entry, dict):
                        continue
                    dvs = entry.get("mDataValues") or []
                    pvals: Dict[str, float] = {}
                    for dv in dvs:
                        m_name = dv.get("mName")
                        m_val = dv.get("mValue")
                        if m_name and isinstance(m_val, (int, float)) and not isinstance(m_val, bool):
                            pvals[str(m_name)] = round(float(m_val), 4)
                    if pvals:
                        updated_stats = dict(row.stats or {})
                        updated_stats["_passive_values"] = pvals
                        row.stats = updated_stats
                        items_enriched += 1

            # 2. Rune engine coefficients (perks.cdtb.bin.json)
            perks_bin = cls._get_json_strict_branch(client, branch, "game/perks.cdtb.bin.json")
            if perks_bin:
                perk_map: Dict[int, Dict[str, float]] = {}
                for _, obj in perks_bin.items():
                    if not isinstance(obj, dict) or "mPerkId" not in obj:
                        continue
                    pid = int(obj["mPerkId"])
                    eff = (
                        ((obj.get("mScript") or {}).get("mSpellScriptData") or {}).get(
                            "mEffectAmount"
                        )
                    )
                    if isinstance(eff, dict):
                        cleaned = {
                            str(k): round(float(v), 4)
                            for k, v in eff.items()
                            if isinstance(v, (int, float)) and not isinstance(v, bool)
                        }
                        if cleaned:
                            perk_map[pid] = cleaned

                rune_rows = db.query(Rune).filter_by(patch_version=patch_version).all()
                for r in rune_rows:
                    if r.rune_id in perk_map:
                        r.effect_values = perk_map[r.rune_id]
                        runes_enriched += 1

        db.commit()
        return {"items_enriched": items_enriched, "runes_enriched": runes_enriched}


if __name__ == "__main__":
    session = SessionLocal()
    try:
        versions = session.query(PatchVersion).order_by(PatchVersion.is_latest.desc()).all()
        if not versions:
            print("⚠️ Please run DDragon sync first (python -m app.services.ddragon_sync).")
        for pv in versions:
            print(f"🐉 Starting CDragon full enrichment: Patch {pv.version}...")
            stats = CDragonEnricherService.enrich_patch_champions(
                db=session,
                patch_version=pv.version,
                update_legacy_tables=pv.is_latest,
            )
            ir_stats = CDragonEnricherService.enrich_patch_items_and_runes(
                db=session,
                patch_version=pv.version,
            )
            print(
                f"✅ Patch {pv.version}: Champions {stats['cdragon']}/{stats['total']} | "
                f"Item Passives: {ir_stats['items_enriched']} | Rune Values: {ir_stats['runes_enriched']}"
            )
    finally:
        session.close()
