from copy import deepcopy
from typing import Dict, List, Any
import numpy as np
from app.schemas.patch_contracts import ChampionPatchDiff


class StatAggregator:
    """
    Uses NumPy vectorization to compute all champion stats across levels 1-18
    (or 1-20 for Top), item build contributions, and patch deltas simultaneously.
    """

    # Level vector from 1 to 18: [1, 2, ..., 18]
    LEVELS = np.arange(1, 19, dtype=np.float64)

    # Official Riot Games per-level growth multiplier formula: (L - 1) * (0.7025 + 0.0175 * (L - 1))
    GROWTH_MULTIPLIER = (LEVELS - 1.0) * (0.7025 + 0.0175 * (LEVELS - 1.0))

    BASE_CRIT_DAMAGE_MULTIPLIER = 1.75
    MAX_ATTACK_SPEED = 2.5

    @classmethod
    def apply_patch_to_base_stats(
        cls, base_stats: Dict[str, float], patch_diff: ChampionPatchDiff | None
    ) -> Dict[str, float]:
        """Applies StatDelta modifications from a patch diff to champion base stats."""
        modified = deepcopy(base_stats)
        if not patch_diff:
            return modified

        for delta in patch_diff.stat_deltas:
            stat_key = delta.stat_name.value
            if stat_key in modified:
                modified[stat_key] = float(delta.new_value)

        return modified

    @classmethod
    def compute_level_vectors(
        cls,
        base_stats: Dict[str, float],
        items: List[Dict[str, Any]] | None = None,
        max_level: int = 18,
    ) -> Dict[str, np.ndarray]:
        """
        Computes vectorized stat curves across levels 1..max_level (18, or 20 for Top Role Quest)
        given base champion stats and an item list.
        """
        items = items or []
        n_levels = max(18, int(max_level))
        if n_levels == 18:
            levels = cls.LEVELS
            growth_mult = cls.GROWTH_MULTIPLIER
        else:
            levels = np.arange(1, n_levels + 1, dtype=np.float64)
            growth_mult = (levels - 1.0) * (0.7025 + 0.0175 * (levels - 1.0))

        # 1. Aggregate flat item stats
        bonus_hp = sum(float(item.get("stats", {}).get("hp", 0.0)) for item in items)
        bonus_ad = sum(float(item.get("stats", {}).get("ad", 0.0)) for item in items)
        raw_ap = sum(float(item.get("stats", {}).get("ap", 0.0)) for item in items)
        ap_mult = sum(float(item.get("stats", {}).get("ap_multiplier", 0.0)) for item in items)
        bonus_armor = sum(float(item.get("stats", {}).get("armor", 0.0)) for item in items)
        bonus_mr = sum(float(item.get("stats", {}).get("mr", 0.0)) for item in items)
        ability_haste = max(
            0.0, sum(float(item.get("stats", {}).get("ability_haste", 0.0)) for item in items)
        )

        # Attack speed bonus from items (decimal format: 0.35 for +35%)
        item_as_bonus = sum(
            float(
                item.get("stats", {}).get(
                    "attack_speed",
                    item.get("stats", {}).get("attack_speed_percent", 0.0),
                )
            )
            for item in items
        )

        # Critical strike chance (capped at 100% = 1.0) and crit damage modifier (e.g., Infinity Edge +0.40)
        crit_chance = min(
            1.0,
            max(0.0, sum(float(item.get("stats", {}).get("crit_chance", 0.0)) for item in items)),
        )
        crit_damage_bonus = max(
            0.0,
            sum(float(item.get("stats", {}).get("crit_damage_bonus", 0.0)) for item in items),
        )
        crit_damage_mult = cls.BASE_CRIT_DAMAGE_MULTIPLIER + crit_damage_bonus
        expected_aa_crit_mult = 1.0 + crit_chance * (crit_damage_mult - 1.0)

        # Apply percentage AP multipliers (e.g., Rabadon's Deathcap)
        total_ap_scalar = raw_ap * (1.0 + ap_mult)

        # Flat & percentage armor/magic penetration values
        lethality = sum(float(item.get("stats", {}).get("lethality", 0.0)) for item in items)
        magic_pen_flat = sum(float(item.get("stats", {}).get("magic_pen_flat", 0.0)) for item in items)

        # Percentage penetration stacks multiplicatively: 1 - prod(1 - p_i)
        armor_pen_pct = 1.0 - np.prod(
            [1.0 - float(item.get("stats", {}).get("armor_pen_percent", 0.0)) for item in items]
        )
        magic_pen_pct = 1.0 - np.prod(
            [1.0 - float(item.get("stats", {}).get("magic_pen_percent", 0.0)) for item in items]
        )

        # 2. Vectorized calculations across levels 1..max_level
        base_hp_vec = base_stats["base_hp"] + base_stats["hp_growth"] * growth_mult
        base_ad_vec = base_stats["base_ad"] + base_stats["ad_growth"] * growth_mult
        base_armor_vec = base_stats["base_armor"] + base_stats["armor_growth"] * growth_mult
        base_mr_vec = base_stats["base_mr"] + base_stats["mr_growth"] * growth_mult

        # Attack Speed: Base_AS * (1 + (AS_Growth * Growth_Mult) / 100 + Item_AS_Bonus), capped at 2.5
        as_bonus_pct = (base_stats["attack_speed_growth"] * growth_mult) / 100.0 + item_as_bonus
        attack_speed_vec = np.minimum(
            cls.MAX_ATTACK_SPEED, base_stats["base_attack_speed"] * (1.0 + as_bonus_pct)
        )

        return {
            "levels": levels,
            "base_hp": np.round(base_hp_vec, 2),
            "bonus_hp": np.full(n_levels, bonus_hp, dtype=np.float64),
            "total_hp": np.round(base_hp_vec + bonus_hp, 2),
            "base_ad": np.round(base_ad_vec, 2),
            "bonus_ad": np.full(n_levels, bonus_ad, dtype=np.float64),
            "total_ad": np.round(base_ad_vec + bonus_ad, 2),
            "ap": np.full(n_levels, round(total_ap_scalar, 2), dtype=np.float64),
            "armor": np.round(base_armor_vec + bonus_armor, 2),
            "mr": np.round(base_mr_vec + bonus_mr, 2),
            "attack_speed": np.round(attack_speed_vec, 3),
            "ability_haste": np.full(n_levels, round(ability_haste, 2), dtype=np.float64),
            "crit_chance": np.full(n_levels, round(crit_chance, 4), dtype=np.float64),
            "crit_damage_multiplier": np.full(n_levels, round(crit_damage_mult, 4), dtype=np.float64),
            "expected_aa_crit_multiplier": np.full(n_levels, round(expected_aa_crit_mult, 4), dtype=np.float64),
            "lethality": np.full(n_levels, lethality, dtype=np.float64),
            "armor_pen_percent": np.full(n_levels, round(float(armor_pen_pct), 4), dtype=np.float64),
            "magic_pen_flat": np.full(n_levels, magic_pen_flat, dtype=np.float64),
            "magic_pen_percent": np.full(n_levels, round(float(magic_pen_pct), 4), dtype=np.float64),
        }
