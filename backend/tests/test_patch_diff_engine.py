import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.entities import (
    AutoPatchDiff,
    ChampionSnapshot,
    ItemSnapshot,
    PatchVersion,
    Rune,
)
from app.services.patch_diff_engine import PatchDiffEngine


@pytest.fixture()
def diff_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()

    db.add_all(
        [
            PatchVersion(version="16.22.1", is_latest=False, sync_status="synced"),
            PatchVersion(
                version="16.23.1", previous_version="16.22.1", is_latest=True, sync_status="synced"
            ),
        ]
    )
    db.flush()

    base_stats_old = {
        "base_hp": 590.0,
        "hp_growth": 104.0,
        "base_ad": 53.0,
        "ad_growth": 3.0,
        "base_armor": 21.0,
        "armor_growth": 4.7,
        "base_mr": 30.0,
        "mr_growth": 1.3,
        "base_attack_speed": 0.668,
        "attack_speed_growth": 2.2,
        "move_speed": 330.0,
    }
    base_stats_new = dict(base_stats_old, base_armor=18.0)

    ab_old = {
        "Q": {
            "name": "AhriQ",
            "damage_type": "magic",
            "base_damage": [80.0, 130.0, 180.0, 230.0, 280.0],
            "cooldown": [7.0, 7.0, 7.0, 7.0, 7.0],
            "scaling": {"ap": 0.90},
        }
    }
    ab_new = {
        "Q": {
            "name": "AhriQ",
            "damage_type": "magic",
            "base_damage": [90.0, 145.0, 200.0, 255.0, 310.0],
            "cooldown": [6.5, 6.5, 6.5, 6.5, 6.5],
            "scaling": {"ap": 1.05},
        }
    }

    # Changed champion (Ahri) + unchanged champion (Zed)
    db.add_all(
        [
            ChampionSnapshot(
                patch_version="16.22.1",
                champion_key="Ahri",
                name="Ahri",
                base_stats=base_stats_old,
                abilities=ab_old,
            ),
            ChampionSnapshot(
                patch_version="16.23.1",
                champion_key="Ahri",
                name="Ahri",
                base_stats=base_stats_new,
                abilities=ab_new,
            ),
            ChampionSnapshot(
                patch_version="16.22.1",
                champion_key="Zed",
                name="Zed",
                base_stats=base_stats_old,
                abilities=ab_old,
            ),
            ChampionSnapshot(
                patch_version="16.23.1",
                champion_key="Zed",
                name="Zed",
                base_stats=base_stats_old,
                abilities=ab_old,
            ),
            # Item buff: Rabadon cheaper (3600 -> 3500) + AP unchanged
            ItemSnapshot(
                patch_version="16.22.1",
                item_id="3089",
                name="Rabadon'un Şapkası",
                gold_total=3600,
                is_completed=True,
                stats={"ap": 130.0, "ap_multiplier": 0.30},
            ),
            ItemSnapshot(
                patch_version="16.23.1",
                item_id="3089",
                name="Rabadon'un Şapkası",
                gold_total=3500,
                is_completed=True,
                stats={"ap": 130.0, "ap_multiplier": 0.30},
            ),
            # Unchanged item
            ItemSnapshot(
                patch_version="16.22.1",
                item_id="3135",
                name="Hiçlik Değneği",
                gold_total=3000,
                is_completed=True,
                stats={"ap": 95.0, "magic_pen_percent": 0.40},
            ),
            ItemSnapshot(
                patch_version="16.23.1",
                item_id="3135",
                name="Hiçlik Değneği",
                gold_total=3000,
                is_completed=True,
                stats={"ap": 95.0, "magic_pen_percent": 0.40},
            ),
        ]
    )
    db.commit()
    try:
        yield db
    finally:
        db.close()
        engine.dispose()


def test_compute_latest_diffs_detects_champion_and_item_changes(diff_db):
    summary = PatchDiffEngine.compute_latest_diffs(diff_db)

    assert summary["from_version"] == "16.22.1"
    assert summary["to_version"] == "16.23.1"
    assert summary["champions_changed"] == 1
    assert summary["items_changed"] == 1

    champ_row = (
        diff_db.query(AutoPatchDiff).filter_by(entity_type="champion", entity_key="Ahri").one()
    )
    assert champ_row.direction == "ADJUSTMENT"  # 1 stat NERF + 1 ability BUFF
    assert len(champ_row.diff_payload["stat_deltas"]) == 1
    assert champ_row.diff_payload["stat_deltas"][0]["stat_name"] == "base_armor"
    assert len(champ_row.diff_payload["ability_deltas"]) == 1
    assert champ_row.diff_payload["ability_deltas"][0]["slot"] == "Q"

    item_row = diff_db.query(AutoPatchDiff).filter_by(entity_type="item", entity_key="3089").one()
    assert item_row.direction == "BUFF"  # Gold decreased 3600 -> 3500
    assert item_row.diff_payload["gold_change"]["delta"] == -100

    # Idempotent re-run produces identical row count
    summary_again = PatchDiffEngine.compute_latest_diffs(diff_db)
    assert summary_again["total"] == 2
    assert diff_db.query(AutoPatchDiff).count() == 2


def test_patch_diff_engine_v2_catches_mana_mechanics_item_passives_and_runes(diff_db):
    # 1. Champion: mana cost increase + _raw_spells shield buff + attack_range buff
    diff_db.add_all(
        [
            ChampionSnapshot(
                patch_version="16.22.1",
                champion_key="Galio",
                name="Galio",
                base_stats={"base_hp": 632.0, "attack_range": 150.0},
                abilities={
                    "W": {"name": "GalioW", "damage_type": "magic", "base_damage": [0]*5, "cooldown": [18]*5, "mana_cost": [50]*5, "scaling": {}},
                    "_raw_spells": {"GalioW": {"data_values": {"ShieldPercent": [0.05, 0.075, 0.09, 0.105, 0.12, 0.135]}, "calculations": {}}},
                },
            ),
            ChampionSnapshot(
                patch_version="16.23.1",
                champion_key="Galio",
                name="Galio",
                base_stats={"base_hp": 632.0, "attack_range": 175.0},
                abilities={
                    "W": {"name": "GalioW", "damage_type": "magic", "base_damage": [0]*5, "cooldown": [18]*5, "mana_cost": [60]*5, "scaling": {}},
                    "_raw_spells": {"GalioW": {"data_values": {"ShieldPercent": [0.05, 0.08, 0.11, 0.14, 0.17, 0.20]}, "calculations": {}}},
                },
            ),
            # 2. Item passive value nerf (Voltaic Cyclosword style)
            ItemSnapshot(
                patch_version="16.22.1",
                item_id="6699",
                name="Elektrikli Devirkılıcı",
                gold_total=3000,
                is_completed=True,
                stats={"ad": 55.0, "_passive_values": {"PercentCurrentHPMelee": 9.0, "PercentCurrentHPRanged": 7.0}},
            ),
            ItemSnapshot(
                patch_version="16.23.1",
                item_id="6699",
                name="Elektrikli Devirkılıcı",
                gold_total=3000,
                is_completed=True,
                stats={"ad": 55.0, "_passive_values": {"PercentCurrentHPMelee": 8.0, "PercentCurrentHPRanged": 6.0}},
            ),
            # 3. Rune engine coefficient buff
            Rune(
                patch_version="16.22.1",
                rune_id=8112,
                key="Electrocute",
                name="Elektrik Ver",
                tree_id=8100,
                tree_key="Domination",
                tree_name="Hakimiyet",
                slot_index=0,
                is_keystone=True,
                effect_values={"DamageBase": 50.0, "Cooldown": 20.0},
            ),
            Rune(
                patch_version="16.23.1",
                rune_id=8112,
                key="Electrocute",
                name="Elektrik Ver",
                tree_id=8100,
                tree_key="Domination",
                tree_name="Hakimiyet",
                slot_index=0,
                is_keystone=True,
                effect_values={"DamageBase": 70.0, "Cooldown": 20.0},
            ),
        ]
    )
    diff_db.commit()

    summary = PatchDiffEngine.compute_latest_diffs(diff_db)
    assert summary["champions_changed"] == 2  # Ahri + Galio
    assert summary["items_changed"] == 2  # Rabadon + Voltaic Cyclosword
    assert summary["runes_changed"] == 1  # Electrocute

    galio_row = diff_db.query(AutoPatchDiff).filter_by(entity_type="champion", entity_key="Galio").one()
    assert galio_row.diff_payload["stat_deltas"][0]["stat_name"] == "attack_range"
    assert galio_row.diff_payload["ability_deltas"][0]["new_mana_cost"] == [60.0] * 5
    assert galio_row.diff_payload["mechanic_deltas"][0]["field_name"] == "ShieldPercent"

    item_row = diff_db.query(AutoPatchDiff).filter_by(entity_type="item", entity_key="6699").one()
    assert item_row.direction == "NERF"
    assert len(item_row.diff_payload["passive_data_changes"]) == 2

    rune_row = diff_db.query(AutoPatchDiff).filter_by(entity_type="rune", entity_key="8112").one()
    assert rune_row.direction == "BUFF"
    assert rune_row.diff_payload["effect_changes"][0]["field_name"] == "DamageBase"
