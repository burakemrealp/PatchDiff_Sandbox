import copy
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.database import Base, get_db
from app.engine.combat_simulator import CombatSimulator
from app.engine.pve_lab_engine import PvELabEngine
from app.main import app
from app.models.entities import ChampionSnapshot, ItemSnapshot, PatchVersion
from app.seed_data import CHAMPION_SEED_DATA
from app.services.aram_balance_service import AramBalanceService


def test_aram_overrides_bundle_covers_roster_and_modifies_aram_simulation():
    AramBalanceService.clear_cache()
    ziggs = AramBalanceService.get_champion_aram_modifiers("Ziggs")
    qiyana = AramBalanceService.get_champion_aram_modifiers("Qiyana")

    assert ziggs["has_modifiers"] is True
    assert ziggs["dmg_dealt"] < 1.0
    assert ziggs["dmg_taken"] > 1.0
    assert ziggs["ability_haste"] < 0.0

    assert qiyana["has_modifiers"] is True
    assert qiyana["dmg_dealt"] > 1.0
    assert qiyana["dmg_taken"] < 1.0
    assert qiyana["ability_haste"] > 0.0

    ahri = CHAMPION_SEED_DATA["Ahri"]
    items = [{"item_id": "6655", "name": "Luden's Companion", "gold_total": 2850, "stats": {"ap": 100.0, "mana": 600.0, "ability_haste": 10.0}}]

    sim_sr = CombatSimulator.run_simulation(
        champion_key="Ahri",
        base_stats=ahri["base_stats"],
        base_abilities=ahri["abilities"],
        patch_diff=None,
        items=items,
        target_profile_key="squishy",
        role="mid",
        game_map="sr",
    )
    sim_aram_nerf = CombatSimulator.run_simulation(
        champion_key="Ahri",
        base_stats=ahri["base_stats"],
        base_abilities=ahri["abilities"],
        patch_diff=None,
        items=items,
        target_profile_key="squishy",
        role="mid",
        game_map="aram",
        aram_modifiers_override={
            "dmg_dealt": 0.92,
            "dmg_taken": 1.20,
            "shielding": 1.0,
            "ability_haste": -20.0,
            "total_as": 1.0,
            "has_modifiers": True,
        },
    )
    sim_aram_buff = CombatSimulator.run_simulation(
        champion_key="Ahri",
        base_stats=ahri["base_stats"],
        base_abilities=ahri["abilities"],
        patch_diff=None,
        items=items,
        target_profile_key="squishy",
        role="mid",
        game_map="aram",
        aram_modifiers_override={
            "dmg_dealt": 1.15,
            "dmg_taken": 0.90,
            "shielding": 1.0,
            "ability_haste": 20.0,
            "total_as": 1.0,
            "has_modifiers": True,
        },
    )

    sr_lvl11 = sim_sr["level_curves"][10]
    nerf_lvl11 = sim_aram_nerf["level_curves"][10]
    buff_lvl11 = sim_aram_buff["level_curves"][10]

    assert nerf_lvl11["new_burst"] < sr_lvl11["new_burst"] < buff_lvl11["new_burst"]
    assert nerf_lvl11["new_dps"] < sr_lvl11["new_dps"] < buff_lvl11["new_dps"]
    assert sim_aram_nerf["abilities"]["Q"]["new_cooldown"][10] > sim_sr["abilities"]["Q"]["new_cooldown"][10]
    assert sim_aram_buff["abilities"]["Q"]["new_cooldown"][10] < sim_sr["abilities"]["Q"]["new_cooldown"][10]
    assert sim_aram_nerf["game_context"]["aram_modifiers"]["dmg_dealt"] == 0.92


def test_waveclear_breakpoints_solve_exact_caster_oneshot_ap_threshold():
    ahri = CHAMPION_SEED_DATA["Ahri"]

    bare_report = PvELabEngine.evaluate(
        champion_key="Ahri",
        champion_name="Ahri",
        base_stats=ahri["base_stats"],
        abilities=ahri["abilities"],
        items=[],
        role="mid",
        game_map="sr",
    )
    min9_bare = next(row for row in bare_report["waveclear_breakpoints"] if row["minute"] == 9)
    assert min9_bare["primary_slot"] == "Q"
    assert min9_bare["can_oneshot_caster"] is False
    # Ahri Q Rank 5 = 280 + 0.90*AP vs 368 Caster HP -> 97.8 AP needed
    assert min9_bare["scaling_stat"] == "ap"
    assert 97.5 <= min9_bare["required_stat_value"] <= 98.0
    assert 97.5 <= min9_bare["missing_stat_value"] <= 98.0

    luden_report = PvELabEngine.evaluate(
        champion_key="Ahri",
        champion_name="Ahri",
        base_stats=ahri["base_stats"],
        abilities=ahri["abilities"],
        items=[{"item_id": "6655", "name": "Luden's Companion", "gold_total": 2850, "stats": {"ap": 100.0, "mana": 600.0, "ability_haste": 10.0}}],
        role="mid",
        game_map="sr",
    )
    min9_luden = next(row for row in luden_report["waveclear_breakpoints"] if row["minute"] == 9)
    assert min9_luden["can_oneshot_caster"] is True
    assert min9_luden["missing_stat_value"] == 0.0
    assert min9_luden["item_proc_damage"] >= 75.0
    assert min9_luden["full_wave_clear_sec"] < min9_bare["full_wave_clear_sec"]


@pytest.fixture()
def pve_client(monkeypatch):
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

    jinx = CHAMPION_SEED_DATA["Jinx"]
    ahri = CHAMPION_SEED_DATA["Ahri"]
    db.add_all(
        [
            PatchVersion(version="16.23.1", is_latest=True, sync_status="synced"),
            ChampionSnapshot(
                patch_version="16.23.1",
                champion_key="Jinx",
                name="Jinx",
                tags=["Marksman"],
                partype="Mana",
                base_stats=copy.deepcopy(jinx["base_stats"]),
                abilities=copy.deepcopy(jinx["abilities"]),
            ),
            ChampionSnapshot(
                patch_version="16.23.1",
                champion_key="Ahri",
                name="Ahri",
                tags=["Mage", "Assassin"],
                partype="Mana",
                base_stats=copy.deepcopy(ahri["base_stats"]),
                abilities=copy.deepcopy(ahri["abilities"]),
            ),
            ItemSnapshot(
                patch_version="16.23.1",
                item_id="3153",
                name="Blade of the Ruined King",
                gold_total=3200,
                is_completed=True,
                stats={"ad": 40.0, "attack_speed": 0.25, "lifesteal": 0.10},
                tags=["Damage"],
                unique_groups=[],
            ),
            ItemSnapshot(
                patch_version="16.23.1",
                item_id="6655",
                name="Luden's Companion",
                gold_total=2850,
                is_completed=True,
                stats={"ap": 100.0, "mana": 600.0, "ability_haste": 10.0},
                tags=["SpellDamage"],
                unique_groups=[],
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


def test_objective_matrix_monster_caps_and_pve_lab_endpoint_25_locales(pve_client, monkeypatch):
    fake_cache = {}
    monkeypatch.setattr("app.api.routes.redis_client.get", lambda k: fake_cache.get(k))
    monkeypatch.setattr(
        "app.api.routes.redis_client.setex", lambda k, ttl, v: fake_cache.__setitem__(k, v)
    )
    monkeypatch.setattr(
        "app.services.locale_service.get_ddragon_localization",
        lambda ver, lang: {
            "champions": {"Jinx": {"name": f"Jinx-{lang}"}, "Ahri": {"name": f"Ahri-{lang}"}},
            "items": {"3153": f"BotRK-{lang}", "6655": f"Luden-{lang}"},
        },
    )

    payload = {
        "champion_key": "Jinx",
        "item_ids": ["3153"],
        "role": "adc",
        "game_map": "sr",
        "lang": "tr_TR",
    }
    r1 = pve_client.post("/api/v1/pve-lab", json=payload)
    assert r1.status_code == 200
    d1 = r1.json()
    assert d1["cached"] is False
    objs = {o["monster_key"]: o for o in d1["report"]["objective_benchmarks"]}
    assert objs["dragon"]["solo_kill_time_sec"] < objs["atakhan"]["solo_kill_time_sec"] < objs["baron"]["solo_kill_time_sec"]
    assert objs["dragon"]["monster_name"] == "Elemental Ejderha"

    r2 = pve_client.post("/api/v1/pve-lab", json=payload)
    assert r2.status_code == 200
    assert r2.json()["cached"] is True

    for loc, expected_baron in [
        ("en_US", "Baron Nashor"),
        ("ko_KR", "\ub0b4\uc154 \ub0a8\uc791"),
        ("ar_AE", "\u0628\u0627\u0631\u0648\u0646 \u0646\u0627\u0634\u0648\u0631"),
    ]:
        resp = pve_client.post("/api/v1/pve-lab", json={**payload, "lang": loc})
        assert resp.status_code == 200
        rep = resp.json()["report"]
        assert rep["champion_name"] == f"Jinx-{loc}"
        baron_row = next(o for o in rep["objective_benchmarks"] if o["monster_key"] == "baron")
        assert baron_row["monster_name"] == expected_baron
