from app.engine.combat_simulator import CombatSimulator
from app.engine.game_rules import infer_default_role, resolve_effective_rules
from app.seed_data import CHAMPION_SEED_DATA


def test_season_16_role_quests_on_summoners_rift_vs_aram():
    # ADC on SR: 7 total slots (6 legendaries + separate boot quest slot)
    adc_sr = resolve_effective_rules("adc", "sr")
    assert adc_sr["total_item_slots"] == 7
    assert adc_sr["legendary_slots"] == 6
    assert adc_sr["separate_boot_slot"] is True
    assert adc_sr["max_level"] == 18

    # ADC on ARAM: SR Role Quests disabled -> standard 6 slots & Single Lane label
    adc_aram = resolve_effective_rules("adc", "aram")
    assert adc_aram["role_quests_enabled"] is False
    assert adc_aram["role_label"] == "Single Lane (ARAM)"
    assert adc_aram["total_item_slots"] == 6
    assert adc_aram["legendary_slots"] == 5
    assert adc_aram["separate_boot_slot"] is False
    assert adc_aram["mana_priority_weight"] > 1.5

    # Top on SR: Level 20 cap!
    top_sr = resolve_effective_rules("top", "sr")
    assert top_sr["max_level"] == 20
    assert top_sr["total_item_slots"] == 6

    # Mid on SR: Tier 3 Boots!
    mid_sr = resolve_effective_rules("mid", "sr")
    assert mid_sr["tier3_boots"] is True
    assert mid_sr["total_item_slots"] == 6

    # Swiftplay: early spike focus + role quests enabled
    sp = resolve_effective_rules("adc", "swiftplay")
    assert sp["early_spike_weight"] > 1.2
    assert sp["total_item_slots"] == 7


def test_infer_default_role():
    assert infer_default_role(["Marksman"]) == "adc"
    assert infer_default_role(["Support", "Tank"]) == "support"
    assert infer_default_role(["Mage", "Assassin"]) == "mid"
    assert infer_default_role(["Tank", "Fighter"]) == "top"


def test_combat_simulator_supports_top_lane_level_20_scaling():
    ornn = CHAMPION_SEED_DATA["Ornn"]
    sim_top = CombatSimulator.run_simulation(
        champion_key="Ornn",
        base_stats=ornn["base_stats"],
        base_abilities=ornn["abilities"],
        patch_diff=None,
        items=[],
        target_profile_key="bruiser",
        keystone_key="GraspOfTheUndying",
        role="top",
        game_map="sr",
    )

    assert len(sim_top["level_curves"]) == 20
    assert sim_top["game_context"]["max_level"] == 20
    assert "late_game_lvl20" in sim_top["summary"]
    assert sim_top["level_curves"][19]["level"] == 20
    assert sim_top["level_curves"][19]["new_burst"] > sim_top["level_curves"][17]["new_burst"]
    assert sim_top["level_curves"][19]["new_dps"] > sim_top["level_curves"][17]["new_dps"]
