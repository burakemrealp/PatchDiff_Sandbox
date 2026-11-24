from typing import Any, Dict, List

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.versioning import to_display_version
from app.models.entities import ChampionSnapshot, ItemSnapshot, PatchVersion, Rune


class DataAuditorService:
    """
    Audits completeness and mathematical integrity of champion, item, and rune snapshots
    across all synchronized patch versions in the database.
    """

    @classmethod
    def audit_version(cls, db: Session, patch_version: str) -> Dict[str, Any]:
        champs = db.query(ChampionSnapshot).filter_by(patch_version=patch_version).all()
        items = db.query(ItemSnapshot).filter_by(patch_version=patch_version, is_completed=True).all()
        runes = db.query(Rune).filter_by(patch_version=patch_version).all()

        # 1. Champion Integrity Audit
        non_cdragon_champs: List[str] = []
        missing_raw_spells: List[str] = []
        missing_attack_range: List[str] = []
        missing_slots: List[str] = []

        for c in champs:
            if c.abilities_source != "cdragon":
                non_cdragon_champs.append(c.champion_key)
            ab = c.abilities or {}
            if "_raw_spells" not in ab or not ab["_raw_spells"]:
                missing_raw_spells.append(c.champion_key)
            if not all(slot in ab for slot in ("Q", "W", "E", "R")):
                missing_slots.append(c.champion_key)
            if "attack_range" not in (c.base_stats or {}):
                missing_attack_range.append(c.champion_key)

        # 2. Completed Item Integrity Audit
        empty_stat_items: List[str] = []
        anomalous_items: List[str] = []
        for it in items:
            st = {k: v for k, v in (it.stats or {}).items() if not k.startswith("_")}
            if not st:
                empty_stat_items.append(f"{it.item_id}:{it.name}")
            if (
                float(st.get("crit_chance", 0.0)) > 1.0
                or float(st.get("armor_pen_percent", 0.0)) > 1.0
                or float(st.get("magic_pen_percent", 0.0)) > 1.0
                or float(st.get("attack_speed", 0.0)) > 2.5
                or it.gold_total <= 0
            ):
                anomalous_items.append(f"{it.item_id}:{it.name}")

        # 3. Rune Integrity Audit
        trees = sorted({r.tree_key for r in runes})
        keystones = [r for r in runes if r.is_keystone]
        invalid_rune_slots = [r.key for r in runes if r.slot_index not in (0, 1, 2, 3)]

        issues_count = (
            len(non_cdragon_champs)
            + len(missing_raw_spells)
            + len(missing_attack_range)
            + len(anomalous_items)
            + len(invalid_rune_slots)
            + (0 if len(trees) == 5 else 1)
        )

        return {
            "patch_version": patch_version,
            "display_version": to_display_version(patch_version),
            "healthy": issues_count == 0 and len(champs) > 0 and len(items) > 0 and len(runes) > 0,
            "issues_count": issues_count,
            "champions": {
                "total": len(champs),
                "cdragon_ok": len(champs) - len(non_cdragon_champs),
                "non_cdragon": non_cdragon_champs,
                "missing_raw_spells": missing_raw_spells,
                "missing_attack_range": missing_attack_range,
                "missing_qwer_slots": missing_slots,
            },
            "items": {
                "completed_total": len(items),
                "empty_stats_count": len(empty_stat_items),
                "empty_stats_sample": empty_stat_items[:10],
                "anomalous": anomalous_items,
            },
            "runes": {
                "total": len(runes),
                "trees_count": len(trees),
                "trees": trees,
                "keystones_count": len(keystones),
                "invalid_slots": invalid_rune_slots,
            },
        }

    @classmethod
    def audit_all_versions(cls, db: Session) -> List[Dict[str, Any]]:
        versions = db.query(PatchVersion).order_by(PatchVersion.is_latest.desc()).all()
        return [cls.audit_version(db, pv.version) for pv in versions]


if __name__ == "__main__":
    session = SessionLocal()
    try:
        reports = DataAuditorService.audit_all_versions(session)
        if not reports:
            print("⚠️ No synchronized patch versions found to audit.")
        for rep in reports:
            status = "✅ HEALTHY" if rep["healthy"] else f"⚠️ {rep['issues_count']} ISSUES"
            print(f"\n=== Patch {rep['display_version']} (Riot API: {rep['patch_version']}) — {status} ===")
            ch = rep["champions"]
            it = rep["items"]
            rn = rep["runes"]
            print(
                f"  Champions : {ch['cdragon_ok']}/{ch['total']} CDragon | "
                f"Missing _raw_spells: {len(ch['missing_raw_spells'])} | "
                f"Missing attack_range: {len(ch['missing_attack_range'])} | "
                f"Missing QWER: {len(ch['missing_qwer_slots'])}"
            )
            if ch["non_cdragon"]:
                print(f"    -> Non-CDragon: {ch['non_cdragon'][:10]}")
            print(
                f"  Items     : {it['completed_total']} completed | "
                f"Empty stats: {it['empty_stats_count']} | Anomalies: {len(it['anomalous'])}"
            )
            print(
                f"  Runes     : {rn['total']} runes | {rn['trees_count']} trees | "
                f"{rn['keystones_count']} Keystones | Invalid slots: {len(rn['invalid_slots'])}"
            )
    finally:
        session.close()
