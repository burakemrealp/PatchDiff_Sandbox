from typing import Dict, List, Any, Optional
import numpy as np
from app.schemas.patch_contracts import ChampionPatchDiff
from app.engine.stat_aggregator import StatAggregator
from app.engine.damage_calculator import DamageCalculator, get_target_profile_vectors
from app.engine.game_rules import resolve_effective_rules
from app.engine.passive_and_rune_engine import PassiveAndRuneEngine


class CombatSimulator:
    """
    Compares pre-patch (N-1) and post-patch (N) parameters to compute
    full-combo Burst, sustained DPS, Time to Kill (TTK), and Effective HP (EHP)
    across champion levels 1-18 (or 1-20 for Top Lane).
    """

    @classmethod
    def run_simulation(
        cls,
        champion_key: str,
        base_stats: Dict[str, float],
        base_abilities: Dict[str, Any],
        patch_diff: ChampionPatchDiff | None,
        items: List[Dict[str, Any]] | None = None,
        target_profile_key: str = "squishy",
        keystone_key: Optional[str] = None,
        role: str = "mid",
        game_map: str = "sr",
    ) -> Dict[str, Any]:
        items = items or []
        rules = resolve_effective_rules(role=role, game_map=game_map)
        n_levels = int(rules["max_level"])
        target = get_target_profile_vectors(target_profile_key, n_levels)
        target_hp_vec = target["hp"]

        # 1. Compute pre-patch and post-patch stat vectors (Levels 1..18, or 1..20 for Top)
        old_stat_vecs = StatAggregator.compute_level_vectors(base_stats, items, max_level=n_levels)
        new_base_stats = StatAggregator.apply_patch_to_base_stats(base_stats, patch_diff)
        new_stat_vecs = StatAggregator.compute_level_vectors(new_base_stats, items, max_level=n_levels)

        # Apply in-combat stat-granting keystones (e.g., Conqueror, Lethal Tempo)
        old_stat_vecs = PassiveAndRuneEngine.apply_precombat_rune_stats(old_stat_vecs, keystone_key)
        new_stat_vecs = PassiveAndRuneEngine.apply_precombat_rune_stats(new_stat_vecs, keystone_key)

        # 2. Build pre-patch and post-patch ability dictionaries
        old_abilities = base_abilities
        new_abilities = DamageCalculator.apply_patch_to_abilities(base_abilities, patch_diff)

        # 3. Compute expected post-mitigation Auto Attack (AA) damage vectors (including crit)
        old_aa_net = DamageCalculator.compute_expected_aa_damage(old_stat_vecs, target_profile_key)
        new_aa_net = DamageCalculator.compute_expected_aa_damage(new_stat_vecs, target_profile_key)

        # 4. Compute damage and cooldown curves for Q, W, E, R abilities
        old_burst = old_aa_net * 2.0  # Include 2 woven auto-attacks in a full spell combo
        new_burst = new_aa_net * 2.0

        # Sustained DPS: Auto-attack DPS (AA_Dmg * Attack_Speed) + Ability rotation DPS
        old_dps = old_aa_net * old_stat_vecs["attack_speed"]
        new_dps = new_aa_net * new_stat_vecs["attack_speed"]

        ability_breakdown: Dict[str, Any] = {}

        for slot in ["Q", "W", "E", "R"]:
            if slot not in old_abilities:
                continue

            old_curve = DamageCalculator.compute_ability_damage_curve(
                slot, old_abilities[slot], old_stat_vecs, target_profile_key
            )
            new_curve = DamageCalculator.compute_ability_damage_curve(
                slot, new_abilities[slot], new_stat_vecs, target_profile_key
            )

            # Add ability net damage to full-combo burst
            old_burst += old_curve["net_damage"]
            new_burst += new_curve["net_damage"]

            # Ability DPS contribution using zero-safe np.divide
            old_ab_dps = np.divide(
                old_curve["net_damage"],
                old_curve["cooldown"],
                out=np.zeros_like(old_curve["net_damage"], dtype=np.float64),
                where=old_curve["cooldown"] > 0,
            )
            new_ab_dps = np.divide(
                new_curve["net_damage"],
                new_curve["cooldown"],
                out=np.zeros_like(new_curve["net_damage"], dtype=np.float64),
                where=new_curve["cooldown"] > 0,
            )

            # Ultimate (R) contributes at 25% weight to sustained DPS (cast once per skirmish); Q/W/E at 100%
            dps_weight = 0.25 if slot == "R" else 1.0
            old_dps += old_ab_dps * dps_weight
            new_dps += new_ab_dps * dps_weight

            # Percentage ability damage change (zero-safe division)
            ab_delta_pct = np.divide(
                (new_curve["net_damage"] - old_curve["net_damage"]) * 100.0,
                old_curve["net_damage"],
                out=np.zeros_like(old_curve["net_damage"], dtype=np.float64),
                where=old_curve["net_damage"] > 0,
            )

            ability_breakdown[slot] = {
                "name": new_abilities[slot].get("name", slot),
                "old_net_damage": np.round(old_curve["net_damage"], 1).tolist(),
                "new_net_damage": np.round(new_curve["net_damage"], 1).tolist(),
                "delta_percent": np.round(ab_delta_pct, 2).tolist(),
                "old_cooldown": old_curve["cooldown"].tolist(),
                "new_cooldown": new_curve["cooldown"].tolist(),
            }

        # 4.5. Apply modeled item passives and keystone rune effects
        old_p_burst, old_p_dps, old_ehp_bonus, _ = PassiveAndRuneEngine.evaluate_effects(
            stat_vecs=old_stat_vecs,
            aa_net=old_aa_net,
            base_burst=old_burst,
            base_dps=old_dps,
            items=items,
            target_profile_key=target_profile_key,
            keystone_key=keystone_key,
        )
        new_p_burst, new_p_dps, new_ehp_bonus, active_effects = PassiveAndRuneEngine.evaluate_effects(
            stat_vecs=new_stat_vecs,
            aa_net=new_aa_net,
            base_burst=new_burst,
            base_dps=new_dps,
            items=items,
            target_profile_key=target_profile_key,
            keystone_key=keystone_key,
        )
        old_burst += old_p_burst
        new_burst += new_p_burst
        old_dps += old_p_dps
        new_dps += new_p_dps

        # 5. Compute Time to Kill (TTK) in seconds
        old_ttk = np.where(
            old_burst >= target_hp_vec,
            np.round((target_hp_vec / np.maximum(1.0, old_burst)) * 1.2, 2),
            np.round(1.2 + (target_hp_vec - old_burst * 0.65) / np.maximum(1.0, old_dps), 2),
        )
        new_ttk = np.where(
            new_burst >= target_hp_vec,
            np.round((target_hp_vec / np.maximum(1.0, new_burst)) * 1.2, 2),
            np.round(1.2 + (target_hp_vec - new_burst * 0.65) / np.maximum(1.0, new_dps), 2),
        )

        # 6. Compute percentage delta vectors
        burst_delta_pct = ((new_burst - old_burst) / np.maximum(1.0, old_burst)) * 100.0
        dps_delta_pct = ((new_dps - old_dps) / np.maximum(1.0, old_dps)) * 100.0

        # Compute Physical (Armor) and Magic (MR) Effective HP (including passive/rune shield modifiers)
        ehp_old = old_stat_vecs["total_hp"] * (1.0 + old_stat_vecs["armor"] / 100.0) * (1.0 + old_ehp_bonus)
        ehp_new = new_stat_vecs["total_hp"] * (1.0 + new_stat_vecs["armor"] / 100.0) * (1.0 + new_ehp_bonus)
        ehp_delta_pct = ((ehp_new - ehp_old) / np.maximum(1.0, ehp_old)) * 100.0

        magic_ehp_old = old_stat_vecs["total_hp"] * (1.0 + old_stat_vecs["mr"] / 100.0) * (1.0 + old_ehp_bonus)
        magic_ehp_new = new_stat_vecs["total_hp"] * (1.0 + new_stat_vecs["mr"] / 100.0) * (1.0 + new_ehp_bonus)
        magic_ehp_delta_pct = ((magic_ehp_new - magic_ehp_old) / np.maximum(1.0, magic_ehp_old)) * 100.0

        # Build level 1..N time-series table for frontend charts
        level_series = []
        for i in range(n_levels):
            level_series.append(
                {
                    "level": i + 1,
                    "target_hp": round(float(target_hp_vec[i]), 1),
                    "old_burst": round(float(old_burst[i]), 1),
                    "new_burst": round(float(new_burst[i]), 1),
                    "burst_delta_pct": round(float(burst_delta_pct[i]), 2),
                    "old_dps": round(float(old_dps[i]), 1),
                    "new_dps": round(float(new_dps[i]), 1),
                    "dps_delta_pct": round(float(dps_delta_pct[i]), 2),
                    "old_ttk_sec": round(float(old_ttk[i]), 2),
                    "new_ttk_sec": round(float(new_ttk[i]), 2),
                    "ttk_diff_sec": round(float(new_ttk[i] - old_ttk[i]), 2),
                    "ehp_delta_pct": round(float(ehp_delta_pct[i]), 2),
                    "magic_ehp_delta_pct": round(float(magic_ehp_delta_pct[i]), 2),
                }
            )

        # Summary metrics (Early Game: Lvl 6, Mid Game: Lvl 11, Late Game: Lvl 18 [+ Top Lvl 20])
        summary_metrics = {
            "early_game_lvl6": level_series[5],
            "mid_game_lvl11": level_series[10],
            "late_game_lvl18": level_series[17],
            "avg_burst_delta_pct": round(float(np.mean(burst_delta_pct)), 2),
            "avg_dps_delta_pct": round(float(np.mean(dps_delta_pct)), 2),
            "avg_ehp_delta_pct": round(float(np.mean(ehp_delta_pct)), 2),
            "avg_magic_ehp_delta_pct": round(float(np.mean(magic_ehp_delta_pct)), 2),
        }
        if n_levels >= 20:
            summary_metrics["late_game_lvl20"] = level_series[19]

        return {
            "champion_key": champion_key,
            "target_profile": target_profile_key,
            "target_label": target["label"],
            "game_context": rules,
            "active_effects": active_effects,
            "summary": summary_metrics,
            "abilities": ability_breakdown,
            "level_curves": level_series,
        }
