from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.core.versioning import to_display_version
from app.models.entities import ChampionSnapshot, ItemSnapshot, PatchVersion, Rune
from app.services.cdragon_enricher import CDragonEnricherService
from app.services.data_auditor import DataAuditorService


def test_to_display_version_maps_season_15_plus_to_year_patch():
    assert to_display_version("16.23.1") == "26.23"
    assert to_display_version("16.22.1") == "26.22"
    assert to_display_version("15.1.1") == "25.1"
    assert to_display_version("17.5.1") == "27.5"
    assert to_display_version("14.23.1") == "14.23"
    assert to_display_version(None) is None


def test_cdragon_captures_raw_spells_and_summary_cooldown_mana():
    sample_bin = {
        "Characters/Syndra/CharacterRecords/Root": {
            "spellNames": ["SyndraQ/SyndraQ", "SyndraW/SyndraW", "SyndraE/SyndraE", "SyndraR/SyndraR"]
        },
        "Characters/Syndra/Spells/SyndraE/SyndraE": {
            "mSpell": {
                "cooldownTime": [15.0] * 7,
                "DataValues": [{"name": "BaseDamage", "values": [0, 75, 115, 155, 195, 235, 275]}],
                "mSpellCalculations": {
                    "TotalDamage": {
                        "__type": "GameCalculation",
                        "mFormulaParts": [{"__type": "StatByCoefficientCalculationPart", "mCoefficient": 0.45}],
                    }
                },
            }
        },
    }
    parsed = CDragonEnricherService.parse_champion_bin(sample_bin, "Syndra", tags=["Mage"])
    assert "_raw_spells" in parsed
    assert "SyndraE" in parsed["_raw_spells"]
    assert parsed["_raw_spells"]["SyndraE"]["data_values"]["BaseDamage"][1] == 75.0

    # Summary JSON overrides with exact Riot cooldownCoefficients & costCoefficients
    summary = {
        "spells": [
            {
                "spellKey": "e",
                "name": "Scatter the Weak",
                "cooldownCoefficients": [17.0, 16.5, 16.0, 15.5, 15.0, 15.0],
                "costCoefficients": [60.0, 60.0, 60.0, 60.0, 60.0, 60.0],
            }
        ]
    }
    CDragonEnricherService._merge_summary_spell_metadata(summary, parsed)
    assert parsed["E"]["cooldown"] == [17.0, 16.5, 16.0, 15.5, 15.0]
    assert parsed["E"]["mana_cost"] == [60.0, 60.0, 60.0, 60.0, 60.0]


def test_data_auditor_flags_missing_cdragon_and_passes_healthy_snapshot():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()

    db.add(PatchVersion(version="16.23.1", is_latest=True, sync_status="synced"))
    db.flush()
    db.add(
        ChampionSnapshot(
            patch_version="16.23.1",
            champion_key="Ahri",
            name="Ahri",
            base_stats={"base_hp": 590.0, "attack_range": 550.0},
            abilities={
                "Q": {},
                "W": {},
                "E": {},
                "R": {},
                "_raw_spells": {"AhriQ": {"data_values": {"BaseDamage": [35.0]}, "calculations": {}}},
            },
            abilities_source="cdragon",
        )
    )
    db.add(
        ItemSnapshot(
            patch_version="16.23.1",
            item_id="3089",
            name="Rabadon",
            gold_total=3500,
            is_completed=True,
            stats={"ap": 130.0},
        )
    )
    for idx, tree in enumerate(["Domination", "Inspiration", "Precision", "Resolve", "Sorcery"]):
        db.add(
            Rune(
                patch_version="16.23.1",
                rune_id=8000 + idx,
                key=f"Key{idx}",
                name=f"Rune{idx}",
                tree_id=8000 + idx * 100,
                tree_key=tree,
                tree_name=tree,
                slot_index=0,
                is_keystone=True,
            )
        )
    db.commit()

    try:
        rep = DataAuditorService.audit_version(db, "16.23.1")
        assert rep["display_version"] == "26.23"
        assert rep["healthy"] is True
        assert rep["issues_count"] == 0
    finally:
        db.close()
        engine.dispose()
