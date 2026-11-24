import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.entities import (
    Champion,
    ChampionSnapshot,
    Item,
    ItemSnapshot,
    PatchVersion,
    Rune,
)
from app.services.ddragon_sync import DDragonSyncService


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_parse_item_stats_handles_tr_and_en_descriptions():
    rabadon = {
        "name": "Rabadon'un Şapkası",
        "stats": {"FlatMagicDamageMod": 130},
        "tags": ["SpellDamage"],
        "description": "<mainText><stats><attention>130</attention> Yetenek Gücü</stats><br><br><passive>Sihirli Eser</passive><br>Toplam <scaleAP>yetenek gücünü %30</scaleAP> arttırır.</mainText>",
    }
    ldr = {
        "name": "Dominik Efendi'nin Hürmetleri",
        "stats": {"FlatCritChanceMod": 0.25, "FlatPhysicalDamageMod": 35},
        "tags": ["Damage", "CriticalStrike", "ArmorPenetration"],
        "description": "<mainText><stats><attention>35</attention> Saldırı Gücü<br><attention>%35</attention> Zırh Delme<br><attention>%25</attention> Kritik Vuruş İhtimali</stats></mainText>",
    }
    shadowflame = {
        "name": "Gölgealev",
        "stats": {"FlatMagicDamageMod": 110},
        "tags": ["SpellDamage", "MagicPenetration"],
        "description": "<mainText><stats><attention>110</attention> Yetenek Gücü<br><attention>15</attention> Büyü Nüfuzu</stats></mainText>",
    }
    ie = {
        "name": "Ebedi Kılıç",
        "stats": {"FlatCritChanceMod": 0.25, "FlatPhysicalDamageMod": 75},
        "tags": ["CriticalStrike", "Damage"],
        "description": "<mainText><stats><attention>75</attention> Saldırı Gücü<br><attention>%25</attention> Kritik Vuruş İhtimali<br><attention>%30</attention> Kritik Vuruş Hasarı</stats></mainText>",
    }
    cleaver = {
        "name": "Kara Balta",
        "stats": {"FlatHPPoolMod": 400, "FlatPhysicalDamageMod": 45},
        "tags": ["Health", "Damage", "AbilityHaste"],
        "description": "<mainText><stats><attention>45</attention> Saldırı Gücü<br><attention>400</attention> Can<br><attention>20</attention> Yetenek Hızı</stats></mainText>",
    }

    r_stats = DDragonSyncService.parse_item_stats(rabadon)
    assert r_stats["ap"] == 130.0
    assert r_stats["ap_multiplier"] == pytest.approx(0.30)

    ldr_stats = DDragonSyncService.parse_item_stats(ldr)
    assert ldr_stats["ad"] == 35.0
    assert ldr_stats["crit_chance"] == pytest.approx(0.25)
    assert ldr_stats["armor_pen_percent"] == pytest.approx(0.35)
    assert "ArmorPen" in DDragonSyncService.detect_unique_groups(ldr, ldr_stats)

    sf_stats = DDragonSyncService.parse_item_stats(shadowflame)
    assert sf_stats["magic_pen_flat"] == 15.0
    assert "magic_pen_percent" not in sf_stats

    ie_stats = DDragonSyncService.parse_item_stats(ie)
    assert ie_stats["crit_damage_bonus"] == pytest.approx(0.30)

    bc_stats = DDragonSyncService.parse_item_stats(cleaver)
    assert bc_stats["hp"] == 400.0
    assert bc_stats["ability_haste"] == 20.0


def test_sync_latest_two_patches_offline_mocked(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()

    sample_champs = {
        "data": {
            "Ahri": {
                "key": "103",
                "name": "Ahri",
                "title": "Dokuz Kuyruklu Tilki",
                "tags": ["Mage", "Assassin"],
                "partype": "Mana",
                "stats": {
                    "hp": 590,
                    "hpperlevel": 104,
                    "attackdamage": 53,
                    "attackdamageperlevel": 3,
                    "armor": 21,
                    "armorperlevel": 4.7,
                    "spellblock": 30,
                    "spellblockperlevel": 1.3,
                    "attackspeed": 0.668,
                    "attackspeedperlevel": 2.2,
                    "movespeed": 330,
                },
            }
        }
    }
    sample_items = {
        "data": {
            "3089": {
                "name": "Rabadon'un Şapkası",
                "maps": {"11": True},
                "gold": {"total": 3500, "purchasable": True},
                "stats": {"FlatMagicDamageMod": 130},
                "tags": ["SpellDamage"],
                "description": "<mainText><stats><attention>130</attention> Yetenek Gücü</stats><br>Toplam <scaleAP>yetenek gücünü %30</scaleAP> arttırır.</mainText>",
            },
            "1052": {
                "name": "Kuvvet Kitabı",
                "maps": {"11": True},
                "gold": {"total": 400, "purchasable": True},
                "into": ["3089"],
                "stats": {"FlatMagicDamageMod": 20},
                "tags": ["SpellDamage"],
                "description": "<mainText><stats><attention>20</attention> Yetenek Gücü</stats></mainText>",
            },
        }
    }
    sample_runes = [
        {
            "id": 8100,
            "key": "Domination",
            "name": "Hakimiyet",
            "slots": [
                {
                    "runes": [
                        {
                            "id": 8112,
                            "key": "Electrocute",
                            "name": "Elektrik Ver",
                            "shortDesc": "3 saldırı ek hasar verir.",
                            "longDesc": "Detaylı açıklama.",
                        }
                    ]
                }
            ],
        }
    ]

    class _FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def get(self, url: str):
            if url.endswith("/api/versions.json"):
                return _FakeResponse(["16.23.1", "16.22.1", "lolpatch_7.23"])
            if url.endswith("/champion.json"):
                return _FakeResponse(sample_champs)
            if url.endswith("/item.json"):
                return _FakeResponse(sample_items)
            if url.endswith("/runesReforged.json"):
                return _FakeResponse(sample_runes)
            raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr("app.services.ddragon_sync.httpx.Client", _FakeClient)

    try:
        synced = DDragonSyncService.sync_latest_two_patches(db)
        assert [p.version for p in synced] == ["16.22.1", "16.23.1"]
        assert db.query(PatchVersion).filter_by(is_latest=True).one().version == "16.23.1"
        assert db.query(ChampionSnapshot).count() == 2
        assert db.query(ItemSnapshot).filter_by(patch_version="16.23.1", is_completed=True).count() == 1
        assert db.query(Rune).filter_by(patch_version="16.23.1", is_keystone=True).count() == 1
        # Legacy tables updated only with latest completed items & champions
        assert db.query(Champion).filter_by(key="Ahri", patch_version="16.23.1").count() == 1
        assert db.query(Item).filter_by(item_id="3089").count() == 1
        assert db.query(Item).filter_by(item_id="1052").count() == 0
    finally:
        db.close()
        engine.dispose()
