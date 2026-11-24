import pytest

from app.engine.combat_simulator import CombatSimulator
from app.engine.damage_calculator import DamageCalculator
from app.engine.stat_aggregator import StatAggregator
from app.schemas.patch_contracts import (
    AbilityDelta,
    AbilitySlot,
    ChampionPatchDiff,
    ScalingDelta,
    ScalingStat,
    StatDelta,
    StatName,
)
from app.seed_data import CHAMPION_SEED_DATA, ITEM_SEED_DATA


def _get_item(item_id: str) -> dict:
    return next(i for i in ITEM_SEED_DATA if i["item_id"] == item_id)


def test_stat_aggregator_ap_multiplier_and_multiplicative_pen():
    ahri = CHAMPION_SEED_DATA["Ahri"]
    rabadon = _get_item("3089")
    void_staff = _get_item("3135")
    shadowflame = _get_item("4645")

    vecs = StatAggregator.compute_level_vectors(ahri["base_stats"], [rabadon, void_staff, shadowflame])

    # Raw AP: 130 + 95 + 110 = 335; with +30% Rabadon = 435.5
    assert vecs["ap"][0] == pytest.approx(435.5)
    assert vecs["magic_pen_flat"][0] == 15.0
    assert vecs["magic_pen_percent"][0] == pytest.approx(0.40)


def test_stat_aggregator_crit_item_as_cap_and_ability_haste():
    jinx = CHAMPION_SEED_DATA["Jinx"]
    ie = _get_item("3031")
    ldr = _get_item("3036")
    extra = {"name": "HasteAS", "stats": {"attack_speed": 0.50, "ability_haste": 25.0}}

    vecs = StatAggregator.compute_level_vectors(jinx["base_stats"], [ie, ldr, extra])

    assert vecs["crit_chance"][0] == pytest.approx(0.50)
    assert vecs["crit_damage_multiplier"][0] == pytest.approx(2.15)
    assert vecs["expected_aa_crit_multiplier"][0] == pytest.approx(1.575)
    assert vecs["ability_haste"][0] == pytest.approx(25.0)
    assert vecs["attack_speed"][0] == pytest.approx(0.938, abs=1e-3)

    cap_vecs = StatAggregator.compute_level_vectors(
        jinx["base_stats"], [{"name": "OverCap", "stats": {"attack_speed": 5.0}}]
    )
    assert cap_vecs["attack_speed"][0] == 2.5
    assert cap_vecs["attack_speed"][17] == 2.5


def test_damage_calculator_ability_haste_reduces_cooldown():
    ahri = CHAMPION_SEED_DATA["Ahri"]
    vecs_0 = StatAggregator.compute_level_vectors(ahri["base_stats"], [])
    vecs_25 = StatAggregator.compute_level_vectors(
        ahri["base_stats"], [{"name": "25 AH", "stats": {"ability_haste": 25.0}}]
    )
    vecs_100 = StatAggregator.compute_level_vectors(
        ahri["base_stats"], [{"name": "100 AH", "stats": {"ability_haste": 100.0}}]
    )

    q0 = DamageCalculator.compute_ability_damage_curve("Q", ahri["abilities"]["Q"], vecs_0)
    q25 = DamageCalculator.compute_ability_damage_curve("Q", ahri["abilities"]["Q"], vecs_25)
    q100 = DamageCalculator.compute_ability_damage_curve("Q", ahri["abilities"]["Q"], vecs_100)

    assert q0["cooldown"][0] == pytest.approx(7.0)
    assert q25["base_cooldown"][0] == pytest.approx(7.0)
    assert q25["cooldown"][0] == pytest.approx(5.6)
    assert q100["cooldown"][0] == pytest.approx(3.5)


def test_combat_simulator_crit_increases_dps_and_reduces_ttk():
    jinx = CHAMPION_SEED_DATA["Jinx"]
    ie = _get_item("3031")
    ldr = _get_item("3036")
    no_crit = [{"name": "PureADPen", "stats": {"ad": 105.0, "armor_pen_percent": 0.35}}]

    sim_crit = CombatSimulator.run_simulation("Jinx", jinx["base_stats"], jinx["abilities"], None, [ie, ldr], "squishy")
    sim_nocrit = CombatSimulator.run_simulation("Jinx", jinx["base_stats"], jinx["abilities"], None, no_crit, "squishy")

    assert sim_crit["level_curves"][17]["new_dps"] > sim_nocrit["level_curves"][17]["new_dps"]
    assert sim_crit["level_curves"][17]["new_ttk_sec"] < sim_nocrit["level_curves"][17]["new_ttk_sec"]


def test_combat_simulator_physical_and_magic_ehp_separation():
    ahri = CHAMPION_SEED_DATA["Ahri"]
    mr_buff = ChampionPatchDiff(
        champion_key="Ahri",
        stat_deltas=[StatDelta(stat_name=StatName.BASE_MR, old_value=30.0, new_value=36.0)],
    )
    armor_nerf = ChampionPatchDiff(
        champion_key="Ahri",
        stat_deltas=[StatDelta(stat_name=StatName.BASE_ARMOR, old_value=21.0, new_value=18.0)],
    )

    sim_mr = CombatSimulator.run_simulation("Ahri", ahri["base_stats"], ahri["abilities"], mr_buff, [], "squishy")
    sim_ar = CombatSimulator.run_simulation("Ahri", ahri["base_stats"], ahri["abilities"], armor_nerf, [], "squishy")

    assert sim_mr["summary"]["avg_ehp_delta_pct"] == 0.0
    assert sim_mr["summary"]["avg_magic_ehp_delta_pct"] > 0.0
    assert sim_ar["summary"]["avg_ehp_delta_pct"] < 0.0
    assert sim_ar["summary"]["avg_magic_ehp_delta_pct"] == 0.0


def test_combat_simulator_ability_buff_improves_burst_and_dps():
    ahri = CHAMPION_SEED_DATA["Ahri"]
    build = [_get_item("3089"), _get_item("4645")]
    q_buff = ChampionPatchDiff(
        champion_key="Ahri",
        ability_deltas=[
            AbilityDelta(
                slot=AbilitySlot.Q,
                old_base_damage=[80.0, 130.0, 180.0, 230.0, 280.0],
                new_base_damage=[90.0, 145.0, 200.0, 255.0, 310.0],
                old_cooldown=[7.0] * 5,
                new_cooldown=[6.5] * 5,
                scaling_changes=[
                    ScalingDelta(scaling_stat=ScalingStat.AP, old_ratio=0.90, new_ratio=1.05)
                ],
            )
        ],
    )

    sim = CombatSimulator.run_simulation("Ahri", ahri["base_stats"], ahri["abilities"], q_buff, build, "squishy")

    assert len(sim["level_curves"]) == 18
    assert sim["summary"]["avg_burst_delta_pct"] > 0.0
    assert sim["summary"]["avg_dps_delta_pct"] > 0.0
    assert sim["level_curves"][17]["ttk_diff_sec"] <= 0.0
