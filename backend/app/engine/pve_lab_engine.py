from typing import Any, Dict, List, Optional
import numpy as np

from app.engine.damage_calculator import ABILITY_RANK_CURVES, DamageCalculator
from app.engine.game_rules import resolve_effective_rules
from app.engine.passive_and_rune_engine import PassiveAndRuneEngine
from app.engine.stat_aggregator import StatAggregator
from app.services.aram_balance_service import AramBalanceService

WAVECLEAR_CHECKPOINTS: List[Dict[str, Any]] = [
    {"minute": 5, "level": 5, "caster_hp": 320.0, "melee_hp": 525.0, "cannon_hp": 1050.0},
    {"minute": 9, "level": 9, "caster_hp": 368.0, "melee_hp": 645.0, "cannon_hp": 1380.0},
    {"minute": 14, "level": 11, "caster_hp": 428.0, "melee_hp": 815.0, "cannon_hp": 1820.0},
]

EPIC_MONSTERS: List[Dict[str, Any]] = [
    {"key": "dragon", "name": "Elemental Dragon", "level": 9, "hp": 5730.0, "armor": 21.0, "mr": 30.0},
    {"key": "atakhan", "name": "Atakhan", "level": 13, "hp": 9800.0, "armor": 90.0, "mr": 70.0},
    {"key": "baron", "name": "Baron Nashor", "level": 16, "hp": 13800.0, "armor": 120.0, "mr": 70.0},
]


class PvELabEngine:
    """
    Computes deterministic League of Legends PvE metrics:
      1. Minion Waveclear Breakpoints at Minutes 5, 9, and 14 (exact AP/AD caster one-shot thresholds),
      2. Epic Monster Solo Kill Speeds (Elemental Dragon, Atakhan, Baron Nashor) with riot monster caps.
    """

    @staticmethod
    def _compute_waveclear_proc_coefficients(item_ids: set[str], bonus_hp_val: float) -> Dict[str, float]:
        base_proc = 0.0
        ap_ratio = 0.0
        total_ad_ratio = 0.0

        if "6655" in item_ids:  # Luden's Companion
            base_proc += 75.0
            ap_ratio += 0.05
        if "2503" in item_ids:  # Blackfire Torch
            base_proc += 60.0
            ap_ratio += 0.06
        if "3087" in item_ids:  # Statikk Shiv
            base_proc += 90.0
        if item_ids & {"6698", "3074", "3748"}:  # Hydra cleave
            total_ad_ratio += 0.40
        if item_ids & {"6664", "3068"}:  # Immolate AoE burn
            base_proc += 20.0 + bonus_hp_val * 0.0175

        return {
            "base_proc": base_proc,
            "ap_ratio": ap_ratio,
            "total_ad_ratio": total_ad_ratio,
        }

    @staticmethod
    def _eval_spell_vs_minion(
        slot: str,
        ability_data: Dict[str, Any],
        stat_vecs: Dict[str, np.ndarray],
        lvl_idx: int,
        aram_dmg_dealt: float,
    ) -> Dict[str, Any]:
        base_curve = ABILITY_RANK_CURVES.get(slot, ABILITY_RANK_CURVES["Q"])
        r_idx = int(base_curve[min(lvl_idx, len(base_curve) - 1)])
        if r_idx < 0:
            return {
                "slot": slot,
                "name": ability_data.get("name", slot),
                "base_damage": 0.0,
                "raw_damage": 0.0,
                "cooldown": 0.0,
                "scaling": {},
            }

        base_dmg_list = ability_data.get("base_damage") or [0.0]
        cd_list = ability_data.get("cooldown") or [10.0]
        scaling = ability_data.get("scaling") or {}

        base_dmg = float(base_dmg_list[min(r_idx, len(base_dmg_list) - 1)])
        base_cd = float(cd_list[min(r_idx, len(cd_list) - 1)])

        scaling_dmg = 0.0
        for s_name, ratio in scaling.items():
            r_val = float(ratio)
            if s_name in ("ap", "bonus_ad", "total_ad", "bonus_hp", "armor", "mr"):
                scaling_dmg += float(stat_vecs[s_name][lvl_idx]) * r_val

        total_dmg = (base_dmg + scaling_dmg) * aram_dmg_dealt
        ah_val = float(stat_vecs["ability_haste"][lvl_idx])
        eff_cd = float(
            DamageCalculator.apply_ability_haste(
                np.array([base_cd], dtype=np.float64),
                np.array([ah_val], dtype=np.float64),
            )[0]
        )

        return {
            "slot": slot,
            "name": ability_data.get("name", slot),
            "base_damage": round(base_dmg, 2),
            "raw_damage": round(total_dmg, 2),
            "cooldown": round(eff_cd, 2),
            "scaling": {k: float(v) for k, v in scaling.items()},
        }

    @classmethod
    def evaluate(
        cls,
        champion_key: str,
        champion_name: str,
        base_stats: Dict[str, float],
        abilities: Dict[str, Any],
        items: Optional[List[Dict[str, Any]]] = None,
        keystone_key: Optional[str] = None,
        role: str = "mid",
        game_map: str = "sr",
        aram_modifiers_override: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Evaluates Minion Waveclear (5/9/14 min) and Epic Monster solo kill speeds."""
        items = items or []
        rules = dict(resolve_effective_rules(role=role, game_map=game_map))
        n_levels = max(16, int(rules["max_level"]))

        aram_mods: Optional[Dict[str, Any]] = None
        if rules["game_map"] == "aram":
            aram_mods = aram_modifiers_override or AramBalanceService.get_champion_aram_modifiers(champion_key)
            rules["aram_modifiers"] = aram_mods
        else:
            rules["aram_modifiers"] = None

        stat_vecs = StatAggregator.compute_level_vectors(base_stats, items, max_level=n_levels)
        stat_vecs = PassiveAndRuneEngine.apply_precombat_rune_stats(stat_vecs, keystone_key)

        if aram_mods:
            aram_ah = float(aram_mods.get("ability_haste", 0.0))
            aram_as_mult = max(0.5, float(aram_mods.get("total_as", 1.0)))
            if abs(aram_ah) > 1e-4:
                stat_vecs["ability_haste"] = np.round(stat_vecs["ability_haste"] + aram_ah, 2)
            if abs(aram_as_mult - 1.0) > 1e-4:
                stat_vecs["attack_speed"] = np.round(np.minimum(2.5, stat_vecs["attack_speed"] * aram_as_mult), 3)

        aram_dmg_dealt = float(aram_mods.get("dmg_dealt", 1.0)) if aram_mods else 1.0
        item_ids = {str(it.get("item_id", "")) for it in items}

        # Pick primary basic waveclear spell at Level 9 (8th zero-based index)
        lvl9_spells: Dict[str, Dict[str, Any]] = {}
        for slot in ("Q", "W", "E"):
            if slot in abilities:
                lvl9_spells[slot] = cls._eval_spell_vs_minion(
                    slot, abilities[slot], stat_vecs, 8, aram_dmg_dealt
                )

        if lvl9_spells:
            primary_slot = max(lvl9_spells.keys(), key=lambda s: lvl9_spells[s]["raw_damage"])
        else:
            primary_slot = "Q"

        waveclear_rows: List[Dict[str, Any]] = []
        for cp in WAVECLEAR_CHECKPOINTS:
            lvl_idx = cp["level"] - 1
            proc_cfg = cls._compute_waveclear_proc_coefficients(
                item_ids, float(stat_vecs["bonus_hp"][lvl_idx])
            )
            cur_ap = float(stat_vecs["ap"][lvl_idx])
            cur_total_ad = float(stat_vecs["total_ad"][lvl_idx])
            item_proc_dmg = (
                proc_cfg["base_proc"]
                + proc_cfg["ap_ratio"] * cur_ap
                + proc_cfg["total_ad_ratio"] * cur_total_ad
            ) * aram_dmg_dealt

            spells_at_cp: Dict[str, Dict[str, Any]] = {}
            for slot in ("Q", "W", "E"):
                if slot in abilities:
                    spells_at_cp[slot] = cls._eval_spell_vs_minion(
                        slot, abilities[slot], stat_vecs, lvl_idx, aram_dmg_dealt
                    )

            primary_info = spells_at_cp.get(
                primary_slot,
                {"slot": primary_slot, "name": primary_slot, "base_damage": 0.0, "raw_damage": 0.0, "cooldown": 8.0, "scaling": {}},
            )
            spell_dmg = float(primary_info["raw_damage"])
            total_hit_dmg = round(spell_dmg + item_proc_dmg, 1)
            caster_hp = float(cp["caster_hp"])
            can_oneshot = total_hit_dmg >= caster_hp
            damage_margin = round(total_hit_dmg - caster_hp, 1)

            # Determine exact missing AP/AD threshold to one-shot caster minions
            scaling_map = primary_info.get("scaling") or {}
            dominant_stat: Optional[str] = None
            dominant_ratio = 0.0
            for candidate_stat in ("ap", "bonus_ad", "total_ad"):
                r_val = float(scaling_map.get(candidate_stat, 0.0))
                if r_val > dominant_ratio:
                    dominant_ratio = r_val
                    dominant_stat = candidate_stat

            current_stat_val = 0.0
            required_stat_val: Optional[float] = None
            missing_stat_val = 0.0
            if dominant_stat and dominant_ratio > 0.0:
                current_stat_val = round(float(stat_vecs[dominant_stat][lvl_idx]), 1)
                proc_stat_ratio = (
                    proc_cfg["ap_ratio"] * aram_dmg_dealt
                    if dominant_stat == "ap"
                    else (
                        proc_cfg["total_ad_ratio"] * aram_dmg_dealt
                        if dominant_stat in ("bonus_ad", "total_ad")
                        else 0.0
                    )
                )
                effective_ratio = dominant_ratio * aram_dmg_dealt + proc_stat_ratio
                # Subtract current stat contribution from total_hit_dmg to isolate flat base + other scalings
                flat_dmg = total_hit_dmg - effective_ratio * current_stat_val
                needed_total = max(0.0, (caster_hp - flat_dmg) / effective_ratio)
                required_stat_val = round(needed_total, 1)
                missing_stat_val = 0.0 if can_oneshot else round(max(0.0, needed_total - current_stat_val), 1)

            # Estimate seconds to clear a full standard 6-minion wave (3 melee + 3 caster)
            full_wave_hp = 3.0 * float(cp["melee_hp"]) + 3.0 * caster_hp
            aa_crit_mult = float(stat_vecs["expected_aa_crit_multiplier"][lvl_idx])
            aa_dps = cur_total_ad * aa_crit_mult * float(stat_vecs["attack_speed"][lvl_idx]) * aram_dmg_dealt
            spell_aoe_dps = sum(
                (float(sp["raw_damage"]) / max(1.0, float(sp["cooldown"]))) * 2.2
                for sp in spells_at_cp.values()
                if float(sp["raw_damage"]) > 0.0
            ) + (item_proc_dmg / 3.0)
            full_wave_clear_sec = round(full_wave_hp / max(25.0, spell_aoe_dps + aa_dps), 2)

            waveclear_rows.append(
                {
                    "minute": cp["minute"],
                    "champion_level": cp["level"],
                    "caster_hp": caster_hp,
                    "melee_hp": cp["melee_hp"],
                    "cannon_hp": cp["cannon_hp"],
                    "primary_slot": primary_slot,
                    "primary_spell_name": primary_info["name"],
                    "spell_damage": round(spell_dmg, 1),
                    "item_proc_damage": round(item_proc_dmg, 1),
                    "total_hit_damage": total_hit_dmg,
                    "can_oneshot_caster": can_oneshot,
                    "damage_margin": damage_margin,
                    "scaling_stat": dominant_stat,
                    "current_stat_value": current_stat_val,
                    "required_stat_value": required_stat_val,
                    "missing_stat_value": missing_stat_val,
                    "full_wave_clear_sec": full_wave_clear_sec,
                    "spells": spells_at_cp,
                }
            )

        # Evaluate Epic Monster Objective solo-kill benchmarks
        objectives: List[Dict[str, Any]] = []
        for mon in EPIC_MONSTERS:
            idx = min(mon["level"] - 1, n_levels - 1)
            armor_arr = np.array([mon["armor"]], dtype=np.float64)
            mr_arr = np.array([mon["mr"]], dtype=np.float64)

            eff_armor = float(
                DamageCalculator.calculate_effective_resistance(
                    armor_arr,
                    np.array([float(stat_vecs["armor_pen_percent"][idx])]),
                    np.array([float(stat_vecs["lethality"][idx])]),
                )[0]
            )
            eff_mr = float(
                DamageCalculator.calculate_effective_resistance(
                    mr_arr,
                    np.array([float(stat_vecs["magic_pen_percent"][idx])]),
                    np.array([float(stat_vecs["magic_pen_flat"][idx])]),
                )[0]
            )
            phys_mult = 100.0 / (100.0 + eff_armor)
            mag_mult = 100.0 / (100.0 + eff_mr)

            cur_as = float(stat_vecs["attack_speed"][idx])
            cur_ap = float(stat_vecs["ap"][idx])
            cur_total_ad = float(stat_vecs["total_ad"][idx])
            cur_bonus_ad = float(stat_vecs["bonus_ad"][idx])
            cur_crit_mult = float(stat_vecs["expected_aa_crit_multiplier"][idx])

            aa_dps = cur_total_ad * cur_crit_mult * cur_as * phys_mult

            ab_dps = 0.0
            for slot in ("Q", "W", "E", "R"):
                if slot not in abilities:
                    continue
                ab = abilities[slot]
                curve = ABILITY_RANK_CURVES.get(slot, ABILITY_RANK_CURVES["Q"])
                r_idx = int(curve[min(idx, len(curve) - 1)])
                if r_idx < 0:
                    continue
                base_list = ab.get("base_damage") or [0.0]
                cd_list = ab.get("cooldown") or [10.0]
                base_d = float(base_list[min(r_idx, len(base_list) - 1)])
                base_cd = float(cd_list[min(r_idx, len(cd_list) - 1)])
                scaling = ab.get("scaling") or {}

                scale_d = 0.0
                for s_name, ratio in scaling.items():
                    r_val = float(ratio)
                    if s_name in ("ap", "bonus_ad", "total_ad", "bonus_hp", "armor", "mr"):
                        scale_d += float(stat_vecs[s_name][idx]) * r_val
                    elif s_name == "target_max_hp":
                        scale_d += min(100.0, float(mon["hp"]) * r_val)

                raw_d = base_d + scale_d
                dtype = ab.get("damage_type", "magic")
                net_d = raw_d * (1.0 if dtype == "true" else (phys_mult if dtype == "physical" else mag_mult))
                eff_cd = float(
                    DamageCalculator.apply_ability_haste(
                        np.array([base_cd], dtype=np.float64),
                        np.array([float(stat_vecs["ability_haste"][idx])], dtype=np.float64),
                    )[0]
                )
                weight = 0.25 if slot == "R" else 1.0
                if eff_cd > 0.0:
                    ab_dps += (net_d / eff_cd) * weight

            # Monster-capped item passive DPS
            item_mon_dps = 0.0
            if "3153" in item_ids:  # BotRK monster damage cap (100 pre-mitigation per hit)
                botrk_hit = min(100.0, float(mon["hp"]) * 0.05)
                item_mon_dps += botrk_hit * cur_as * phys_mult
            if "6653" in item_ids:  # Liandry monster burn cap (~80 pre-mitigation DPS)
                item_mon_dps += 80.0 * mag_mult
            if "6672" in item_ids:  # Kraken Slayer
                item_mon_dps += ((150.0 + 0.15 * cur_bonus_ad) / 3.0) * cur_as * phys_mult
            if "3115" in item_ids:  # Nashor's Tooth
                item_mon_dps += (15.0 + 0.15 * cur_ap) * cur_as * mag_mult
            if "3091" in item_ids:  # Wit's End
                item_mon_dps += 45.0 * cur_as * mag_mult
            if "3124" in item_ids:  # Guinsoo's Rageblade
                item_mon_dps += 30.0 * cur_as * mag_mult

            sustained_dps = round((aa_dps + ab_dps + item_mon_dps) * aram_dmg_dealt, 1)
            kill_sec = round(float(mon["hp"]) / max(1.0, sustained_dps), 2)
            tier = "FAST" if kill_sec < 22.0 else ("MODERATE" if kill_sec <= 40.0 else "SLOW")

            objectives.append(
                {
                    "monster_key": mon["key"],
                    "monster_name": mon["name"],
                    "reference_level": mon["level"],
                    "monster_hp": mon["hp"],
                    "armor": mon["armor"],
                    "mr": mon["mr"],
                    "sustained_dps": sustained_dps,
                    "solo_kill_time_sec": kill_sec,
                    "speed_tier": tier,
                    "speed_label": tier,
                }
            )

        return {
            "champion_key": champion_key,
            "champion_name": champion_name,
            "game_context": rules,
            "aram_modifiers": aram_mods or AramBalanceService.get_champion_aram_modifiers(champion_key),
            "waveclear_breakpoints": waveclear_rows,
            "objective_benchmarks": objectives,
            "items": [
                {
                    "item_id": str(i.get("item_id", "")),
                    "name": i.get("name", ""),
                    "gold_total": int(i.get("gold_total", 0)),
                    "icon_url": i.get("icon_url"),
                }
                for i in items
            ],
        }
