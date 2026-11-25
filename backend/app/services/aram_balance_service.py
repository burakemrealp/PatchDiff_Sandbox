import json
import logging
from pathlib import Path
import re
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)

WIKI_CHAMPION_DATA_URL = "https://wiki.leagueoflegends.com/en-us/Module:ChampionData/data?action=raw"
ARAM_DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "aram_overrides.json"

ARAM_MODIFIER_DEFAULTS: Dict[str, Any] = {
    "dmg_dealt": 1.0,
    "dmg_taken": 1.0,
    "healing": 1.0,
    "shielding": 1.0,
    "ability_haste": 0.0,
    "total_as": 1.0,
    "tenacity": 1.0,
    "energyregen_mod": 1.0,
}

_ARAM_CACHE: Optional[Dict[str, Dict[str, Any]]] = None


def parse_wiki_aram_lua(raw_lua_text: str) -> Dict[str, Dict[str, Any]]:
    """
    Parses League of Legends official Wiki Module:ChampionData/data Lua table
    to extract exact champion-specific ARAM balance multipliers keyed by lowercase champion_key.
    """
    parsed: Dict[str, Dict[str, Any]] = {}
    champ_blocks = re.split(r'\n  \["[^"]+"\]\s*=\s*\{', raw_lua_text)[1:]
    for blk in champ_blocks:
        m_api = re.search(r'\["apiname"\]\s*=\s*"([^"]+)"', blk)
        if not m_api:
            continue
        apiname = m_api.group(1).strip()
        if not apiname:
            continue

        entry: Dict[str, Any] = {"champion_key": apiname, **ARAM_MODIFIER_DEFAULTS}
        m_aram = re.search(r'\["aram"\]\s*=\s*\{([^}]*)\}', blk)
        if m_aram:
            for kv in re.finditer(r'\["([^"]+)"\]\s*=\s*(-?[0-9]+(?:\.[0-9]+)?)', m_aram.group(1)):
                k = kv.group(1).strip()
                val = float(kv.group(2))
                if k in ARAM_MODIFIER_DEFAULTS:
                    entry[k] = round(val, 4)

        has_modifiers = (
            abs(float(entry["dmg_dealt"]) - 1.0) > 1e-4
            or abs(float(entry["dmg_taken"]) - 1.0) > 1e-4
            or abs(float(entry["healing"]) - 1.0) > 1e-4
            or abs(float(entry["shielding"]) - 1.0) > 1e-4
            or abs(float(entry["ability_haste"])) > 1e-4
            or abs(float(entry["total_as"]) - 1.0) > 1e-4
            or abs(float(entry["tenacity"]) - 1.0) > 1e-4
            or abs(float(entry["energyregen_mod"]) - 1.0) > 1e-4
        )
        entry["has_modifiers"] = has_modifiers
        parsed[apiname.lower()] = entry
    return parsed


class AramBalanceService:
    """
    Provides official champion-specific ARAM (Howling Abyss) balance multipliers
    (dmg_dealt, dmg_taken, healing, shielding, ability_haste, total_as, tenacity, energyregen_mod)
    backed by an offline-bundled JSON dataset refreshed cleanly during patch syncs.
    """

    @classmethod
    def _load_cache(cls) -> Dict[str, Dict[str, Any]]:
        global _ARAM_CACHE
        if _ARAM_CACHE is not None:
            return _ARAM_CACHE

        if ARAM_DATA_PATH.exists():
            try:
                raw = json.loads(ARAM_DATA_PATH.read_text(encoding="utf-8"))
                champions_map = raw.get("champions") if isinstance(raw, dict) else None
                if isinstance(champions_map, dict):
                    _ARAM_CACHE = {
                        str(k).lower(): v
                        for k, v in champions_map.items()
                        if isinstance(v, dict)
                    }
                    return _ARAM_CACHE
            except Exception as exc:
                logger.warning("Failed to read bundled ARAM overrides file: %s", exc)

        _ARAM_CACHE = {}
        return _ARAM_CACHE

    @classmethod
    def clear_cache(cls) -> None:
        global _ARAM_CACHE
        _ARAM_CACHE = None

    @classmethod
    def get_champion_aram_modifiers(cls, champion_key: str) -> Dict[str, Any]:
        """Returns normalized ARAM modifiers for the given champion_key (neutral 1.0 / 0.0 fallback)."""
        cache = cls._load_cache()
        rec = cache.get((champion_key or "").strip().lower())
        if not rec:
            return {
                "champion_key": champion_key,
                **ARAM_MODIFIER_DEFAULTS,
                "has_modifiers": False,
            }
        merged = {
            "champion_key": rec.get("champion_key", champion_key),
            **ARAM_MODIFIER_DEFAULTS,
        }
        for key in ARAM_MODIFIER_DEFAULTS:
            if key in rec and isinstance(rec[key], (int, float)):
                merged[key] = float(rec[key])
        merged["has_modifiers"] = bool(rec.get("has_modifiers", False))
        return merged

    @classmethod
    def refresh_aram_overrides_file(cls, timeout_sec: float = 12.0) -> Dict[str, Any]:
        """
        Fetches the latest official League Wiki ChampionData Lua module, extracts all champion
        ARAM modifiers, updates backend/app/data/aram_overrides.json, and refreshes RAM cache.
        """
        global _ARAM_CACHE
        try:
            with httpx.Client(
                timeout=timeout_sec,
                follow_redirects=True,
                headers={"User-Agent": "PatchDiffSandbox/2.0"},
            ) as client:
                resp = client.get(WIKI_CHAMPION_DATA_URL)
                resp.raise_for_status()
                champions_map = parse_wiki_aram_lua(resp.text)

            if len(champions_map) < 100:
                return {
                    "status": "offline_fallback",
                    "reason": f"Parsed only {len(champions_map)} champions; preserving existing bundle.",
                }

            ARAM_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "source": WIKI_CHAMPION_DATA_URL,
                "champions_count": len(champions_map),
                "overrides_count": sum(1 for v in champions_map.values() if v.get("has_modifiers")),
                "champions": champions_map,
            }
            ARAM_DATA_PATH.write_text(
                json.dumps(payload, indent=2, sort_keys=True),
                encoding="utf-8",
            )
            _ARAM_CACHE = champions_map
            return {
                "status": "refreshed",
                "champions_count": payload["champions_count"],
                "overrides_count": payload["overrides_count"],
            }
        except Exception as exc:
            logger.warning("ARAM override refresh skipped (using bundled data): %s", exc)
            return {
                "status": "offline_fallback",
                "reason": str(exc),
            }
