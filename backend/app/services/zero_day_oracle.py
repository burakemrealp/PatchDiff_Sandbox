import time
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy.orm import Session

from app.core.versioning import to_display_version
from app.engine.build_optimizer import (
    FIRST_ITEM_PRIORITY_IDS,
    LATE_CAPSTONE_IDS,
    _has_unique_conflict,
    filter_candidate_items,
    infer_champion_profile,
    order_build_items,
    select_candidate_keystones,
    select_optimal_boot,
)
from app.engine.combat_simulator import CombatSimulator
from app.engine.damage_calculator import get_target_profile_vectors
from app.engine.game_rules import infer_default_role, resolve_effective_rules
from app.engine.stat_aggregator import StatAggregator
from app.models.entities import (
    AutoPatchDiff,
    ChampionSnapshot,
    ItemSnapshot,
    PatchVersion,
    Rune,
)
from app.services.meta_shift_analyzer import _pct_diff, _snapshot_items_to_dicts

VERDICT_LABELS_EN: Dict[str, str] = {
    "MODE_SPECIFIC_TRAP": "Mode-Only Adjustment (No SR Impact)",
    "TRAP_BUFF_NET_NERF": "Trap Buff (Net Ecosystem Nerf)",
    "HIDDEN_NET_BUFF": "Hidden Net Buff (Despite Patch Nerf)",
    "PLACEBO_BUFF": "Placebo Buff (< +1% Combat Impact)",
    "PAPER_TIGER_NERF": "Paper-Tiger Nerf (< 1% Full-Combo Loss)",
    "CONFIRMED_POWER_SPIKE": "Confirmed Power Spike",
    "CONFIRMED_HEAVY_NERF": "Confirmed Heavy Nerf",
    "VERIFIED_BUFF": "Verified Net Buff",
    "VERIFIED_NERF": "Verified Net Nerf",
    "NEUTRAL_ADJUSTMENT": "Neutral Adjustment",
}


def _score_item_for_profile(
    item: Dict[str, Any],
    profile: Dict[str, Any],
    rules: Dict[str, Any],
) -> float:
    """Fast deterministic O(1) item heuristic used for zero-day roster-wide scans."""
    iid = str(item.get("item_id", ""))
    stats = item.get("stats") or {}
    ug = set(item.get("unique_groups") or [])

    ap = float(stats.get("ap", 0.0))
    ad = float(stats.get("ad", 0.0))
    hp = float(stats.get("hp", 0.0))
    armor = float(stats.get("armor", 0.0))
    mr = float(stats.get("mr", 0.0))
    mana = float(stats.get("mana", 0.0))
    ah = float(stats.get("ability_haste", 0.0))
    attack_speed = float(stats.get("attack_speed", 0.0))
    crit = float(stats.get("crit_chance", 0.0))
    lethality = float(stats.get("lethality", 0.0))
    armor_pen = float(stats.get("armor_pen_percent", 0.0))
    magic_pen_flat = float(stats.get("magic_pen_flat", 0.0))
    magic_pen_pct = float(stats.get("magic_pen_percent", 0.0))

    if iid == "3179" and rules.get("role") != "support":
        return -9999.0

    score = 0.0
    tags = set(profile.get("tags") or [])

    if profile.get("is_tank"):
        score = hp * 0.45 + armor * 3.2 + mr * 3.2 + ah * 1.8
    elif profile.get("is_aa_onhit_mage"):
        score = (
            attack_speed * 220.0
            + ap * 1.8
            + ah * 1.4
            + (180.0 if iid == "3115" else 0.0)
        )
    elif profile.get("is_ranged_control_mage") or (
        profile.get("is_ap_user") and not profile.get("is_ad_user")
    ):
        mana_bonus = 95.0 if (profile.get("uses_mana") and mana >= 400.0) else 0.0
        score = (
            ap * 2.1
            + magic_pen_flat * 5.5
            + magic_pen_pct * 260.0
            + ah * 1.5
            + mana_bonus
        )
    elif profile.get("is_spell_caster_adc"):
        spellblade_bonus = 220.0 if ("Spellblade" in ug or iid == "3078") else 0.0
        manamune_bonus = 200.0 if iid == "3004" else 0.0
        score = (
            ad * 2.2
            + ah * 2.6
            + armor_pen * 220.0
            + spellblade_bonus
            + manamune_bonus
        )
    elif profile.get("is_crit_marksman") or profile.get("is_marksman"):
        score = crit * 240.0 + ad * 2.1 + attack_speed * 150.0 + armor_pen * 230.0
    elif "Assassin" in tags and profile.get("is_ad_user"):
        if crit > 0.0 and lethality == 0.0:
            score = -500.0
        else:
            rush_bonus = 110.0 if iid in FIRST_ITEM_PRIORITY_IDS else 0.0
            score = (
                ad * 2.1
                + lethality * 4.8
                + ah * 1.6
                + armor_pen * 230.0
                + rush_bonus
            )
    else:
        fighter_bonus = (
            120.0
            if ("Spellblade" in ug or iid in ("3078", "3071", "3153"))
            else 0.0
        )
        score = (
            ad * 2.1
            + ap * 1.6
            + hp * 0.32
            + ah * 2.0
            + armor_pen * 180.0
            + fighter_bonus
        )

    if iid in LATE_CAPSTONE_IDS:
        score += 45.0

    # Gently reward ARAM sustain / mana reliability on Howling Abyss
    if rules.get("game_map") == "aram" and profile.get("uses_mana") and mana >= 400.0:
        score += 55.0

    return score


def select_archetype_core_build(
    profile: Dict[str, Any],
    candidate_items: List[Dict[str, Any]],
    target_profile_key: str,
    rules: Dict[str, Any],
) -> Tuple[List[Dict[str, Any]], str]:
    """Selects a realistic full core item build and primary keystone for a champion archetype."""
    filtered = filter_candidate_items(candidate_items, profile)
    scored = sorted(
        filtered,
        key=lambda item: (
            _score_item_for_profile(item, profile, rules),
            -int(item.get("gold_total", 3000)),
        ),
        reverse=True,
    )

    max_leg_slots = int(rules.get("legendary_slots", 5))
    max_mana_items = 2 if rules.get("game_map") == "aram" else 1
    chosen_legendaries: List[Dict[str, Any]] = []
    mana_count = 0
    total_crit = 0.0

    for cand in scored:
        if len(chosen_legendaries) >= max_leg_slots:
            break
        if _has_unique_conflict(chosen_legendaries, cand):
            continue
        stats = cand.get("stats") or {}
        cand_mana = float(stats.get("mana", 0.0))
        cand_crit = float(stats.get("crit_chance", 0.0))
        if cand_mana >= 400.0 and mana_count >= max_mana_items:
            continue
        if cand_crit > 0.0 and total_crit + cand_crit > 1.0 + 1e-6:
            continue
        chosen_legendaries.append(cand)
        if cand_mana >= 400.0:
            mana_count += 1
        total_crit += cand_crit

    # Relax secondary caps if pool is tiny (e.g., compact synthetic test fixtures)
    if len(chosen_legendaries) < min(max_leg_slots, len(scored)):
        for cand in scored:
            if len(chosen_legendaries) >= min(max_leg_slots, len(scored)):
                break
            if _has_unique_conflict(chosen_legendaries, cand):
                continue
            chosen_legendaries.append(cand)

    boot = select_optimal_boot(
        candidate_items, profile, "balanced" if profile.get("is_tank") else "burst", target_profile_key, rules
    )
    ordered = order_build_items(chosen_legendaries, boot, profile, rules)
    keystones = select_candidate_keystones(profile)
    keystone_key = keystones[0] if keystones else "Electrocute"
    return ordered, keystone_key


def _evaluate_ecosystem_shift(
    core_items: List[Dict[str, Any]],
    keystone_key: str,
    profile: Dict[str, Any],
    item_diffs_by_id: Dict[str, Dict[str, Any]],
    rune_diffs_by_key: Dict[str, Dict[str, Any]],
) -> Tuple[float, List[Dict[str, Any]]]:
    """
    Computes ecosystem impact from changed item passives (e.g., Voltaic Cyclosword passive nerf)
    and changed keystone runes affecting this champion's core setup.
    """
    catalysts: List[Dict[str, Any]] = []
    passive_shift_pct = 0.0

    for item in core_items:
        iid = str(item.get("item_id", ""))
        diff_row = item_diffs_by_id.get(iid)
        if not diff_row:
            continue
        payload = diff_row.get("diff_payload") or {}
        catalysts.append(
            {
                "entity_type": "item",
                "entity_key": iid,
                "entity_name": diff_row.get("entity_name") or item.get("name") or iid,
                "icon_url": item.get("icon_url"),
                "direction": diff_row.get("direction") or "ADJUSTMENT",
            }
        )

        pchanges = payload.get("passive_data_changes") or []
        item_rels: List[float] = []
        for change in pchanges:
            fname = str(change.get("field_name", "")).lower()
            if "melee" in fname and not profile.get("is_melee"):
                continue
            if "ranged" in fname and not profile.get("is_ranged"):
                continue
            old_v = change.get("old_value")
            new_v = change.get("new_value")
            if isinstance(old_v, (int, float)) and isinstance(new_v, (int, float)) and abs(float(old_v)) > 1e-6:
                rel = ((float(new_v) - float(old_v)) / abs(float(old_v))) * 100.0
                c_dir = str(change.get("direction", "")).upper()
                if c_dir == "NERF" and rel > 0:
                    rel = -rel
                elif c_dir == "BUFF" and rel < 0:
                    rel = -rel
                item_rels.append(rel)

        if item_rels:
            avg_rel = sum(item_rels) / len(item_rels)
            passive_shift_pct += max(-5.0, min(5.0, avg_rel * 0.12))

    rune_diff = rune_diffs_by_key.get(keystone_key)
    if rune_diff:
        catalysts.append(
            {
                "entity_type": "rune",
                "entity_key": keystone_key,
                "entity_name": rune_diff.get("entity_name") or keystone_key,
                "icon_url": None,
                "direction": rune_diff.get("direction") or "ADJUSTMENT",
            }
        )
        r_dir = str(rune_diff.get("direction", "")).upper()
        if r_dir == "BUFF":
            passive_shift_pct += 0.9
        elif r_dir == "NERF":
            passive_shift_pct -= 0.9

    return round(passive_shift_pct, 2), catalysts


def _evaluate_mechanic_and_cd_deltas(
    champion_diff_row: Optional[Dict[str, Any]],
    game_map: str,
) -> Tuple[float, float, bool]:
    """
    Evaluates non-curve mechanic deltas (shield/heal/summon/mode modifiers) and
    cooldown/mana adjustments from AutoPatchDiff.
    Returns: (mechanic_shift_pct, cd_mana_shift_pct, is_other_mode_only)
    """
    if not champion_diff_row:
        return 0.0, 0.0, False

    payload = champion_diff_row.get("diff_payload") or {}
    st_deltas = payload.get("stat_deltas") or []
    ab_deltas = payload.get("ability_deltas") or []
    mc_deltas = payload.get("mechanic_deltas") or []

    other_mode_count = 0
    active_mode_count = 0
    mech_shift = 0.0

    for mc in mc_deltas:
        fname = str(mc.get("field_name", "")).lower()
        is_arena_only = "cherry" in fname or "kiwi" in fname
        is_aram_only = "aram" in fname

        if is_arena_only:
            other_mode_count += 1
            continue
        if is_aram_only and game_map != "aram":
            other_mode_count += 1
            continue

        active_mode_count += 1
        old_vals = [float(x) for x in (mc.get("old_values") or []) if isinstance(x, (int, float))]
        new_vals = [float(x) for x in (mc.get("new_values") or []) if isinstance(x, (int, float))]
        if old_vals and new_vals:
            avg_old = sum(old_vals) / len(old_vals)
            avg_new = sum(new_vals) / len(new_vals)
            if abs(avg_old) > 1e-6:
                rel = ((avg_new - avg_old) / abs(avg_old)) * 100.0
                mdir = str(mc.get("direction", "")).upper()
                if mdir == "NERF" and rel > 0:
                    rel = -rel
                elif mdir == "BUFF" and rel < 0:
                    rel = -rel
                mech_shift += max(-6.0, min(6.0, rel * 0.18))

    cd_mana_shift = 0.0
    for ab in ab_deltas:
        old_cd = [float(x) for x in (ab.get("old_cooldown") or []) if isinstance(x, (int, float))]
        new_cd = [float(x) for x in (ab.get("new_cooldown") or []) if isinstance(x, (int, float))]
        if old_cd and new_cd:
            avg_o = sum(old_cd) / len(old_cd)
            avg_n = sum(new_cd) / len(new_cd)
            if avg_o > 1e-6:
                cd_rel = ((avg_o - avg_n) / avg_o) * 100.0
                cd_mana_shift += cd_rel * 0.025

        old_mana = [float(x) for x in (ab.get("old_mana_cost") or []) if isinstance(x, (int, float))]
        new_mana = [float(x) for x in (ab.get("new_mana_cost") or []) if isinstance(x, (int, float))]
        if old_mana and new_mana:
            avg_o = sum(old_mana) / len(old_mana)
            avg_n = sum(new_mana) / len(new_mana)
            if avg_o > 1e-6:
                mana_rel = ((avg_o - avg_n) / avg_o) * 100.0
                cd_mana_shift += mana_rel * 0.015

    cd_mana_shift = max(-2.0, min(2.0, cd_mana_shift))
    is_other_mode_only = (
        other_mode_count > 0 and active_mode_count == 0 and not st_deltas and not ab_deltas
    )
    return round(mech_shift, 2), round(cd_mana_shift, 2), is_other_mode_only


def _classify_mythbuster_verdict(
    official_direction: str,
    power_shift_score: float,
    is_other_mode_only: bool,
) -> Tuple[str, bool, str]:
    """Classifies whether an official champion patch note matches real combat math."""
    off = official_direction.upper()

    if is_other_mode_only and abs(power_shift_score) < 0.25:
        code = "MODE_SPECIFIC_TRAP"
        busted = True
        summary = (
            f"Official note is mode-specific (e.g., Arena); active map impact is {power_shift_score:+.2f}%."
        )
    elif off == "BUFF" and power_shift_score <= -0.25:
        code = "TRAP_BUFF_NET_NERF"
        busted = True
        summary = (
            f"Trap Buff: Champion was listed as buffed, but ecosystem item/rune changes drop net power by {power_shift_score:+.2f}%."
        )
    elif off == "NERF" and power_shift_score >= 0.25:
        code = "HIDDEN_NET_BUFF"
        busted = True
        summary = (
            f"Hidden Net Buff: Listed as nerfed, yet item/ecosystem gains result in {power_shift_score:+.2f}% net combat power."
        )
    elif off == "BUFF" and -0.25 < power_shift_score < 1.0:
        code = "PLACEBO_BUFF"
        busted = True
        summary = (
            f"Placebo Buff: Listed as buffed, but full-build combat impact is minimal ({power_shift_score:+.2f}%)."
        )
    elif off == "NERF" and -1.0 < power_shift_score < 0.25:
        code = "PAPER_TIGER_NERF"
        busted = True
        summary = (
            f"Paper-Tiger Nerf: Looks scary on paper, yet full-combo impact is only {power_shift_score:+.2f}%."
        )
    elif power_shift_score >= 2.5:
        code = "CONFIRMED_POWER_SPIKE"
        busted = False
        summary = f"Confirmed Power Spike: Real full-build simulation gain of {power_shift_score:+.2f}%."
    elif power_shift_score <= -2.5:
        code = "CONFIRMED_HEAVY_NERF"
        busted = False
        summary = f"Confirmed Heavy Nerf: Significant real full-build power drop of {power_shift_score:+.2f}%."
    elif off == "BUFF":
        code = "VERIFIED_BUFF"
        busted = False
        summary = f"Verified Buff: Measurable combat increase of {power_shift_score:+.2f}%."
    elif off == "NERF":
        code = "VERIFIED_NERF"
        busted = False
        summary = f"Verified Nerf: Measurable combat decrease of {power_shift_score:+.2f}%."
    else:
        code = "NEUTRAL_ADJUSTMENT"
        busted = False
        summary = f"Balanced adjustment with {power_shift_score:+.2f}% net combat shift."

    return code, busted, summary


class ZeroDayOracleService:
    """
    Scans the entire champion roster in under 500ms on Day 0 of a patch (before live match win-rate
    data exists) to uncover:
      1. Hidden Winners & Hidden Losers driven indirectly by item/rune shifts,
      2. Patch Mythbusters exposing placebo buffs, paper-tiger nerfs, trap buffs, and mode-only edits,
      3. Structured social share-card summaries ready for localization across all 25 LoL locales.
    """

    @staticmethod
    def _compute_blended_ehp(
        base_stats: Dict[str, float],
        items: List[Dict[str, Any]],
        n_levels: int,
        ehp_bonus_pct: float,
    ) -> float:
        vecs = StatAggregator.compute_level_vectors(base_stats, items, max_level=n_levels)
        shield_mult = 1.0 + ehp_bonus_pct / 100.0
        idx_mid = min(10, n_levels - 1)
        idx_late = n_levels - 1

        def _ehp_at(idx: int) -> float:
            hp = float(vecs["total_hp"][idx])
            phys = hp * (1.0 + float(vecs["armor"][idx]) / 100.0) * shield_mult
            mag = hp * (1.0 + float(vecs["mr"][idx]) / 100.0) * shield_mult
            return 0.5 * (phys + mag)

        return 0.45 * _ehp_at(idx_mid) + 0.55 * _ehp_at(idx_late)

    @classmethod
    def compute_radar_from_snapshots(
        cls,
        from_version: str,
        to_version: str,
        old_champions: Dict[str, Dict[str, Any]],
        new_champions: Dict[str, Dict[str, Any]],
        old_items: List[Dict[str, Any]],
        new_items: List[Dict[str, Any]],
        champ_diffs_by_key: Dict[str, Dict[str, Any]],
        item_diffs_by_id: Dict[str, Dict[str, Any]],
        rune_diffs_by_key: Dict[str, Dict[str, Any]],
        target_profile_key: str = "squishy",
        game_map: str = "sr",
        limit_per_bucket: int = 8,
    ) -> Dict[str, Any]:
        """Runs full-roster deterministic Zero-Day Oracle analysis from in-memory patch snapshots."""
        started = time.perf_counter()

        old_items_by_id = {str(i["item_id"]): i for i in old_items}
        new_items_by_id = {str(i["item_id"]): i for i in new_items}
        target_info = get_target_profile_vectors(target_profile_key, 18)

        all_entries: List[Dict[str, Any]] = []
        hidden_winners: List[Dict[str, Any]] = []
        hidden_losers: List[Dict[str, Any]] = []
        mythbusters: List[Dict[str, Any]] = []
        core_build_cache: Dict[Tuple[Any, ...], Tuple[List[Dict[str, Any]], str]] = {}

        for ckey in sorted(new_champions.keys()):
            new_c = new_champions[ckey]
            old_c = old_champions.get(ckey) or new_c

            tags = new_c.get("tags") or []
            partype = new_c.get("partype")
            old_base = old_c.get("base_stats") or {}
            new_base = new_c.get("base_stats") or {}
            old_ab = old_c.get("abilities") or {}
            new_ab = new_c.get("abilities") or {}

            champ_diff_row = champ_diffs_by_key.get(ckey)
            profile = infer_champion_profile(
                new_ab,
                tags=tags,
                partype=partype,
                base_stats=new_base,
                patch_signals=None,
            )
            role = infer_default_role(tags)
            rules = resolve_effective_rules(role=role, game_map=game_map)
            n_levels = int(rules["max_level"])

            archetype_cache_key = (
                tuple(sorted(tags)),
                bool(profile.get("uses_mana")),
                bool(profile.get("is_ap_user")),
                bool(profile.get("is_ad_user")),
                bool(profile.get("is_tank")),
                bool(profile.get("is_marksman")),
                bool(profile.get("is_aa_onhit_mage")),
                bool(profile.get("is_ranged_control_mage")),
                bool(profile.get("is_spell_caster_adc")),
                bool(profile.get("is_crit_marksman")),
                bool(profile.get("is_melee")),
                role,
                game_map,
                target_profile_key,
            )
            if archetype_cache_key in core_build_cache:
                new_core, keystone_key = core_build_cache[archetype_cache_key]
            else:
                new_core, keystone_key = select_archetype_core_build(
                    profile=profile,
                    candidate_items=new_items,
                    target_profile_key=target_profile_key,
                    rules=rules,
                )
                core_build_cache[archetype_cache_key] = (new_core, keystone_key)

            old_core_mapped = [
                {
                    **old_items_by_id.get(str(it["item_id"]), new_items_by_id.get(str(it["item_id"]), it)),
                    "is_boot": it.get("is_boot", False),
                }
                for it in new_core
            ]

            old_gold = sum(int(i.get("gold_total", 0)) for i in old_core_mapped)
            new_gold = sum(int(i.get("gold_total", 0)) for i in new_core)
            core_gold_delta = int(new_gold - old_gold)
            tempo_gold_shift_pct = round((-core_gold_delta / 3000.0) * 3.5, 2)

            eco_shift_pct, catalysts = _evaluate_ecosystem_shift(
                core_items=new_core,
                keystone_key=keystone_key,
                profile=profile,
                item_diffs_by_id=item_diffs_by_id,
                rune_diffs_by_key=rune_diffs_by_key,
            )
            mech_shift_pct, cd_mana_shift_pct, is_other_mode_only = _evaluate_mechanic_and_cd_deltas(
                champ_diff_row, game_map=game_map
            )

            # Fast path: when champion stats, Q/W/E/R curves, and combat item stats are identical,
            # combat simulation delta is identically 0.0%, saving >80% of full-roster CPU time.
            items_identical = all(
                {k: v for k, v in (old_it.get("stats") or {}).items() if not k.startswith("_")}
                == {k: v for k, v in (new_it.get("stats") or {}).items() if not k.startswith("_")}
                for old_it, new_it in zip(old_core_mapped, new_core)
            )
            slots_identical = all(
                old_ab.get(slot) == new_ab.get(slot) for slot in ("Q", "W", "E", "R")
            )
            if champ_diff_row is None and old_base == new_base and slots_identical and items_identical:
                burst_delta_pct = 0.0
                dps_delta_pct = 0.0
                ehp_delta_pct = 0.0
                combat_delta = 0.0
            else:
                old_sim = CombatSimulator.run_simulation(
                    champion_key=ckey,
                    base_stats=old_base,
                    base_abilities=old_ab,
                    patch_diff=None,
                    items=old_core_mapped,
                    target_profile_key=target_profile_key,
                    keystone_key=keystone_key,
                    role=role,
                    game_map=game_map,
                )
                new_sim = CombatSimulator.run_simulation(
                    champion_key=ckey,
                    base_stats=new_base,
                    base_abilities=new_ab,
                    patch_diff=None,
                    items=new_core,
                    target_profile_key=target_profile_key,
                    keystone_key=keystone_key,
                    role=role,
                    game_map=game_map,
                )

                old_curves = old_sim["level_curves"]
                new_curves = new_sim["level_curves"]
                idx_mid = min(10, len(new_curves) - 1)
                idx_late = len(new_curves) - 1

                old_burst = 0.45 * old_curves[idx_mid]["new_burst"] + 0.55 * old_curves[idx_late]["new_burst"]
                new_burst = 0.45 * new_curves[idx_mid]["new_burst"] + 0.55 * new_curves[idx_late]["new_burst"]
                burst_delta_pct = _pct_diff(new_burst, old_burst)

                old_dps = 0.45 * old_curves[idx_mid]["new_dps"] + 0.55 * old_curves[idx_late]["new_dps"]
                new_dps = 0.45 * new_curves[idx_mid]["new_dps"] + 0.55 * new_curves[idx_late]["new_dps"]
                dps_delta_pct = _pct_diff(new_dps, old_dps)

                old_ehp_bonus = float((old_sim.get("active_effects") or {}).get("ehp_bonus_pct", 0.0))
                new_ehp_bonus = float((new_sim.get("active_effects") or {}).get("ehp_bonus_pct", 0.0))
                old_ehp = cls._compute_blended_ehp(old_base, old_core_mapped, n_levels, old_ehp_bonus)
                new_ehp = cls._compute_blended_ehp(new_base, new_core, n_levels, new_ehp_bonus)
                ehp_delta_pct = _pct_diff(new_ehp, old_ehp)

                if profile.get("is_tank"):
                    combat_delta = 0.25 * burst_delta_pct + 0.25 * dps_delta_pct + 0.50 * ehp_delta_pct
                elif profile.get("is_marksman") or profile.get("is_aa_onhit_mage"):
                    combat_delta = 0.30 * burst_delta_pct + 0.60 * dps_delta_pct + 0.10 * ehp_delta_pct
                elif profile.get("is_ranged_control_mage") or "Assassin" in set(tags):
                    combat_delta = 0.65 * burst_delta_pct + 0.25 * dps_delta_pct + 0.10 * ehp_delta_pct
                else:
                    combat_delta = 0.45 * burst_delta_pct + 0.40 * dps_delta_pct + 0.15 * ehp_delta_pct

            power_shift_score = round(
                combat_delta + tempo_gold_shift_pct + eco_shift_pct + mech_shift_pct + cd_mana_shift_pct,
                2,
            )

            entry_base: Dict[str, Any] = {
                "champion_key": ckey,
                "champion_name": new_c.get("name") or ckey,
                "role": role,
                "role_label": rules["role_label"],
                "kit_archetype_label": profile["kit_archetype_label"],
                "keystone_key": keystone_key,
                "champion_changed_in_patch": champ_diff_row is not None,
                "official_direction": (champ_diff_row or {}).get("direction"),
                "power_shift_score": power_shift_score,
                "burst_delta_pct": burst_delta_pct,
                "dps_delta_pct": dps_delta_pct,
                "ehp_delta_pct": ehp_delta_pct,
                "core_gold_delta": core_gold_delta,
                "ecosystem_shift_pct": eco_shift_pct,
                "mechanic_shift_pct": mech_shift_pct,
                "catalysts": catalysts,
                "core_items": [
                    {
                        "item_id": str(i["item_id"]),
                        "name": i["name"],
                        "gold_total": int(i.get("gold_total", 0)),
                        "icon_url": i.get("icon_url"),
                        "is_boot": bool(i.get("is_boot")),
                    }
                    for i in new_core
                ],
            }
            all_entries.append(entry_base)

            if champ_diff_row is None:
                if power_shift_score >= 0.35:
                    hidden_winners.append(entry_base)
                elif power_shift_score <= -0.35:
                    hidden_losers.append(entry_base)
            else:
                verdict_code, is_busted, verdict_summary = _classify_mythbuster_verdict(
                    official_direction=str(champ_diff_row.get("direction") or "ADJUSTMENT"),
                    power_shift_score=power_shift_score,
                    is_other_mode_only=is_other_mode_only,
                )
                myth_entry = {
                    **entry_base,
                    "verdict_code": verdict_code,
                    "verdict_label": VERDICT_LABELS_EN[verdict_code],
                    "is_myth_busted": is_busted,
                    "verdict_summary": verdict_summary,
                }
                mythbusters.append(myth_entry)

        hidden_winners.sort(key=lambda x: x["power_shift_score"], reverse=True)
        hidden_losers.sort(key=lambda x: x["power_shift_score"])
        mythbusters.sort(
            key=lambda x: (1 if x["is_myth_busted"] else 0, abs(x["power_shift_score"])),
            reverse=True,
        )

        top_winners = sorted(
            [e for e in all_entries if e["power_shift_score"] > 0],
            key=lambda x: x["power_shift_score"],
            reverse=True,
        )[:limit_per_bucket]
        top_losers = sorted(
            [e for e in all_entries if e["power_shift_score"] < 0],
            key=lambda x: x["power_shift_score"],
        )[:limit_per_bucket]

        myths_busted_total = sum(1 for m in mythbusters if m["is_myth_busted"])
        hidden_movers = sorted(
            hidden_winners + hidden_losers,
            key=lambda x: abs(x["power_shift_score"]),
            reverse=True,
        )

        from_disp = to_display_version(from_version)
        to_disp = to_display_version(to_version)
        map_label = resolve_effective_rules(role="mid", game_map=game_map)["map_label"]
        elapsed_ms = round((time.perf_counter() - started) * 1000.0, 2)

        return {
            "from_version": from_version,
            "from_display_version": from_disp,
            "to_version": to_version,
            "to_display_version": to_disp,
            "game_map": game_map,
            "map_label": map_label,
            "target_profile": target_profile_key,
            "target_label": target_info["label"],
            "champions_scanned": len(all_entries),
            "scan_duration_ms": elapsed_ms,
            "summary_counts": {
                "hidden_winners": len(hidden_winners),
                "hidden_losers": len(hidden_losers),
                "mythbusters_total": len(mythbusters),
                "myths_busted": myths_busted_total,
                "items_changed": len(item_diffs_by_id),
                "runes_changed": len(rune_diffs_by_key),
            },
            "hidden_winners": hidden_winners[:limit_per_bucket],
            "hidden_losers": hidden_losers[:limit_per_bucket],
            "mythbusters": mythbusters[: max(limit_per_bucket, 12)],
            "top_winners": top_winners,
            "top_losers": top_losers,
            "share_card": {
                "headline": f"LoL {to_disp} — Zero-Day Meta Oracle & Patch Mythbuster",
                "subtitle": f"Deterministic scan of {len(all_entries)} champions ({from_disp} -> {to_disp}) before Day-1 match data",
                "patch_transition": f"{from_disp} → {to_disp}",
                "champions_scanned": len(all_entries),
                "hidden_winners_count": len(hidden_winners),
                "hidden_losers_count": len(hidden_losers),
                "myths_busted_count": myths_busted_total,
                "top_winner": top_winners[0] if top_winners else None,
                "top_hidden_mover": hidden_movers[0] if hidden_movers else None,
                "top_myth": mythbusters[0] if mythbusters else None,
            },
        }

    @classmethod
    def analyze_patch_radar(
        cls,
        db: Session,
        to_version: Optional[str] = None,
        target_profile_key: str = "squishy",
        game_map: str = "sr",
        limit_per_bucket: int = 8,
    ) -> Dict[str, Any]:
        """Loads synchronized patch snapshots and AutoPatchDiff entries to run full-roster Zero-Day radar."""
        pv = (
            db.query(PatchVersion).filter_by(version=to_version).first()
            if to_version
            else db.query(PatchVersion).filter_by(is_latest=True).first()
        )
        if not pv:
            raise ValueError("No synchronized patch version found in the database.")

        target_ver = pv.version
        prev_ver = pv.previous_version or pv.version

        new_champs_rows = db.query(ChampionSnapshot).filter_by(patch_version=target_ver).all()
        old_champs_rows = (
            db.query(ChampionSnapshot).filter_by(patch_version=prev_ver).all()
            if prev_ver != target_ver
            else new_champs_rows
        )

        new_champions = {
            c.champion_key: {
                "name": c.name,
                "tags": c.tags or [],
                "partype": c.partype,
                "base_stats": c.base_stats or {},
                "abilities": c.abilities or {},
            }
            for c in new_champs_rows
        }
        old_champions = {
            c.champion_key: {
                "name": c.name,
                "tags": c.tags or [],
                "partype": c.partype,
                "base_stats": c.base_stats or {},
                "abilities": c.abilities or {},
            }
            for c in old_champs_rows
        }

        new_item_rows = db.query(ItemSnapshot).filter_by(patch_version=target_ver, is_completed=True).all()
        old_item_rows = (
            db.query(ItemSnapshot).filter_by(patch_version=prev_ver, is_completed=True).all()
            if prev_ver != target_ver
            else new_item_rows
        )

        # Ensure boots are included even if a patch row had purchasable boots marked separately
        new_items = _snapshot_items_to_dicts(new_item_rows)
        old_items = _snapshot_items_to_dicts(old_item_rows)

        # Normalize Rune table access just to ensure patch sync integrity if needed later
        _ = db.query(Rune.rune_id).filter_by(patch_version=target_ver).limit(1).all()

        diff_rows = (
            db.query(AutoPatchDiff)
            .filter_by(from_version=prev_ver, to_version=target_ver)
            .all()
            if prev_ver != target_ver
            else []
        )
        champ_diffs_by_key: Dict[str, Dict[str, Any]] = {}
        item_diffs_by_id: Dict[str, Dict[str, Any]] = {}
        rune_diffs_by_key: Dict[str, Dict[str, Any]] = {}

        for row in diff_rows:
            entry = {
                "entity_key": row.entity_key,
                "entity_name": row.entity_name,
                "direction": row.direction,
                "diff_payload": row.diff_payload or {},
            }
            if row.entity_type == "champion":
                champ_diffs_by_key[row.entity_key] = entry
            elif row.entity_type == "item":
                item_diffs_by_id[row.entity_key] = entry
            elif row.entity_type == "rune":
                rune_diffs_by_key[row.entity_key] = entry

        return cls.compute_radar_from_snapshots(
            from_version=prev_ver,
            to_version=target_ver,
            old_champions=old_champions,
            new_champions=new_champions,
            old_items=old_items,
            new_items=new_items,
            champ_diffs_by_key=champ_diffs_by_key,
            item_diffs_by_id=item_diffs_by_id,
            rune_diffs_by_key=rune_diffs_by_key,
            target_profile_key=target_profile_key,
            game_map=game_map,
            limit_per_bucket=limit_per_bucket,
        )
