import re
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import Base, SessionLocal, engine
from app.core.versioning import build_item_icon_url
from app.models.entities import (
    Champion,
    ChampionSnapshot,
    Item,
    ItemSnapshot,
    PatchVersion,
    Rune,
)
from app.seed_data import CHAMPION_SEED_DATA

DDRAGON_BASE = "https://ddragon.leagueoflegends.com"
VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")

DDRAGON_STAT_MAP = {
    "FlatHPPoolMod": "hp",
    "FlatMPPoolMod": "mana",
    "FlatPhysicalDamageMod": "ad",
    "FlatMagicDamageMod": "ap",
    "FlatArmorMod": "armor",
    "FlatSpellBlockMod": "mr",
    "PercentAttackSpeedMod": "attack_speed",
    "FlatCritChanceMod": "crit_chance",
    "PercentLifeStealMod": "lifesteal",
    "FlatMovementSpeedMod": "move_speed",
    "PercentMovementSpeedMod": "move_speed_percent",
}


def _strip_html(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"[ \t]+", " ", text).strip()


def _turkish_lower(text: str) -> str:
    """Normalizes Turkish dotted/dotless uppercase letters (U+0130 / I) before calling .lower()."""
    return text.replace("İ", "i").replace("I", "ı").lower()


class DDragonSyncService:
    """
    Detects the latest League of Legends patches from Riot Data Dragon CDN and persists
    versioned snapshots for all champions, items, and runes into PostgreSQL.
    """

    @staticmethod
    def _get_json_with_retry(
        client: httpx.Client, url: str, max_retries: int = 3
    ) -> Any:
        last_exc: Optional[Exception] = None
        for attempt in range(max_retries):
            try:
                resp = client.get(url)
                resp.raise_for_status()
                return resp.json()
            except Exception as exc:
                last_exc = exc
                if attempt < max_retries - 1:
                    time.sleep(0.5 * (2**attempt))
        raise RuntimeError(f"DDragon request failed after {max_retries} attempts: {url}") from last_exc

    @classmethod
    def fetch_latest_versions(cls, count: int = 2, timeout: float = 10.0) -> List[str]:
        url = f"{DDRAGON_BASE}/api/versions.json"
        with httpx.Client(timeout=timeout) as client:
            all_versions: List[str] = cls._get_json_with_retry(client, url)

        valid = [v for v in all_versions if VERSION_PATTERN.match(v)]
        return valid[:count]

    @staticmethod
    def parse_item_stats(raw_item: Dict[str, Any]) -> Dict[str, float]:
        """Extracts normalized combat stats from DDragon item['stats'] and HTML <stats> blocks (TR & EN)."""
        parsed: Dict[str, float] = {}

        # 1. Direct JSON stats mapping
        raw_stats = raw_item.get("stats") or {}
        for dd_key, engine_key in DDRAGON_STAT_MAP.items():
            val = raw_stats.get(dd_key)
            if val is not None and float(val) != 0.0:
                parsed[engine_key] = round(float(val), 4)

        # 2. Extended stats inside HTML <stats>...</stats> tags (Ability Haste, Lethality, Pen, Crit Dmg, etc.)
        description = raw_item.get("description") or ""
        stats_match = re.search(r"<stats>(.*?)</stats>", description, flags=re.IGNORECASE | re.DOTALL)
        if stats_match:
            stats_html = stats_match.group(1)
            entries = re.split(r"<br\s*/?>", stats_html, flags=re.IGNORECASE)
            for entry in entries:
                att_match = re.search(r"<attention>\s*([^<]+?)\s*</attention>\s*(.+)", entry, flags=re.IGNORECASE)
                if not att_match:
                    continue

                raw_val = att_match.group(1).strip().replace(",", ".")
                label = _turkish_lower(_strip_html(att_match.group(2)))
                is_percent = "%" in raw_val
                num_match = re.search(r"(\d+(?:\.\d+)?)", raw_val)
                if not num_match:
                    continue
                val_num = float(num_match.group(1))

                if "yetenek hızı" in label or "ability haste" in label:
                    parsed["ability_haste"] = round(val_num, 2)
                elif "zırh deşme" in label or "lethality" in label:
                    parsed["lethality"] = round(val_num, 2)
                elif "zırh delme" in label or "armor penetration" in label:
                    parsed["armor_pen_percent"] = round(val_num / 100.0 if is_percent else val_num, 4)
                elif "büyü nüfuzu" in label or "magic penetration" in label:
                    if is_percent:
                        parsed["magic_pen_percent"] = round(val_num / 100.0, 4)
                    else:
                        parsed["magic_pen_flat"] = round(val_num, 2)
                elif "kritik vuruş hasarı" in label or "critical strike damage" in label:
                    parsed["crit_damage_bonus"] = round(val_num / 100.0 if is_percent else val_num, 4)
                elif "mutlak sömürü" in label or "omnivamp" in label:
                    parsed["omnivamp"] = round(val_num / 100.0 if is_percent else val_num, 4)
                elif "iyileştirme ve kalkan" in label or "heal and shield" in label:
                    parsed["heal_shield_power"] = round(val_num / 100.0 if is_percent else val_num, 4)
                elif "sıvışma" in label or "tenacity" in label:
                    parsed["tenacity"] = round(val_num / 100.0 if is_percent else val_num, 4)
                elif "taban can yenilenmesi" in label or "base health regen" in label:
                    parsed["hp_regen_percent"] = round(val_num / 100.0 if is_percent else val_num, 4)
                elif "taban mana yenilenmesi" in label or "base mana regen" in label:
                    parsed["mana_regen_percent"] = round(val_num / 100.0 if is_percent else val_num, 4)

        # 3. Total AP percentage multiplier (e.g., Rabadon's Deathcap)
        clean_desc = _turkish_lower(_strip_html(description))
        ap_mult_tr = re.search(r"yetenek gücünü\s*%(\d+(?:\.\d+)?)\s*art", clean_desc)
        ap_mult_en = re.search(r"total ability power by\s*(\d+(?:\.\d+)?)%", clean_desc)
        if ap_mult_tr:
            parsed["ap_multiplier"] = round(float(ap_mult_tr.group(1)) / 100.0, 4)
        elif ap_mult_en:
            parsed["ap_multiplier"] = round(float(ap_mult_en.group(1)) / 100.0, 4)

        return parsed

    @staticmethod
    def detect_unique_groups(
        raw_item: Dict[str, Any], parsed_stats: Dict[str, float]
    ) -> List[str]:
        """Identifies mutually exclusive unique item groups (Boots, Lifeline, ArmorPen, etc.)."""
        groups: List[str] = []
        tags = raw_item.get("tags") or []
        clean_desc = _turkish_lower(_strip_html(raw_item.get("description") or ""))
        name_lower = _turkish_lower(raw_item.get("name") or "")

        if "Boots" in tags:
            groups.append("Boots")
        if parsed_stats.get("armor_pen_percent", 0.0) > 0.0:
            groups.append("ArmorPen")
        if parsed_stats.get("magic_pen_percent", 0.0) > 0.0:
            groups.append("MagicPenPercent")
        if "can simidi" in clean_desc or "lifeline" in clean_desc:
            groups.append("Lifeline")
        if "büyülükılıç" in clean_desc or "spellblade" in clean_desc:
            groups.append("Spellblade")
        if "hidra" in name_lower or "hydra" in name_lower:
            groups.append("Hydra")

        return groups

    @staticmethod
    def is_completed_sr_item(raw_item: Dict[str, Any], item_id: str = "") -> bool:
        """Checks whether an item is a standard completed purchasable Summoner's Rift (Map 11) item."""
        # 5-6 digit IDs (22xxxx, 32xxxx, 66xxxx) are Arena/mode variants; 70xx are Ornn Masterwork upgrades.
        if item_id:
            if not item_id.isdigit() or len(item_id) != 4:
                return False
            iid_num = int(item_id)
            if 7000 <= iid_num < 7100:
                return False

        maps = raw_item.get("maps") or {}
        gold = raw_item.get("gold") or {}
        if not maps.get("11", False):
            return False
        if not gold.get("purchasable", False):
            return False
        if raw_item.get("inStore") is False:
            return False
        if raw_item.get("requiredChampion") or raw_item.get("requiredAlly"):
            return False
        total_gold = int(gold.get("total", 0))
        tags = raw_item.get("tags") or []
        # In Season 16, Tier-2 boots upgrade into Mid Role Quest Tier-3 boots (317x) and carry an 'into' field;
        # keep them flagged as completed boot items when cost >= 900g.
        if "Boots" in tags:
            return total_gold >= 900
        if raw_item.get("into"):
            return False
        return total_gold >= 2000

    @staticmethod
    def _extract_champion_base_stats(raw_stats: Dict[str, Any]) -> Dict[str, float]:
        return {
            "base_hp": float(raw_stats.get("hp", 0.0)),
            "hp_growth": float(raw_stats.get("hpperlevel", 0.0)),
            "base_mp": float(raw_stats.get("mp", 0.0)),
            "mp_growth": float(raw_stats.get("mpperlevel", 0.0)),
            "base_ad": float(raw_stats.get("attackdamage", 0.0)),
            "ad_growth": float(raw_stats.get("attackdamageperlevel", 0.0)),
            "base_armor": float(raw_stats.get("armor", 0.0)),
            "armor_growth": float(raw_stats.get("armorperlevel", 0.0)),
            "base_mr": float(raw_stats.get("spellblock", 0.0)),
            "mr_growth": float(raw_stats.get("spellblockperlevel", 0.0)),
            "base_attack_speed": float(raw_stats.get("attackspeed", 0.625)),
            "attack_speed_growth": float(raw_stats.get("attackspeedperlevel", 0.0)),
            "attack_range": float(raw_stats.get("attackrange", 125.0)),
            "move_speed": float(raw_stats.get("movespeed", 325.0)),
            "base_hp_regen": float(raw_stats.get("hpregen", 0.0)),
            "hp_regen_growth": float(raw_stats.get("hpregenperlevel", 0.0)),
            "base_mp_regen": float(raw_stats.get("mpregen", 0.0)),
            "mp_regen_growth": float(raw_stats.get("mpregenperlevel", 0.0)),
        }

    @classmethod
    def sync_version(
        cls,
        db: Session,
        version: str,
        previous_version: Optional[str] = None,
        is_latest: bool = False,
        update_legacy_tables: bool = False,
        lang: Optional[str] = None,
        timeout: float = 15.0,
    ) -> PatchVersion:
        """Downloads and upserts all champion, item, and rune data from DDragon for one patch version."""
        locale = lang or settings.DDRAGON_LANG
        base_url = f"{DDRAGON_BASE}/cdn/{version}/data/{locale}"

        with httpx.Client(timeout=timeout) as client:
            champs_data: Dict[str, Any] = cls._get_json_with_retry(
                client, f"{base_url}/champion.json"
            )["data"]
            items_data: Dict[str, Any] = cls._get_json_with_retry(
                client, f"{base_url}/item.json"
            )["data"]
            runes_data: List[Dict[str, Any]] = cls._get_json_with_retry(
                client, f"{base_url}/runesReforged.json"
            )

        # 1. Upsert PatchVersion metadata row
        if is_latest:
            db.query(PatchVersion).filter(PatchVersion.version != version).update(
                {"is_latest": False}
            )

        patch_row = db.query(PatchVersion).filter(PatchVersion.version == version).first()
        if not patch_row:
            patch_row = PatchVersion(
                version=version,
                previous_version=previous_version,
                is_latest=is_latest,
                sync_status="pending",
            )
            db.add(patch_row)
            db.flush()
        else:
            if previous_version:
                patch_row.previous_version = previous_version
            patch_row.is_latest = is_latest

        # 2. Upsert Champion Snapshots
        existing_champs = {
            c.champion_key: c
            for c in db.query(ChampionSnapshot).filter(ChampionSnapshot.patch_version == version).all()
        }
        champ_count = 0
        for champ_key, raw in champs_data.items():
            base_stats = cls._extract_champion_base_stats(raw.get("stats") or {})
            riot_id = int(raw["key"]) if str(raw.get("key", "")).isdigit() else None
            seed_abilities = CHAMPION_SEED_DATA.get(champ_key, {}).get("abilities", {})

            snap = existing_champs.get(champ_key)
            if snap:
                snap.riot_id = riot_id
                snap.name = raw.get("name", champ_key)
                snap.title = raw.get("title")
                snap.tags = raw.get("tags") or []
                snap.partype = raw.get("partype")
                snap.base_stats = base_stats
                if not snap.abilities and seed_abilities:
                    snap.abilities = seed_abilities
                    snap.abilities_source = "seed"
            else:
                db.add(
                    ChampionSnapshot(
                        patch_version=version,
                        champion_key=champ_key,
                        riot_id=riot_id,
                        name=raw.get("name", champ_key),
                        title=raw.get("title"),
                        tags=raw.get("tags") or [],
                        partype=raw.get("partype"),
                        base_stats=base_stats,
                        abilities=seed_abilities,
                        abilities_source="seed" if seed_abilities else "ddragon",
                    )
                )
            champ_count += 1

            if update_legacy_tables:
                legacy_champ = db.query(Champion).filter(Champion.key == champ_key).first()
                if legacy_champ:
                    legacy_champ.name = raw.get("name", champ_key)
                    legacy_champ.title = raw.get("title")
                    legacy_champ.patch_version = version
                    legacy_champ.base_stats = base_stats
                    if not legacy_champ.abilities and seed_abilities:
                        legacy_champ.abilities = seed_abilities
                else:
                    db.add(
                        Champion(
                            key=champ_key,
                            name=raw.get("name", champ_key),
                            title=raw.get("title"),
                            patch_version=version,
                            base_stats=base_stats,
                            abilities=seed_abilities,
                        )
                    )

        # 3. Upsert Item Snapshots (Map 11 / Summoner's Rift purchasable items only)
        existing_items = {
            i.item_id: i
            for i in db.query(ItemSnapshot).filter(ItemSnapshot.patch_version == version).all()
        }
        item_count = 0
        for item_id, raw in items_data.items():
            maps = raw.get("maps") or {}
            gold = raw.get("gold") or {}
            if not maps.get("11", False) or not gold.get("purchasable", False):
                continue
            if raw.get("inStore") is False or raw.get("requiredChampion"):
                continue

            parsed_stats = cls.parse_item_stats(raw)
            completed = cls.is_completed_sr_item(raw, item_id=item_id)
            unique_groups = cls.detect_unique_groups(raw, parsed_stats)
            passive_text = _strip_html(raw.get("description") or "")
            img_full = (raw.get("image") or {}).get("full")
            icon_url = build_item_icon_url(version, item_id, img_full)

            snap = existing_items.get(item_id)
            if snap:
                snap.name = raw.get("name", item_id)
                snap.gold_total = int(gold.get("total", 0))
                snap.is_completed = completed
                snap.purchasable = True
                snap.stats = parsed_stats
                snap.tags = raw.get("tags") or []
                snap.unique_groups = unique_groups
                snap.passive_text = passive_text
                snap.icon_url = icon_url
            else:
                db.add(
                    ItemSnapshot(
                        patch_version=version,
                        item_id=item_id,
                        name=raw.get("name", item_id),
                        gold_total=int(gold.get("total", 0)),
                        is_completed=completed,
                        purchasable=True,
                        stats=parsed_stats,
                        tags=raw.get("tags") or [],
                        unique_groups=unique_groups,
                        passive_text=passive_text,
                        icon_url=icon_url,
                    )
                )
            item_count += 1

            if update_legacy_tables and completed and parsed_stats:
                legacy_item = db.query(Item).filter(Item.item_id == item_id).first()
                if legacy_item:
                    legacy_item.name = raw.get("name", item_id)
                    legacy_item.gold_total = int(gold.get("total", 0))
                    legacy_item.stats = parsed_stats
                else:
                    db.add(
                        Item(
                            item_id=item_id,
                            name=raw.get("name", item_id),
                            gold_total=int(gold.get("total", 0)),
                            stats=parsed_stats,
                        )
                    )

        # Clean up stale items in legacy `items` table that are no longer valid completed SR items
        if update_legacy_tables:
            valid_legacy_ids = {
                iid
                for iid, raw in items_data.items()
                if cls.is_completed_sr_item(raw, item_id=iid) and cls.parse_item_stats(raw)
            }
            if valid_legacy_ids:
                db.query(Item).filter(~Item.item_id.in_(valid_legacy_ids)).delete(
                    synchronize_session=False
                )

        # 4. Upsert Runes
        existing_runes = {
            r.rune_id: r
            for r in db.query(Rune).filter(Rune.patch_version == version).all()
        }
        rune_count = 0
        for tree in runes_data:
            tree_id = int(tree["id"])
            tree_key = tree["key"]
            tree_name = tree["name"]
            for slot_idx, slot in enumerate(tree.get("slots") or []):
                for rune in slot.get("runes") or []:
                    r_id = int(rune["id"])
                    short_desc = _strip_html(rune.get("shortDesc") or "")
                    long_desc = _strip_html(rune.get("longDesc") or "")
                    existing_r = existing_runes.get(r_id)
                    if existing_r:
                        existing_r.key = rune["key"]
                        existing_r.name = rune["name"]
                        existing_r.tree_id = tree_id
                        existing_r.tree_key = tree_key
                        existing_r.tree_name = tree_name
                        existing_r.slot_index = slot_idx
                        existing_r.is_keystone = slot_idx == 0
                        existing_r.short_desc = short_desc
                        existing_r.long_desc = long_desc
                    else:
                        db.add(
                            Rune(
                                patch_version=version,
                                rune_id=r_id,
                                key=rune["key"],
                                name=rune["name"],
                                tree_id=tree_id,
                                tree_key=tree_key,
                                tree_name=tree_name,
                                slot_index=slot_idx,
                                is_keystone=slot_idx == 0,
                                short_desc=short_desc,
                                long_desc=long_desc,
                            )
                        )
                    rune_count += 1

        patch_row.champions_count = champ_count
        patch_row.items_count = item_count
        patch_row.runes_count = rune_count
        patch_row.sync_status = "synced"
        patch_row.synced_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(patch_row)
        return patch_row

    @classmethod
    def sync_latest_two_patches(cls, db: Session) -> List[PatchVersion]:
        """Discovers the latest two Riot Data Dragon patches and syncs them sequentially."""
        versions = cls.fetch_latest_versions(count=2)
        if not versions:
            raise RuntimeError("Failed to retrieve valid patch versions from Riot Data Dragon.")

        synced: List[PatchVersion] = []
        if len(versions) >= 2:
            latest_v, prev_v = versions[0], versions[1]
            synced.append(
                cls.sync_version(
                    db=db,
                    version=prev_v,
                    previous_version=None,
                    is_latest=False,
                    update_legacy_tables=False,
                )
            )
            synced.append(
                cls.sync_version(
                    db=db,
                    version=latest_v,
                    previous_version=prev_v,
                    is_latest=True,
                    update_legacy_tables=True,
                )
            )
        else:
            synced.append(
                cls.sync_version(
                    db=db,
                    version=versions[0],
                    previous_version=None,
                    is_latest=True,
                    update_legacy_tables=True,
                )
            )

        return synced


if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        print("🌐 Syncing the latest 2 patches from Riot Data Dragon...")
        results = DDragonSyncService.sync_latest_two_patches(session)
        for pv in results:
            tag = " [LATEST]" if pv.is_latest else ""
            print(
                f"✅ Patch {pv.version}{tag}: saved {pv.champions_count} champions, "
                f"{pv.items_count} items, {pv.runes_count} runes."
            )
    finally:
        session.close()
