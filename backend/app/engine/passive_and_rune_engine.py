from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from app.engine.damage_calculator import DamageCalculator, get_target_profile_vectors


def _level_scale(n_levels: int) -> np.ndarray:
    """Linear scaling vector: 0.0 at Level 1, 1.0 at Level 18 (extrapolated linearly for Levels 19-20)."""
    levels = np.arange(1, n_levels + 1, dtype=np.float64)
    return (levels - 1.0) / 17.0


# Supported Keystone runes metadata (also consumed by BuildOptimizerEngine)
SUPPORTED_KEYSTONES: Dict[str, Dict[str, Any]] = {
    "Electrocute": {"label": "Electrocute", "tree": "Domination", "archetypes": ["Mage", "Assassin"]},
    "DarkHarvest": {"label": "Dark Harvest", "tree": "Domination", "archetypes": ["Mage", "Assassin", "Marksman"]},
    "HailOfBlades": {"label": "Hail of Blades", "tree": "Domination", "archetypes": ["Assassin", "Marksman", "Fighter"]},
    "ArcaneComet": {"label": "Arcane Comet", "tree": "Sorcery", "archetypes": ["Mage", "Support"]},
    "SummonAery": {"label": "Summon Aery", "tree": "Sorcery", "archetypes": ["Mage", "Support"]},
    "PhaseRush": {"label": "Phase Rush", "tree": "Sorcery", "archetypes": ["Mage", "Fighter"]},
    "Conqueror": {"label": "Conqueror", "tree": "Precision", "archetypes": ["Fighter", "Assassin", "Mage"]},
    "LethalTempo": {"label": "Lethal Tempo", "tree": "Precision", "archetypes": ["Marksman", "Fighter"]},
    "PressTheAttack": {"label": "Press the Attack", "tree": "Precision", "archetypes": ["Marksman", "Fighter"]},
    "FleetFootwork": {"label": "Fleet Footwork", "tree": "Precision", "archetypes": ["Marksman", "Fighter", "Assassin"]},
    "FirstStrike": {"label": "First Strike", "tree": "Inspiration", "archetypes": ["Mage", "Assassin", "Marksman"]},
    "GraspOfTheUndying": {"label": "Grasp of the Undying", "tree": "Resolve", "archetypes": ["Tank", "Fighter"]},
    "Aftershock": {"label": "Aftershock", "tree": "Resolve", "archetypes": ["Tank", "Support"]},
}

# Modeled item passives (Riot Item ID -> display label)
MODELED_ITEM_PASSIVES: Dict[str, str] = {
    "3100": "Lich Bane (Spellblade)",
    "3078": "Trinity Force (Spellblade)",
    "6653": "Liandry's Torment (%HP Burn)",
    "2503": "Blackfire Torch (Burn)",
    "6655": "Luden's Companion (Fire)",
    "4646": "Stormsurge (Squall)",
    "3115": "Nashor's Tooth (On-Hit)",
    "3153": "Blade of the Ruined King (%HP On-Hit)",
    "6672": "Kraken Slayer (3rd Hit)",
    "3091": "Wit's End (Magic On-Hit)",
    "3124": "Guinsoo's Rageblade (Phantom Hit)",
    "4645": "Shadowflame (Low-HP Crit)",
    "3071": "Black Cleaver (Armor Shred)",
    "3157": "Zhonya's Hourglass (Stasis)",
    "3026": "Guardian Angel (Rebirth)",
    "3053": "Sterak's Gage (Lifeline Shield)",
    "3156": "Maw of Malmortius (Magic Shield)",
}


def _adaptive_damage_type(stat_vecs: Dict[str, np.ndarray]) -> str:
    """Adaptive Force / damage type: magic if AP > Bonus AD, otherwise physical."""
    if float(stat_vecs["ap"][0]) > float(stat_vecs["bonus_ad"][0]):
        return "magic"
    return "physical"


class PassiveAndRuneEngine:
    """
    Deterministically computes combat contributions of Keystone runes and key item passives
    to Burst, DPS, Auto Attacks, and Effective HP (EHP) across levels 1-18 (or 1-20).
    """

    @staticmethod
    def apply_precombat_rune_stats(
        stat_vecs: Dict[str, np.ndarray], keystone_key: Optional[str]
    ) -> Dict[str, np.ndarray]:
        """Applies in-combat stat-granting keystones such as Conqueror and Lethal Tempo to stat vectors."""
        if not keystone_key:
            return stat_vecs

        updated = {k: v.copy() if isinstance(v, np.ndarray) else v for k, v in stat_vecs.items()}
        scale_01 = _level_scale(len(updated["levels"]))

        if keystone_key == "Conqueror":
            # Average 8 stacks (12 max): 1.08..2.4 AD or 1.8..4.0 AP per stack by level
            is_ap = _adaptive_damage_type(updated) == "magic"
            if is_ap:
                bonus_ap = (1.8 + 2.2 * scale_01) * 8.0
                updated["ap"] = np.round(updated["ap"] + bonus_ap, 2)
            else:
                bonus_ad = (1.08 + 1.32 * scale_01) * 8.0
                updated["bonus_ad"] = np.round(updated["bonus_ad"] + bonus_ad, 2)
                updated["total_ad"] = np.round(updated["total_ad"] + bonus_ad, 2)

        elif keystone_key == "LethalTempo":
            # Average ~30%..45% attack speed ramp at 5 stacks (2.5 attack speed cap respected)
            bonus_as_ratio = 0.30 + 0.15 * np.minimum(1.0, scale_01)
            updated["attack_speed"] = np.round(
                np.minimum(2.5, updated["attack_speed"] * (1.0 + bonus_as_ratio)), 3
            )

        return updated

    @classmethod
    def evaluate_effects(
        cls,
        stat_vecs: Dict[str, np.ndarray],
        aa_net: np.ndarray,
        base_burst: np.ndarray,
        base_dps: np.ndarray,
        items: List[Dict[str, Any]],
        target_profile_key: str = "squishy",
        keystone_key: Optional[str] = None,
    ) -> Tuple[np.ndarray, np.ndarray, float, Dict[str, Any]]:
        """
        Evaluates all modeled item passives and the selected Keystone rune.
        Returns: (bonus_burst_vec, bonus_dps_vec, ehp_bonus_ratio, active_effects_meta)
        """
        n_levels = len(stat_vecs["levels"])
        scale_01 = _level_scale(n_levels)
        target = get_target_profile_vectors(target_profile_key, n_levels)
        target_hp = target["hp"]
        as_vec = stat_vecs["attack_speed"]
        ap_vec = stat_vecs["ap"]
        base_ad_vec = stat_vecs["base_ad"]
        bonus_ad_vec = stat_vecs["bonus_ad"]
        total_hp_vec = stat_vecs["total_hp"]
        bonus_hp_vec = stat_vecs["bonus_hp"]

        bonus_burst = np.zeros(n_levels, dtype=np.float64)
        bonus_dps = np.zeros(n_levels, dtype=np.float64)
        ehp_bonus_ratio = 0.0
        active_item_passives: List[str] = []

        # --- 1. ITEM PASSIVES ---
        seen_ids = set()
        for item in items:
            iid = str(item.get("item_id", ""))
            if not iid or iid in seen_ids:
                continue
            seen_ids.add(iid)

            if iid not in MODELED_ITEM_PASSIVES:
                continue

            if iid == "3100":  # Lich Bane
                raw = 0.75 * base_ad_vec + 0.40 * ap_vec
                net = DamageCalculator.mitigate_damage(raw, "magic", stat_vecs, target_profile_key)
                bonus_burst += net
                bonus_dps += net / 2.5

            elif iid == "3078":  # Trinity Force
                raw = 2.0 * base_ad_vec
                net = DamageCalculator.mitigate_damage(raw, "physical", stat_vecs, target_profile_key)
                bonus_burst += net
                bonus_dps += net / 2.5

            elif iid == "6653":  # Liandry's Torment (2% max HP/sec over 3s)
                raw_per_sec = 0.02 * target_hp
                net_per_sec = DamageCalculator.mitigate_damage(
                    raw_per_sec, "magic", stat_vecs, target_profile_key
                )
                bonus_burst += net_per_sec * 3.0
                bonus_dps += net_per_sec

            elif iid == "2503":  # Blackfire Torch (20 + 2% AP/sec over 3s)
                raw_per_sec = 20.0 + 0.02 * ap_vec
                net_per_sec = DamageCalculator.mitigate_damage(
                    raw_per_sec, "magic", stat_vecs, target_profile_key
                )
                bonus_burst += net_per_sec * 3.0
                bonus_dps += net_per_sec

            elif iid == "6655":  # Luden's Companion (single-target full fire proc)
                raw = 120.0 + 0.08 * ap_vec
                net = DamageCalculator.mitigate_damage(raw, "magic", stat_vecs, target_profile_key)
                bonus_burst += net
                bonus_dps += net / 10.0

            elif iid == "4646":  # Stormsurge
                raw = 125.0 + 0.10 * ap_vec
                net = DamageCalculator.mitigate_damage(raw, "magic", stat_vecs, target_profile_key)
                bonus_burst += net
                bonus_dps += net / 30.0

            elif iid == "3115":  # Nashor's Tooth (15 + 15% AP on-hit)
                raw_hit = 15.0 + 0.15 * ap_vec
                net_hit = DamageCalculator.mitigate_damage(
                    raw_hit, "magic", stat_vecs, target_profile_key
                )
                bonus_burst += net_hit * 2.0
                bonus_dps += net_hit * as_vec

            elif iid == "3153":  # Blade of the Ruined King (~4.5% avg target max HP physical on-hit)
                raw_hit = 0.045 * target_hp
                net_hit = DamageCalculator.mitigate_damage(
                    raw_hit, "physical", stat_vecs, target_profile_key
                )
                bonus_burst += net_hit * 2.0
                bonus_dps += net_hit * as_vec

            elif iid == "6672":  # Kraken Slayer (150..200 physical every 3rd attack)
                raw_3rd = 150.0 + 50.0 * scale_01
                net_3rd = DamageCalculator.mitigate_damage(
                    raw_3rd, "physical", stat_vecs, target_profile_key
                )
                bonus_burst += net_3rd * (2.0 / 3.0)
                bonus_dps += (net_3rd / 3.0) * as_vec

            elif iid == "3091":  # Wit's End (45 magic on-hit)
                raw_hit = np.full(n_levels, 45.0, dtype=np.float64)
                net_hit = DamageCalculator.mitigate_damage(
                    raw_hit, "magic", stat_vecs, target_profile_key
                )
                bonus_burst += net_hit * 2.0
                bonus_dps += net_hit * as_vec

            elif iid == "3124":  # Guinsoo's Rageblade (30 magic on-hit + Seething Strike phantom hit)
                raw_hit = np.full(n_levels, 30.0, dtype=np.float64)
                net_hit = DamageCalculator.mitigate_damage(
                    raw_hit, "magic", stat_vecs, target_profile_key
                )
                bonus_burst += net_hit * 2.5
                bonus_dps += net_hit * as_vec * 1.25

            elif iid == "4645":  # Shadowflame (+6% average effective magic crit multiplier below 40% HP)
                bonus_burst += base_burst * 0.06
                bonus_dps += base_dps * 0.06

            elif iid == "3071":  # Black Cleaver (~18% average armor shred amplification)
                armor_factor = target["armor"] / (100.0 + target["armor"])
                amp = 0.18 * armor_factor
                bonus_burst += base_burst * (amp * 0.5)
                bonus_dps += base_dps * amp

            elif iid in ("3157", "3026"):  # Zhonya's Hourglass / Guardian Angel
                ehp_bonus_ratio += 0.12

            elif iid in ("3053", "3156"):  # Sterak's Gage / Maw of Malmortius Lifeline shield
                ehp_bonus_ratio += 0.15

            active_item_passives.append(MODELED_ITEM_PASSIVES[iid])

        # --- 2. KEYSTONE RUNE EFFECT ---
        keystone_label: Optional[str] = None
        if keystone_key and keystone_key in SUPPORTED_KEYSTONES:
            keystone_label = SUPPORTED_KEYSTONES[keystone_key]["label"]
            adapt_type = _adaptive_damage_type(stat_vecs)

            if keystone_key == "Electrocute":
                raw = 70.0 + 170.0 * scale_01 + 0.10 * bonus_ad_vec + 0.05 * ap_vec
                cd = np.full(n_levels, 20.0, dtype=np.float64)
                net = DamageCalculator.mitigate_damage(raw, adapt_type, stat_vecs, target_profile_key)
                bonus_burst += net
                bonus_dps += net / cd

            elif keystone_key == "DarkHarvest":
                est_stacks = 2.0 + 10.0 * scale_01
                raw = 20.0 + 40.0 * scale_01 + est_stacks * 9.0 + 0.10 * bonus_ad_vec + 0.05 * ap_vec
                net = DamageCalculator.mitigate_damage(raw, adapt_type, stat_vecs, target_profile_key)
                bonus_burst += net
                bonus_dps += net / 35.0

            elif keystone_key == "ArcaneComet":
                raw = 30.0 + 100.0 * scale_01 + 0.10 * bonus_ad_vec + 0.05 * ap_vec
                cd = np.maximum(8.0, 20.0 - 12.0 * scale_01)
                net = DamageCalculator.mitigate_damage(raw, adapt_type, stat_vecs, target_profile_key)
                bonus_burst += net
                bonus_dps += net / cd

            elif keystone_key == "SummonAery":
                raw = 10.0 + 40.0 * scale_01 + 0.10 * bonus_ad_vec + 0.05 * ap_vec
                net = DamageCalculator.mitigate_damage(raw, adapt_type, stat_vecs, target_profile_key)
                bonus_burst += net
                bonus_dps += net / 3.5

            elif keystone_key == "HailOfBlades":
                # +1.5 extra auto-attacks in short burst window
                bonus_burst += aa_net * 1.5
                bonus_dps += (aa_net * 1.5) / 10.0

            elif keystone_key == "PressTheAttack":
                raw = 40.0 + 120.0 * scale_01
                net = DamageCalculator.mitigate_damage(raw, adapt_type, stat_vecs, target_profile_key)
                bonus_burst += net + base_burst * 0.04
                bonus_dps += net / 6.0 + base_dps * 0.08

            elif keystone_key == "FirstStrike":
                # +7% true damage amplification on burst combo
                bonus_burst += base_burst * 0.07
                bonus_dps += (base_burst * 0.07) / 20.0

            elif keystone_key == "LethalTempo":
                raw_hit = 9.0 + 21.0 * scale_01
                net_hit = DamageCalculator.mitigate_damage(
                    raw_hit, adapt_type, stat_vecs, target_profile_key
                )
                bonus_burst += net_hit * 2.0
                bonus_dps += net_hit * as_vec

            elif keystone_key == "Conqueror":
                ehp_bonus_ratio += 0.05

            elif keystone_key == "FleetFootwork":
                ehp_bonus_ratio += 0.06

            elif keystone_key == "PhaseRush":
                ehp_bonus_ratio += 0.04

            elif keystone_key == "GraspOfTheUndying":
                raw = 0.035 * total_hp_vec
                net = DamageCalculator.mitigate_damage(raw, "magic", stat_vecs, target_profile_key)
                bonus_burst += net
                bonus_dps += net / 4.0
                ehp_bonus_ratio += 0.07

            elif keystone_key == "Aftershock":
                raw = 25.0 + 95.0 * scale_01 + 0.08 * bonus_hp_vec
                net = DamageCalculator.mitigate_damage(raw, "magic", stat_vecs, target_profile_key)
                bonus_burst += net
                bonus_dps += net / 20.0
                ehp_bonus_ratio += 0.12

        meta = {
            "keystone": keystone_key,
            "keystone_label": keystone_label,
            "item_passives": active_item_passives,
            "ehp_bonus_pct": round(ehp_bonus_ratio * 100.0, 2),
        }
        return bonus_burst, bonus_dps, ehp_bonus_ratio, meta
