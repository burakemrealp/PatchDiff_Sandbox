import copy
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.database import Base, get_db
from app.main import app
from app.models.entities import AutoPatchDiff, ChampionSnapshot, ItemSnapshot, PatchVersion
from app.seed_data import CHAMPION_SEED_DATA
from app.services.zero_day_oracle import ZeroDayOracleService


def _base_test_items():
    return [
        {
            "item_id": "6655",
            "name": "Luden's Companion",
            "gold_total": 2850,
            "stats": {"ap": 100.0, "mana": 600.0, "ability_haste": 10.0},
            "tags": ["SpellDamage"],
            "unique_groups": [],
        },
        {
            "item_id": "3089",
            "name": "Rabadon's Deathcap",
            "gold_total": 3600,
            "stats": {"ap": 130.0, "ap_multiplier": 0.30},
            "tags": ["SpellDamage"],
            "unique_groups": [],
        },
        {
            "item_id": "4645",
            "name": "Shadowflame",
            "gold_total": 3200,
            "stats": {"ap": 110.0, "magic_pen_flat": 15.0},
            "tags": ["SpellDamage"],
            "unique_groups": [],
        },
        {
            "item_id": "3135",
            "name": "Void Staff",
            "gold_total": 3000,
            "stats": {"ap": 95.0, "magic_pen_percent": 0.40},
            "tags": ["SpellDamage"],
            "unique_groups": ["MagicPenPercent"],
        },
        {
            "item_id": "3157",
            "name": "Zhonya's Hourglass",
            "gold_total": 3250,
            "stats": {"ap": 105.0, "armor": 50.0},
            "tags": ["SpellDamage"],
            "unique_groups": [],
        },
        {
            "item_id": "6699",
            "name": "Voltaic Cyclosword",
            "gold_total": 3000,
            "stats": {"ad": 55.0, "lethality": 10.0, "ability_haste": 10.0},
            "tags": ["Damage"],
            "unique_groups": [],
        },
        {
            "item_id": "3142",
            "name": "Youmuu's Ghostblade",
            "gold_total": 2800,
            "stats": {"ad": 55.0, "lethality": 18.0},
            "tags": ["Damage"],
            "unique_groups": [],
        },
        {
            "item_id": "6697",
            "name": "Hubris",
            "gold_total": 2800,
            "stats": {"ad": 55.0, "lethality": 18.0, "ability_haste": 10.0},
            "tags": ["Damage"],
            "unique_groups": [],
        },
        {
            "item_id": "6696",
            "name": "Axiom Arc",
            "gold_total": 2750,
            "stats": {"ad": 55.0, "lethality": 18.0, "ability_haste": 20.0},
            "tags": ["Damage"],
            "unique_groups": [],
        },
        {
            "item_id": "6694",
            "name": "Serylda's Grudge",
            "gold_total": 3000,
            "stats": {"ad": 45.0, "armor_pen_percent": 0.35, "ability_haste": 15.0},
            "tags": ["Damage"],
            "unique_groups": ["ArmorPenPercent"],
        },
        {
            "item_id": "3020",
            "name": "Sorcerer's Shoes",
            "gold_total": 1100,
            "stats": {"magic_pen_flat": 12.0, "move_speed_flat": 45.0},
            "tags": ["Boots"],
            "unique_groups": ["Boots"],
        },
        {
            "item_id": "3158",
            "name": "Ionian Boots of Lucidity",
            "gold_total": 900,
            "stats": {"ability_haste": 10.0, "move_speed_flat": 45.0},
            "tags": ["Boots"],
            "unique_groups": ["Boots"],
        },
    ]


def test_hidden_winners_and_hidden_losers_detected_without_champion_changes():
    old_items = _base_test_items()
    new_items = copy.deepcopy(old_items)

    # Buff Luden's Companion (+25 AP, -200g) -> indirect Hidden Winner for unchanged AP Mage
    for it in new_items:
        if it["item_id"] == "6655":
            it["stats"]["ap"] = 125.0
            it["gold_total"] = 2650

    ahri = CHAMPION_SEED_DATA["Ahri"]
    zed = CHAMPION_SEED_DATA["Zed"]

    champs = {
        "Ahri": {
            "name": "Ahri",
            "tags": ["Mage", "Assassin"],
            "partype": "Mana",
            "base_stats": {**ahri["base_stats"], "attack_range": 550.0},
            "abilities": ahri["abilities"],
        },
        "Zed": {
            "name": "Zed",
            "tags": ["Assassin"],
            "partype": "Energy",
            "base_stats": {**zed["base_stats"], "attack_range": 125.0},
            "abilities": zed["abilities"],
        },
    }

    item_diffs = {
        "6655": {
            "entity_key": "6655",
            "entity_name": "Luden's Companion",
            "direction": "BUFF",
            "diff_payload": {
                "item_id": "6655",
                "gold_change": {"old": 2850, "new": 2650, "delta": -200},
                "stat_changes": [{"stat_name": "ap", "old_value": 100.0, "new_value": 125.0}],
                "passive_data_changes": [],
            },
        },
        "6699": {
            "entity_key": "6699",
            "entity_name": "Voltaic Cyclosword",
            "direction": "NERF",
            "diff_payload": {
                "item_id": "6699",
                "gold_change": None,
                "stat_changes": [],
                "passive_data_changes": [
                    {
                        "field_name": "PercentCurrentHPMelee",
                        "old_value": 9.0,
                        "new_value": 8.0,
                        "direction": "NERF",
                    },
                    {
                        "field_name": "PercentCurrentHPRanged",
                        "old_value": 7.0,
                        "new_value": 6.0,
                        "direction": "NERF",
                    },
                ],
            },
        },
    }

    radar = ZeroDayOracleService.compute_radar_from_snapshots(
        from_version="16.22.1",
        to_version="16.23.1",
        old_champions=champs,
        new_champions=champs,
        old_items=old_items,
        new_items=new_items,
        champ_diffs_by_key={},
        item_diffs_by_id=item_diffs,
        rune_diffs_by_key={},
    )

    hw_keys = [c["champion_key"] for c in radar["hidden_winners"]]
    hl_keys = [c["champion_key"] for c in radar["hidden_losers"]]

    assert "Ahri" in hw_keys
    assert "Zed" in hl_keys

    ahri_entry = next(c for c in radar["hidden_winners"] if c["champion_key"] == "Ahri")
    assert ahri_entry["power_shift_score"] > 1.0
    assert any(cat["entity_key"] == "6655" for cat in ahri_entry["catalysts"])

    zed_entry = next(c for c in radar["hidden_losers"] if c["champion_key"] == "Zed")
    assert zed_entry["power_shift_score"] < -0.5
    assert any(cat["entity_key"] == "6699" for cat in zed_entry["catalysts"])


def test_mythbuster_classifies_arena_only_placebo_paper_tiger_and_trap_buff():
    old_items = _base_test_items()
    new_items = copy.deepcopy(old_items)
    # Nerf Luden's heavily (-35 AP) so a +1 HP champ buff becomes a Trap Buff
    for it in new_items:
        if it["item_id"] == "6655":
            it["stats"]["ap"] = 65.0

    ahri = copy.deepcopy(CHAMPION_SEED_DATA["Ahri"])
    ahri_new = copy.deepcopy(ahri)
    ahri_new["base_stats"]["base_hp"] = ahri["base_stats"]["base_hp"] + 1.0

    zed = copy.deepcopy(CHAMPION_SEED_DATA["Zed"])
    ornn = copy.deepcopy(CHAMPION_SEED_DATA["Ornn"])
    jinx = copy.deepcopy(CHAMPION_SEED_DATA["Jinx"])
    jinx_new = copy.deepcopy(jinx)
    jinx_new["base_stats"]["base_hp"] = jinx["base_stats"]["base_hp"] + 5.0

    old_champs = {
        "Ahri": {"name": "Ahri", "tags": ["Mage", "Assassin"], "partype": "Mana", "base_stats": ahri["base_stats"], "abilities": ahri["abilities"]},
        "Zed": {"name": "Zed", "tags": ["Assassin"], "partype": "Energy", "base_stats": zed["base_stats"], "abilities": zed["abilities"]},
        "Ornn": {"name": "Ornn", "tags": ["Tank"], "partype": "Mana", "base_stats": ornn["base_stats"], "abilities": ornn["abilities"]},
        "Jinx": {"name": "Jinx", "tags": ["Marksman"], "partype": "Mana", "base_stats": jinx["base_stats"], "abilities": jinx["abilities"]},
    }
    new_champs = {
        **old_champs,
        "Ahri": {"name": "Ahri", "tags": ["Mage", "Assassin"], "partype": "Mana", "base_stats": ahri_new["base_stats"], "abilities": ahri_new["abilities"]},
        "Jinx": {"name": "Jinx", "tags": ["Marksman"], "partype": "Mana", "base_stats": jinx_new["base_stats"], "abilities": jinx_new["abilities"]},
    }

    champ_diffs = {
        "Ornn": {
            "entity_key": "Ornn",
            "entity_name": "Ornn",
            "direction": "BUFF",
            "diff_payload": {
                "stat_deltas": [],
                "ability_deltas": [],
                "mechanic_deltas": [
                    {
                        "spell_name": "OrnnPassive",
                        "field_name": "CherryBonusMod",
                        "old_values": [0.7],
                        "new_values": [0.8],
                        "direction": "BUFF",
                    }
                ],
            },
        },
        "Zed": {
            "entity_key": "Zed",
            "entity_name": "Zed",
            "direction": "NERF",
            "diff_payload": {
                "stat_deltas": [],
                "ability_deltas": [
                    {
                        "slot": "W",
                        "old_cooldown": [20.0, 18.5, 17.0, 15.5, 14.0],
                        "new_cooldown": [22.0, 20.0, 18.0, 16.0, 14.0],
                        "old_mana_cost": [40.0, 35.0, 30.0, 25.0, 20.0],
                        "new_mana_cost": [45.0, 40.0, 35.0, 30.0, 25.0],
                    }
                ],
                "mechanic_deltas": [],
            },
        },
        "Ahri": {
            "entity_key": "Ahri",
            "entity_name": "Ahri",
            "direction": "BUFF",
            "diff_payload": {
                "stat_deltas": [{"stat_name": "base_hp", "old_value": 590.0, "new_value": 591.0, "direction": "BUFF"}],
                "ability_deltas": [],
                "mechanic_deltas": [],
            },
        },
        "Jinx": {
            "entity_key": "Jinx",
            "entity_name": "Jinx",
            "direction": "BUFF",
            "diff_payload": {
                "stat_deltas": [{"stat_name": "base_hp", "old_value": 630.0, "new_value": 635.0, "direction": "BUFF"}],
                "ability_deltas": [],
                "mechanic_deltas": [],
            },
        },
    }

    radar = ZeroDayOracleService.compute_radar_from_snapshots(
        from_version="16.22.1",
        to_version="16.23.1",
        old_champions=old_champs,
        new_champions=new_champs,
        old_items=old_items,
        new_items=new_items,
        champ_diffs_by_key=champ_diffs,
        item_diffs_by_id={
            "6655": {
                "entity_key": "6655",
                "entity_name": "Luden's Companion",
                "direction": "NERF",
                "diff_payload": {"stat_changes": [{"stat_name": "ap", "old_value": 100.0, "new_value": 65.0}]},
            }
        },
        rune_diffs_by_key={},
        game_map="sr",
    )

    by_key = {m["champion_key"]: m for m in radar["mythbusters"]}
    assert by_key["Ornn"]["verdict_code"] == "MODE_SPECIFIC_TRAP"
    assert by_key["Ornn"]["is_myth_busted"] is True

    assert by_key["Zed"]["verdict_code"] == "PAPER_TIGER_NERF"
    assert by_key["Zed"]["is_myth_busted"] is True

    assert by_key["Ahri"]["verdict_code"] == "TRAP_BUFF_NET_NERF"
    assert by_key["Ahri"]["is_myth_busted"] is True

    assert by_key["Jinx"]["verdict_code"] == "PLACEBO_BUFF"
    assert by_key["Jinx"]["is_myth_busted"] is True


@pytest.fixture()
def radar_client(monkeypatch):
    monkeypatch.setattr(settings, "AUTO_SYNC_ENABLED", False)
    monkeypatch.setattr(settings, "LLM_PROVIDER", "offline")

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine)
    db = TestingSession()

    ahri = CHAMPION_SEED_DATA["Ahri"]
    zed = CHAMPION_SEED_DATA["Zed"]
    db.add_all(
        [
            PatchVersion(version="16.22.1", is_latest=False, sync_status="synced"),
            PatchVersion(
                version="16.23.1",
                previous_version="16.22.1",
                is_latest=True,
                sync_status="synced",
            ),
            ChampionSnapshot(
                patch_version="16.22.1",
                champion_key="Ahri",
                name="Ahri",
                tags=["Mage", "Assassin"],
                partype="Mana",
                base_stats=ahri["base_stats"],
                abilities=ahri["abilities"],
            ),
            ChampionSnapshot(
                patch_version="16.23.1",
                champion_key="Ahri",
                name="Ahri",
                tags=["Mage", "Assassin"],
                partype="Mana",
                base_stats=ahri["base_stats"],
                abilities=ahri["abilities"],
            ),
            ChampionSnapshot(
                patch_version="16.22.1",
                champion_key="Zed",
                name="Zed",
                tags=["Assassin"],
                partype="Energy",
                base_stats=zed["base_stats"],
                abilities=zed["abilities"],
            ),
            ChampionSnapshot(
                patch_version="16.23.1",
                champion_key="Zed",
                name="Zed",
                tags=["Assassin"],
                partype="Energy",
                base_stats=zed["base_stats"],
                abilities=zed["abilities"],
            ),
        ]
    )

    for ver in ("16.22.1", "16.23.1"):
        for it in _base_test_items():
            stats = copy.deepcopy(it["stats"])
            gold = it["gold_total"]
            if ver == "16.23.1" and it["item_id"] == "6655":
                stats["ap"] = 125.0
                gold = 2650
            db.add(
                ItemSnapshot(
                    patch_version=ver,
                    item_id=it["item_id"],
                    name=it["name"],
                    gold_total=gold,
                    is_completed=True,
                    stats=stats,
                    tags=it["tags"],
                    unique_groups=it["unique_groups"],
                )
            )

    db.add_all(
        [
            AutoPatchDiff(
                from_version="16.22.1",
                to_version="16.23.1",
                entity_type="item",
                entity_key="6655",
                entity_name="Luden's Companion",
                direction="BUFF",
                diff_payload={"stat_changes": [{"stat_name": "ap", "old_value": 100.0, "new_value": 125.0}]},
            ),
            AutoPatchDiff(
                from_version="16.22.1",
                to_version="16.23.1",
                entity_type="champion",
                entity_key="Zed",
                entity_name="Zed",
                direction="BUFF",
                diff_payload={
                    "stat_deltas": [],
                    "ability_deltas": [],
                    "mechanic_deltas": [
                        {
                            "spell_name": "ZedPassive",
                            "field_name": "CherryBonusDamage",
                            "old_values": [0.5],
                            "new_values": [0.6],
                            "direction": "BUFF",
                        }
                    ],
                },
            ),
        ]
    )
    db.commit()
    db.close()

    def _override_db():
        s = TestingSession()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = _override_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
    engine.dispose()


def test_zero_day_radar_endpoint_caching_and_25_locales(radar_client, monkeypatch):
    fake_cache = {}
    monkeypatch.setattr("app.api.routes.redis_client.get", lambda k: fake_cache.get(k))
    monkeypatch.setattr(
        "app.api.routes.redis_client.setex", lambda k, ttl, v: fake_cache.__setitem__(k, v)
    )
    monkeypatch.setattr(
        "app.services.locale_service.get_ddragon_localization",
        lambda ver, lang: {
            "champions": {"Ahri": {"name": f"Ahri-{lang}"}, "Zed": {"name": f"Zed-{lang}"}},
            "items": {"6655": f"Luden-{lang}"},
            "runes": {},
            "rune_ids": {},
        },
    )

    r_tr = radar_client.get("/api/v1/patches/zero-day-radar?lang=tr_TR")
    assert r_tr.status_code == 200
    d_tr = r_tr.json()
    assert d_tr["cached"] is False
    assert "0. Dakika Meta Kâhini" in d_tr["radar"]["share_card"]["headline"]
    assert d_tr["radar"]["mythbusters"][0]["verdict_code"] == "MODE_SPECIFIC_TRAP"
    assert "Farkl\u0131 Mod" in d_tr["radar"]["mythbusters"][0]["verdict_label"]

    r_tr_cached = radar_client.get("/api/v1/patches/zero-day-radar?lang=tr_TR")
    assert r_tr_cached.status_code == 200
    assert r_tr_cached.json()["cached"] is True

    for locale, expected_word in [
        ("en_US", "Zero-Day Meta Oracle"),
        ("ko_KR", "0분 차 메타 예언자"),
        ("ar_AE", "عرّاف الميتا"),
    ]:
        resp = radar_client.get(f"/api/v1/patches/zero-day-radar?lang={locale}")
        assert resp.status_code == 200
        radar = resp.json()["radar"]
        assert expected_word in radar["share_card"]["headline"]
        assert radar["hidden_winners"][0]["champion_name"] == f"Ahri-{locale}"
