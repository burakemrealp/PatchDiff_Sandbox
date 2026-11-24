from copy import deepcopy

from app.seed_data import CHAMPION_SEED_DATA
from app.services.meta_shift_analyzer import MetaShiftAnalyzer

SAMPLE_AP_ITEMS_OLD = [
    {"item_id": "3089", "name": "Rabadon'un Şapkası", "gold_total": 3600, "tags": ["SpellDamage"], "unique_groups": [], "stats": {"ap": 130.0, "ap_multiplier": 0.30}},
    {"item_id": "3135", "name": "Hiçlik Değneği", "gold_total": 3000, "tags": ["SpellDamage"], "unique_groups": ["MagicPenPercent"], "stats": {"ap": 95.0, "magic_pen_percent": 0.40}},
    {"item_id": "4645", "name": "Gölgealev", "gold_total": 3200, "tags": ["SpellDamage"], "unique_groups": [], "stats": {"ap": 110.0, "magic_pen_flat": 15.0}},
    {"item_id": "6655", "name": "Luden'in Feryadı", "gold_total": 2900, "tags": ["SpellDamage"], "unique_groups": [], "stats": {"ap": 95.0, "mana": 600.0, "ability_haste": 10.0}},
    {"item_id": "3157", "name": "Zhonya'nın Kumsaati", "gold_total": 3250, "tags": ["SpellDamage"], "unique_groups": [], "stats": {"ap": 105.0, "armor": 50.0}},
    {"item_id": "3100", "name": "Lich Boğan", "gold_total": 3100, "tags": ["SpellDamage"], "unique_groups": ["Spellblade"], "stats": {"ap": 90.0, "ability_haste": 10.0}},
]


def test_meta_shift_analyzer_detects_buff_gains_and_baseline_comparison():
    ahri = CHAMPION_SEED_DATA["Ahri"]
    old_abilities = deepcopy(ahri["abilities"])
    new_abilities = deepcopy(ahri["abilities"])
    # Buff Ahri Q AP ratio 90% -> 115% in the new patch
    new_abilities["Q"]["scaling"]["ap"] = 1.15

    # Reduce Lich Bane cost (3100 -> 2800) and buff AP (90 -> 120) in the new patch
    new_items = deepcopy(SAMPLE_AP_ITEMS_OLD)
    for it in new_items:
        if it["item_id"] == "3100":
            it["gold_total"] = 2800
            it["stats"]["ap"] = 120.0

    report = MetaShiftAnalyzer.analyze_snapshots(
        champion_key="Ahri",
        champion_name="Ahri",
        from_version="16.22.1",
        to_version="16.23.1",
        old_base_stats=ahri["base_stats"],
        old_abilities=old_abilities,
        new_base_stats=ahri["base_stats"],
        new_abilities=new_abilities,
        old_items=SAMPLE_AP_ITEMS_OLD,
        new_items=new_items,
        tags=["Mage", "Assassin"],
        partype="Mana",
        target_profile_key="squishy",
        champion_patch_diff={"champion_key": "Ahri", "summary": "Q AP ratio buff"},
    )

    assert report["champion_changed_in_patch"] is True
    assert report["old_meta_baseline"] is not None
    assert len(report["variations"]) == 3

    for var in report["variations"]:
        shift = var["patch_shift"]
        assert shift["status"] == "GAINED"
        assert shift["lvl18_burst_delta_pct"] > 0.0
        assert shift["lvl18_dps_delta_pct"] > 0.0
        assert var["vs_old_meta"] is not None
        assert "rank" in var
