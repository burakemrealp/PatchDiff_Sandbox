import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.entities import Champion, ChampionSnapshot, PatchVersion
from app.services.cdragon_enricher import CDragonEnricherService, version_to_cdragon_branch


def test_version_to_cdragon_branch():
    assert version_to_cdragon_branch("16.23.1") == "16.23"
    assert version_to_cdragon_branch("15.4.1") == "15.4"
    assert version_to_cdragon_branch("invalid") == "latest"


def test_parse_champion_bin_extracts_base_damage_cooldown_and_scalings():
    sample_bin = {
        "Characters/Ahri/CharacterRecords/Root": {
            "spellNames": [
                "AhriQAbility/AhriQ",
                "AhriWAbility/AhriW",
                "AhriEAbility/AhriE",
                "AhriRAbility/AhriR",
            ]
        },
        "Characters/Ahri/Spells/AhriQAbility/AhriQ": {
            "mSpell": {
                "cooldownTime": [7.0, 7.0, 7.0, 7.0, 7.0, 7.0, 7.0],
                "DataValues": [
                    {"name": "BaseDamage", "values": [10.0, 35.0, 60.0, 85.0, 110.0, 135.0, 160.0]}
                ],
                "mSpellCalculations": {
                    "TotalDamage": {
                        "__type": "GameCalculation",
                        "mFormulaParts": [
                            {"__type": "NamedDataValueCalculationPart", "mDataValue": "BaseDamage"},
                            {"__type": "StatByCoefficientCalculationPart", "mCoefficient": 0.5},
                        ],
                    }
                },
            }
        },
        "Characters/Ahri/Spells/AhriRAbility/AhriR": {
            "mSpell": {
                "cooldownTime": [140.0, 140.0, 120.0, 100.0, 100.0, 100.0, 100.0],
                "DataValues": [
                    {"name": "RBaseDamage", "values": [25.0, 75.0, 125.0, 175.0, 225.0]},
                    {"name": "rAPCoefficient", "values": [0.35, 0.35, 0.35, 0.35]},
                ],
                "mSpellCalculations": {
                    "RCalculatedDamage": {
                        "__type": "GameCalculation",
                        "mFormulaParts": [
                            {"__type": "NamedDataValueCalculationPart", "mDataValue": "RBaseDamage"},
                            {
                                "__type": "StatByNamedDataValueCalculationPart",
                                "mDataValue": "rAPCoefficient",
                            },
                        ],
                    }
                },
            }
        },
    }

    abilities = CDragonEnricherService.parse_champion_bin(sample_bin, "Ahri", tags=["Mage"])
    assert abilities["Q"]["base_damage"] == [35.0, 60.0, 85.0, 110.0, 135.0]
    assert abilities["Q"]["cooldown"] == [7.0, 7.0, 7.0, 7.0, 7.0]
    assert abilities["Q"]["scaling"] == {"ap": 0.5}
    assert abilities["Q"]["damage_type"] == "magic"

    assert abilities["R"]["base_damage"] == [75.0, 125.0, 175.0]
    assert abilities["R"]["cooldown"] == [140.0, 120.0, 100.0]
    assert abilities["R"]["scaling"] == {"ap": 0.35}


def test_parse_champion_bin_maps_bonus_ad_armor_and_mr_scaling():
    sample_bin = {
        "Characters/Ornn/CharacterRecords/Root": {
            "spellNames": ["OrnnQAbility/OrnnQ", "OrnnEAbility/OrnnE"]
        },
        "Characters/Ornn/Spells/OrnnQAbility/OrnnQ": {
            "mSpell": {
                "cooldownTime": [9.0, 9.0, 8.5, 8.0, 7.5, 7.0, 6.5],
                "DataValues": [{"name": "BaseDamage", "values": [0, 20, 45, 70, 95, 120, 145]}],
                "mSpellCalculations": {
                    "TotalDamage": {
                        "__type": "GameCalculation",
                        "mFormulaParts": [
                            {"__type": "NamedDataValueCalculationPart", "mDataValue": "BaseDamage"},
                            {
                                "__type": "StatByCoefficientCalculationPart",
                                "mStat": 2,
                                "mStatFormula": 2,
                                "mCoefficient": 1.1,
                            },
                        ],
                    }
                },
            }
        },
        "Characters/Ornn/Spells/OrnnEAbility/OrnnE": {
            "mSpell": {
                "cooldownTime": [16.0, 16.0, 15.0, 14.0, 13.0, 12.0, 11.0],
                "DataValues": [
                    {"name": "ArmorRatio", "values": [0.4, 0.4, 0.4, 0.4, 0.4, 0.4]},
                    {"name": "MRRatio", "values": [0.4, 0.4, 0.4, 0.4, 0.4, 0.4]},
                ],
                "mSpellCalculations": {
                    "TotalDamage": {
                        "__type": "GameCalculation",
                        "mFormulaParts": [
                            {
                                "__type": "StatByNamedDataValueCalculationPart",
                                "mStat": 1,
                                "mStatFormula": 2,
                                "mDataValue": "ArmorRatio",
                            },
                            {
                                "__type": "StatByNamedDataValueCalculationPart",
                                "mStat": 6,
                                "mStatFormula": 2,
                                "mDataValue": "MRRatio",
                            },
                        ],
                    }
                },
            }
        },
    }

    abilities = CDragonEnricherService.parse_champion_bin(sample_bin, "Ornn", tags=["Tank"])
    assert abilities["Q"]["scaling"] == {"bonus_ad": 1.1}
    assert abilities["Q"]["damage_type"] == "physical"
    assert abilities["W"]["scaling"] == {"armor": 0.4, "mr": 0.4}


def test_enrich_patch_champions_falls_back_to_seed_when_offline(monkeypatch):
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
            tags=["Mage"],
            base_stats={"base_hp": 590.0},
            abilities={},
            abilities_source="ddragon",
        )
    )
    db.add(
        Champion(
            key="Ahri",
            name="Ahri",
            patch_version="16.23.1",
            base_stats={"base_hp": 590.0},
            abilities={},
        )
    )
    db.commit()

    class _FailClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def get(self, url: str):
            raise RuntimeError("network offline")

    monkeypatch.setattr("app.services.cdragon_enricher.httpx.Client", _FailClient)

    try:
        summary = CDragonEnricherService.enrich_patch_champions(
            db, "16.23.1", update_legacy_tables=True
        )
        assert summary == {"total": 1, "cdragon": 0, "fallback": 1}
        snap = db.query(ChampionSnapshot).filter_by(patch_version="16.23.1", champion_key="Ahri").one()
        assert snap.abilities_source == "seed"
        assert "Q" in snap.abilities
        legacy = db.query(Champion).filter_by(key="Ahri").one()
        assert "Q" in legacy.abilities
    finally:
        db.close()
        engine.dispose()
