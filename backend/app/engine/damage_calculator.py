from copy import deepcopy
from typing import Dict, Any
import numpy as np
from app.schemas.patch_contracts import ChampionPatchDiff


# Three target dummy defensive profiles scaled across levels 1 to 18
TARGET_PROFILES: Dict[str, Dict[str, Any]] = {
    "squishy": {
        "label": "Squishy Target (ADC / Mage)",
        "hp": np.linspace(600.0, 2100.0, 18),
        "armor": np.linspace(28.0, 85.0, 18),
        "mr": np.linspace(30.0, 52.0, 18),
    },
    "bruiser": {
        "label": "Bruiser / Fighter",
        "hp": np.linspace(650.0, 3300.0, 18),
        "armor": np.linspace(36.0, 145.0, 18),
        "mr": np.linspace(32.0, 110.0, 18),
    },
    "tank": {
        "label": "Heavy Tank (Frontline)",
        "hp": np.linspace(700.0, 4800.0, 18),
        "armor": np.linspace(45.0, 260.0, 18),
        "mr": np.linspace(35.0, 210.0, 18),
    },
}


def get_target_profile_vectors(target_profile_key: str, n_levels: int = 18) -> Dict[str, Any]:
    """
    Returns target dummy HP/Armor/MR vectors across levels 1..n_levels.
    When Top Role Quest pushes the attacker to Level 19-20, standard enemy targets remain
    at their Level 18 defensive cap, accurately modeling Top's level advantage.
    """
    base = TARGET_PROFILES.get(target_profile_key, TARGET_PROFILES["squishy"])
    if n_levels <= 18:
        return base

    extra = n_levels - 18
    extended: Dict[str, Any] = {"label": base["label"]}
    for key in ("hp", "armor", "mr"):
        arr = base[key]
        tail = np.full(extra, float(arr[-1]), dtype=np.float64)
        extended[key] = np.concatenate([arr, tail])
    return extended


# Standard skill-maxing order (Q -> W -> E max, R upgraded at levels 6, 11, and 16).
# Maps champion level (1..18) to 0-based ability rank index (0..4 for basic spells, 0..2 for R; -1 = locked).
ABILITY_RANK_CURVES: Dict[str, np.ndarray] = {
    "Q": np.array([0, 0, 1, 1, 2, 2, 3, 3, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4], dtype=int),
    "W": np.array([0, 0, 0, 0, 0, 0, 0, 1, 1, 2, 2, 3, 4, 4, 4, 4, 4, 4], dtype=int),
    "E": np.array([0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 2, 2, 3, 4], dtype=int),
    "R": np.array([-1, -1, -1, -1, -1, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 2, 2, 2], dtype=int),
}


class DamageCalculator:
    """
    Computes raw ability and auto-attack damage and applies Riot's armor/MR
    mitigation and penetration order to derive post-mitigation net damage.
    """

    @classmethod
    def apply_patch_to_abilities(
        cls, base_abilities: Dict[str, Any], patch_diff: ChampionPatchDiff | None
    ) -> Dict[str, Any]:
        """Applies AbilityDelta updates from a patch diff to a champion ability map."""
        modified = deepcopy(base_abilities)
        if not patch_diff:
            return modified

        for ab_delta in patch_diff.ability_deltas:
            slot = ab_delta.slot.value
            if slot not in modified:
                continue

            target_ab = modified[slot]

            if ab_delta.new_base_damage:
                target_ab["base_damage"] = [float(x) for x in ab_delta.new_base_damage]

            if ab_delta.new_cooldown:
                target_ab["cooldown"] = [float(x) for x in ab_delta.new_cooldown]

            for sc in ab_delta.scaling_changes:
                stat_key = sc.scaling_stat.value
                if "scaling" not in target_ab:
                    target_ab["scaling"] = {}
                target_ab["scaling"][stat_key] = float(sc.new_ratio)

        return modified

    @staticmethod
    def calculate_effective_resistance(
        target_resist: np.ndarray,
        percent_pen: np.ndarray,
        flat_pen: np.ndarray,
    ) -> np.ndarray:
        """
        Riot Games Penetration Order:
        1. Percentage penetration is applied first.
        2. Flat penetration (Lethality / Flat Magic Pen) is subtracted next (floored at 0).
        """
        after_percent = target_resist * (1.0 - percent_pen)
        effective = np.maximum(0.0, after_percent - flat_pen)
        return effective

    @classmethod
    def mitigate_damage(
        cls,
        raw_damage: np.ndarray,
        damage_type: str,
        attacker_vectors: Dict[str, np.ndarray],
        target_profile_key: str = "squishy",
    ) -> np.ndarray:
        """Reduces a raw damage vector (Levels 1..N) by the target's effective armor or MR."""
        if damage_type == "true":
            return np.round(raw_damage, 2)

        n_levels = len(raw_damage)
        target = get_target_profile_vectors(target_profile_key, n_levels)

        if damage_type == "physical":
            eff_resist = cls.calculate_effective_resistance(
                target_resist=target["armor"],
                percent_pen=attacker_vectors["armor_pen_percent"],
                flat_pen=attacker_vectors["lethality"],
            )
        else:  # magic
            eff_resist = cls.calculate_effective_resistance(
                target_resist=target["mr"],
                percent_pen=attacker_vectors["magic_pen_percent"],
                flat_pen=attacker_vectors["magic_pen_flat"],
            )

        multiplier = 100.0 / (100.0 + eff_resist)
        return np.round(raw_damage * multiplier, 2)

    @staticmethod
    def apply_ability_haste(
        base_cooldown: np.ndarray,
        ability_haste: np.ndarray,
    ) -> np.ndarray:
        """
        Riot Games Ability Haste formula:
        Effective Cooldown = Base Cooldown / (1 + Ability_Haste / 100),
        clamping the divisor at 0.25 to support negative ARAM Ability Haste safely.
        """
        divisor = np.maximum(0.25, 1.0 + ability_haste / 100.0)
        return np.where(base_cooldown > 0.0, base_cooldown / divisor, 0.0)

    @classmethod
    def compute_expected_aa_damage(
        cls,
        attacker_vectors: Dict[str, np.ndarray],
        target_profile_key: str = "squishy",
    ) -> np.ndarray:
        """
        Computes expected post-mitigation Auto Attack (AA) damage including critical strike
        chance and critical strike damage modifiers (e.g., Infinity Edge).
        """
        n_levels = len(attacker_vectors["total_ad"])
        crit_mult = attacker_vectors.get(
            "expected_aa_crit_multiplier", np.ones(n_levels, dtype=np.float64)
        )
        raw_aa = attacker_vectors["total_ad"] * crit_mult
        return cls.mitigate_damage(raw_aa, "physical", attacker_vectors, target_profile_key)

    @classmethod
    def compute_ability_damage_curve(
        cls,
        slot: str,
        ability_data: Dict[str, Any],
        attacker_vectors: Dict[str, np.ndarray],
        target_profile_key: str = "squishy",
    ) -> Dict[str, np.ndarray]:
        """
        Computes level 1..N vectors for a single ability (Q, W, E, or R):
        - raw_damage
        - net_damage (post-mitigation)
        - base_cooldown and effective cooldown
        """
        n_levels = len(attacker_vectors["levels"])
        base_curve = ABILITY_RANK_CURVES.get(slot, ABILITY_RANK_CURVES["Q"])
        if n_levels > len(base_curve):
            rank_curve = np.concatenate(
                [base_curve, np.full(n_levels - len(base_curve), base_curve[-1], dtype=int)]
            )
        else:
            rank_curve = base_curve[:n_levels]

        base_dmg_list = ability_data.get("base_damage", [0.0] * 5)
        cd_list = ability_data.get("cooldown", [10.0] * 5)
        scaling_dict = ability_data.get("scaling", {})
        damage_type = ability_data.get("damage_type", "magic")
        target = get_target_profile_vectors(target_profile_key, n_levels)

        # Build base damage and cooldown arrays across levels 1..N
        raw_base = np.zeros(n_levels, dtype=np.float64)
        cooldowns = np.zeros(n_levels, dtype=np.float64)

        for lvl_idx in range(n_levels):
            r_idx = int(rank_curve[lvl_idx])
            if r_idx < 0:  # Ultimate (R) is locked during levels 1-5
                raw_base[lvl_idx] = 0.0
                cooldowns[lvl_idx] = 0.0
            else:
                safe_dmg_idx = min(r_idx, len(base_dmg_list) - 1)
                safe_cd_idx = min(r_idx, len(cd_list) - 1)
                raw_base[lvl_idx] = float(base_dmg_list[safe_dmg_idx])
                cooldowns[lvl_idx] = float(cd_list[safe_cd_idx])

        # Add scaling damage from AP, Bonus AD, Total AD, Target Max HP, etc.
        scaling_bonus = np.zeros(n_levels, dtype=np.float64)
        for stat_name, ratio in scaling_dict.items():
            ratio_val = float(ratio)
            if stat_name == "ap":
                scaling_bonus += attacker_vectors["ap"] * ratio_val
            elif stat_name == "bonus_ad":
                scaling_bonus += attacker_vectors["bonus_ad"] * ratio_val
            elif stat_name == "total_ad":
                scaling_bonus += attacker_vectors["total_ad"] * ratio_val
            elif stat_name == "bonus_hp":
                scaling_bonus += attacker_vectors["bonus_hp"] * ratio_val
            elif stat_name == "armor":
                scaling_bonus += attacker_vectors["armor"] * ratio_val
            elif stat_name == "mr":
                scaling_bonus += attacker_vectors["mr"] * ratio_val
            elif stat_name == "target_max_hp":
                scaling_bonus += target["hp"] * ratio_val

        # Ensure locked ultimate ranks (levels 1-5) deal 0 total damage
        active_mask = (rank_curve >= 0).astype(np.float64)
        total_raw = (raw_base + scaling_bonus) * active_mask

        net_damage = cls.mitigate_damage(
            raw_damage=total_raw,
            damage_type=damage_type,
            attacker_vectors=attacker_vectors,
            target_profile_key=target_profile_key,
        )

        ability_haste = attacker_vectors.get("ability_haste", np.zeros(n_levels, dtype=np.float64))
        effective_cooldowns = cls.apply_ability_haste(cooldowns, ability_haste)

        return {
            "raw_damage": np.round(total_raw, 2),
            "net_damage": net_damage,
            "base_cooldown": np.round(cooldowns, 2),
            "cooldown": np.round(effective_cooldowns, 2),
        }
