import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.database import Base, get_db
from app.engine.game_state_pivot_engine import classify_item_winrate_trap
from app.main import app
from app.models.entities import ChampionSnapshot, ItemSnapshot, PatchVersion
from app.seed_data import CHAMPION_SEED_DATA
from app.services.meta_shift_analyzer import MetaShiftAnalyzer


def _pivot_item_pool():
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
            "item_id": "3041",
            "name": "Mejai's Soulstealer",
            "gold_total": 1500,
            "stats": {"ap": 115.0, "hp": 100.0, "move_speed_percent": 0.10},
            "tags": ["SpellDamage"],
            "unique_groups": ["Glory"],
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
            "item_id": "3157",
            "name": "Zhonya's Hourglass",
            "gold_total": 3250,
            "stats": {"ap": 105.0, "armor": 50.0},
            "tags": ["SpellDamage"],
            "unique_groups": [],
        },
        {
            "item_id": "3102",
            "name": "Banshee's Veil",
            "gold_total": 3000,
            "stats": {"ap": 105.0, "mr": 40.0},
            "tags": ["SpellDamage"],
            "unique_groups": ["Annul"],
        },
        {
            "item_id": "3137",
            "name": "Cryptbloom",
            "gold_total": 2850,
            "stats": {"ap": 60.0, "magic_pen_percent": 0.30, "ability_haste": 15.0},
            "tags": ["SpellDamage"],
            "unique_groups": ["MagicPenPercent"],
        },
        {
            "item_id": "6653",
            "name": "Liandry's Torment",
            "gold_total": 3000,
            "stats": {"ap": 70.0, "hp": 300.0},
            "tags": ["SpellDamage"],
            "unique_groups": [],
        },
        {
            "item_id": "3116",
            "name": "Rylai's Crystal Scepter",
            "gold_total": 2600,
            "stats": {"ap": 65.0, "hp": 400.0},
            "tags": ["SpellDamage"],
            "unique_groups": [],
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


def test_winrate_trap_detector_identifies_snowball_and_luxury_traps_with_comeback_alternatives():
    items = _pivot_item_pool()
    mejai = next(i for i in items if i["item_id"] == "3041")
    rabadon = next(i for i in items if i["item_id"] == "3089")
    shadowflame = next(i for i in items if i["item_id"] == "4645")
    cryptbloom = next(i for i in items if i["item_id"] == "3137")

    assert classify_item_winrate_trap(mejai)["trap_code"] == "STACKING_SNOWBALL_TRAP"
    assert classify_item_winrate_trap(rabadon)["trap_code"] == "LUXURY_GOLD_WALL_TRAP"
    assert classify_item_winrate_trap(shadowflame)["trap_code"] == "FLAT_PEN_EXECUTION_TRAP"
    assert classify_item_winrate_trap(cryptbloom) is None


def test_dynamic_pivot_adapts_gold_survivability_and_burst_across_behind_even_ahead():
    ahri = CHAMPION_SEED_DATA["Ahri"]
    items = _pivot_item_pool()

    report_behind = MetaShiftAnalyzer.analyze_snapshots(
        champion_key="Ahri",
        champion_name="Ahri",
        from_version="16.22.1",
        to_version="16.23.1",
        old_base_stats=ahri["base_stats"],
        old_abilities=ahri["abilities"],
        new_base_stats=ahri["base_stats"],
        new_abilities=ahri["abilities"],
        old_items=items,
        new_items=items,
        tags=["Mage", "Assassin"],
        partype="Mana",
        target_profile_key="squishy",
        role="mid",
        game_map="sr",
        game_state="behind",
    )

    assert report_behind["game_state"] == "behind"
    assert len(report_behind["winrate_trap_warnings"]) >= 2
    assert any(
        w["trap_code"] == "LUXURY_GOLD_WALL_TRAP" and w["comeback_alternative"] is not None
        for w in report_behind["winrate_trap_warnings"]
    )

    pivots = report_behind["pivot_tree"]["pivots"]
    assert set(pivots.keys()) == {"behind", "even", "ahead"}
    assert pivots["behind"]["total_gold"] < pivots["ahead"]["total_gold"]
    assert pivots["behind"]["avg_ehp_lvl11"] > pivots["ahead"]["avg_ehp_lvl11"]
    assert pivots["ahead"]["lvl18_burst"] >= pivots["behind"]["lvl18_burst"]


@pytest.fixture()
def pivot_client(monkeypatch):
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
        ]
    )

    for ver in ("16.22.1", "16.23.1"):
        for it in _pivot_item_pool():
            db.add(
                ItemSnapshot(
                    patch_version=ver,
                    item_id=it["item_id"],
                    name=it["name"],
                    gold_total=it["gold_total"],
                    is_completed=True,
                    stats=it["stats"],
                    tags=it["tags"],
                    unique_groups=it["unique_groups"],
                )
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


def test_recommend_builds_endpoint_supports_game_state_and_25_locales(pivot_client, monkeypatch):
    fake_cache = {}
    monkeypatch.setattr("app.api.routes.redis_client.get", lambda k: fake_cache.get(k))
    monkeypatch.setattr(
        "app.api.routes.redis_client.setex", lambda k, ttl, v: fake_cache.__setitem__(k, v)
    )
    monkeypatch.setattr(
        "app.services.locale_service.get_ddragon_localization",
        lambda ver, lang: {
            "champions": {"Ahri": {"name": f"Ahri-{lang}"}},
            "items": {"3089": f"Rabadon-{lang}", "3137": f"Cryptbloom-{lang}"},
            "trees": {},
            "runes": {},
            "rune_ids": {},
        },
    )

    r_tr = pivot_client.post(
        "/api/v1/recommend-builds",
        json={
            "champion_key": "Ahri",
            "target_profile": "squishy",
            "role": "mid",
            "game_map": "sr",
            "game_state": "behind",
            "use_ai": False,
            "lang": "tr_TR",
        },
    )
    assert r_tr.status_code == 200
    rep_tr = r_tr.json()["report"]
    assert rep_tr["game_state"] == "behind"
    assert "Gerideyim" in rep_tr["pivot_tree"]["active_state_label"]
    assert len(rep_tr["winrate_trap_warnings"]) >= 1

    for loc, expected_label in [
        ("en_US", "Behind"),
        ("ko_KR", "\ubd88\ub9ac\ud568"),
        ("ar_AE", "\u0645\u062a\u0623\u062e\u0631"),
    ]:
        resp = pivot_client.post(
            "/api/v1/recommend-builds",
            json={
                "champion_key": "Ahri",
                "target_profile": "squishy",
                "role": "mid",
                "game_map": "sr",
                "game_state": "behind",
                "use_ai": False,
                "lang": loc,
            },
        )
        assert resp.status_code == 200
        rep = resp.json()["report"]
        assert expected_label in rep["pivot_tree"]["active_state_label"]
