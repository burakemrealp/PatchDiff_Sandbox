from app.engine.combat_simulator import CombatSimulator
from app.seed_data import CHAMPION_SEED_DATA


def test_electrocute_and_first_strike_boost_burst():
    ahri = CHAMPION_SEED_DATA["Ahri"]
    items = [{"item_id": "3089", "name": "Rabadon", "stats": {"ap": 130.0, "ap_multiplier": 0.30}}]

    base_sim = CombatSimulator.run_simulation("Ahri", ahri["base_stats"], ahri["abilities"], None, items, "squishy")
    elec_sim = CombatSimulator.run_simulation(
        "Ahri", ahri["base_stats"], ahri["abilities"], None, items, "squishy", keystone_key="Electrocute"
    )
    fs_sim = CombatSimulator.run_simulation(
        "Ahri", ahri["base_stats"], ahri["abilities"], None, items, "squishy", keystone_key="FirstStrike"
    )

    assert elec_sim["level_curves"][10]["new_burst"] > base_sim["level_curves"][10]["new_burst"]
    assert fs_sim["level_curves"][17]["new_burst"] > base_sim["level_curves"][17]["new_burst"]
    assert elec_sim["active_effects"]["keystone"] == "Electrocute"


def test_lethal_tempo_and_pta_boost_jinx_sustained_dps():
    jinx = CHAMPION_SEED_DATA["Jinx"]
    items = [{"item_id": "3031", "name": "IE", "stats": {"ad": 75.0, "crit_chance": 0.25, "crit_damage_bonus": 0.30}}]

    base_sim = CombatSimulator.run_simulation("Jinx", jinx["base_stats"], jinx["abilities"], None, items, "tank")
    lt_sim = CombatSimulator.run_simulation(
        "Jinx", jinx["base_stats"], jinx["abilities"], None, items, "tank", keystone_key="LethalTempo"
    )
    pta_sim = CombatSimulator.run_simulation(
        "Jinx", jinx["base_stats"], jinx["abilities"], None, items, "tank", keystone_key="PressTheAttack"
    )

    assert lt_sim["level_curves"][17]["new_dps"] > base_sim["level_curves"][17]["new_dps"]
    assert pta_sim["level_curves"][17]["new_dps"] > base_sim["level_curves"][17]["new_dps"]


def test_item_passives_liandry_and_lich_bane_affect_simulation():
    ahri = CHAMPION_SEED_DATA["Ahri"]

    plain_ap = [{"item_id": "9999", "name": "Plain AP", "stats": {"ap": 70.0, "hp": 300.0}}]
    liandry = [{"item_id": "6653", "name": "Liandry", "stats": {"ap": 70.0, "hp": 300.0}}]
    lich_plain = [{"item_id": "9998", "name": "Plain Lich", "stats": {"ap": 115.0, "ability_haste": 10.0}}]
    lich_bane = [{"item_id": "3100", "name": "Lich Bane", "stats": {"ap": 115.0, "ability_haste": 10.0}}]

    sim_plain_tank = CombatSimulator.run_simulation("Ahri", ahri["base_stats"], ahri["abilities"], None, plain_ap, "tank")
    sim_liandry_tank = CombatSimulator.run_simulation("Ahri", ahri["base_stats"], ahri["abilities"], None, liandry, "tank")

    sim_lich_plain = CombatSimulator.run_simulation("Ahri", ahri["base_stats"], ahri["abilities"], None, lich_plain, "squishy")
    sim_lich = CombatSimulator.run_simulation("Ahri", ahri["base_stats"], ahri["abilities"], None, lich_bane, "squishy")

    # Liandry's %max HP burn shines against Tank
    assert sim_liandry_tank["level_curves"][17]["new_dps"] > sim_plain_tank["level_curves"][17]["new_dps"]
    assert len(sim_liandry_tank["active_effects"]["item_passives"]) == 1

    # Lich Bane Spellblade adds burst and DPS
    assert sim_lich["level_curves"][10]["new_burst"] > sim_lich_plain["level_curves"][10]["new_burst"]
    assert "Lich Bane" in sim_lich["active_effects"]["item_passives"][0]


def test_defensive_passives_and_aftershock_report_ehp_bonus():
    ornn = CHAMPION_SEED_DATA["Ornn"]
    sterak = [{"item_id": "3053", "name": "Sterak", "stats": {"hp": 400.0}}]

    sim = CombatSimulator.run_simulation(
        "Ornn", ornn["base_stats"], ornn["abilities"], None, sterak, "bruiser", keystone_key="Aftershock"
    )
    # Sterak (+15%) + Aftershock (+12%) = +27%
    assert sim["active_effects"]["ehp_bonus_pct"] == 27.0
