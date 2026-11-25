from typing import Any, Dict, List, Literal, Optional, Tuple

from app.engine.combat_simulator import CombatSimulator
from app.engine.stat_aggregator import StatAggregator

GameStateKey = Literal["even", "ahead", "behind"]

SNOWBALL_STACK_IDS = {"3041", "6697", "3084"}  # Mejai's Soulstealer, Hubris, Heartsteel
SNOWBALL_SPIKE_IDS = {"3089", "4645", "4646", "3031", "6676", "3072", "3142", "3078"}
COMEBACK_ANCHOR_IDS = {
    "3157",  # Zhonya's Hourglass
    "3102",  # Banshee's Veil
    "3137",  # Cryptbloom
    "3135",  # Void Staff
    "3116",  # Rylai's Crystal Scepter
    "6653",  # Liandry's Torment
    "3071",  # Black Cleaver
    "3053",  # Sterak's Gage
    "6333",  # Death's Dance
    "3156",  # Maw of Malmortius
    "3026",  # Guardian Angel
    "6695",  # Serpent's Fang
    "3033",  # Mortal Reminder
    "6694",  # Serylda's Grudge
    "3110",  # Frozen Heart
    "3143",  # Randuin's Omen
    "3109",  # Knight's Vow
    "2502",  # Unending Despair
}

STATE_LABELS_EN: Dict[str, str] = {
    "behind": "Behind (Comeback / Tempo)",
    "even": "Even (Balanced Standard)",
    "ahead": "Ahead (Snowball / Carry)",
}

STATE_TACTICAL_RULES_EN: Dict[str, str] = {
    "behind": "Skip risky stacking or 3500g+ luxury walls; spike earlier with affordable %Penetration, Ability Haste, and survival anchors.",
    "even": "Follow standard power-curve efficiency mixing core spikes, penetration, and balanced defense.",
    "ahead": "Accelerate your lead with multiplier capstones, flat penetration, and high-ceiling snowball items to close the game before enemy scaling.",
}

TRAP_DETAILS_EN: Dict[str, Tuple[str, str]] = {
    "STACKING_SNOWBALL_TRAP": (
        "Win-More Stacking Trap",
        "Stats inflate win-rate because players mostly buy stacking items when already winning; dying while behind leaves wasted gold.",
    ),
    "LUXURY_GOLD_WALL_TRAP": (
        "Luxury Gold-Wall Trap",
        "High-cost zero-defense capstone delays your 2nd/3rd item power spike by several minutes when income is starved.",
    ),
    "FLAT_PEN_EXECUTION_TRAP": (
        "Flat-Pen / Execution Bias Trap",
        "Flat penetration drops sharply in value once enemies hit armor/MR spikes or if you cannot survive long enough to combo.",
    ),
}


def classify_item_winrate_trap(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Detects whether a completed legendary item exhibits win-rate survivorship/snowball bias
    or creates a risky gold-wall when playing from behind.
    """
    iid = str(item.get("item_id", ""))
    gold = int(item.get("gold_total", 0))
    stats = item.get("stats") or {}

    hp = float(stats.get("hp", 0.0))
    armor = float(stats.get("armor", 0.0))
    mr = float(stats.get("mr", 0.0))
    lethality = float(stats.get("lethality", 0.0))
    magic_pen_flat = float(stats.get("magic_pen_flat", 0.0))
    armor_pen_pct = float(stats.get("armor_pen_percent", 0.0))
    magic_pen_pct = float(stats.get("magic_pen_percent", 0.0))

    has_defense = hp > 0.0 or armor > 0.0 or mr > 0.0
    trap_code: Optional[str] = None
    risk_level = "MODERATE"

    if iid in SNOWBALL_STACK_IDS:
        trap_code = "STACKING_SNOWBALL_TRAP"
        risk_level = "HIGH"
    elif gold >= 3400 and not has_defense:
        trap_code = "LUXURY_GOLD_WALL_TRAP"
        risk_level = "HIGH" if gold >= 3500 else "MODERATE"
    elif (
        (iid in ("4646", "6676") or lethality >= 18.0 or magic_pen_flat >= 15.0)
        and not has_defense
        and armor_pen_pct == 0.0
        and magic_pen_pct == 0.0
    ):
        trap_code = "FLAT_PEN_EXECUTION_TRAP"
        risk_level = "MODERATE"

    if not trap_code:
        return None

    title, reason = TRAP_DETAILS_EN[trap_code]
    return {
        "trap_code": trap_code,
        "risk_level": risk_level,
        "trap_title": title,
        "trap_reason": reason,
    }


def is_comeback_anchor_item(item: Dict[str, Any]) -> bool:
    """Returns True when an item offers affordable carry/fighter comeback tempo, defense, or %Penetration."""
    iid = str(item.get("item_id", ""))
    if iid in COMEBACK_ANCHOR_IDS:
        return True

    gold = int(item.get("gold_total", 0))
    stats = item.get("stats") or {}
    if gold < 2450 or gold > 3100:
        return False

    return bool(
        float(stats.get("hp", 0.0)) >= 250.0
        or float(stats.get("armor", 0.0)) >= 35.0
        or float(stats.get("mr", 0.0)) >= 35.0
        or float(stats.get("armor_pen_percent", 0.0)) >= 0.30
        or float(stats.get("magic_pen_percent", 0.0)) >= 0.30
        or float(stats.get("ability_haste", 0.0)) >= 20.0
    )


def compute_game_state_score_adjustment(
    real_items: List[Dict[str, Any]],
    profile: Dict[str, Any],
    avg_ehp_11: float,
    burst_val: float,
    ah: float,
    game_state: str = "even",
    rules: Optional[Dict[str, Any]] = None,
) -> float:
    """
    Applies Behind (Comeback) vs. Ahead (Snowball) Beam Search score adjustments.
    Returns 0.0 for 'even' to keep baseline build optimization completely unchanged.
    """
    state = (game_state or "even").lower()
    if state == "even":
        return 0.0

    is_support_ctx = (rules or {}).get("role") == "support" or (
        "Support" in set(profile.get("tags") or []) and "Mage" not in set(profile.get("tags") or [])
    )
    adj = 0.0
    if state == "behind":
        comeback_count = 0

        for item in real_items:
            iid = str(item.get("item_id", ""))
            gold = int(item.get("gold_total", 3000))
            stats = item.get("stats") or {}
            trap = classify_item_winrate_trap(item)

            if trap:
                if trap["trap_code"] == "STACKING_SNOWBALL_TRAP":
                    adj -= 900.0
                elif trap["trap_code"] == "LUXURY_GOLD_WALL_TRAP":
                    adj -= 850.0
                elif trap["trap_code"] == "FLAT_PEN_EXECUTION_TRAP":
                    adj -= 420.0

            if gold < 2450 and not is_support_ctx:
                adj -= 550.0
            elif is_comeback_anchor_item(item) and comeback_count < 4:
                adj += 380.0
                comeback_count += 1

            if 2450 <= gold <= 3100:
                adj += (3200.0 - float(gold)) * 0.45

            if float(stats.get("armor_pen_percent", 0.0)) > 0 or float(stats.get("magic_pen_percent", 0.0)) > 0:
                adj += 180.0

            if iid in SNOWBALL_STACK_IDS:
                adj -= 150.0

        adj += avg_ehp_11 * 0.35 + ah * 4.5
        return round(adj, 2)

    if state == "ahead":
        snowball_count = 0
        pure_tank_detours = 0
        defensive_detours = 0
        for item in real_items:
            iid = str(item.get("item_id", ""))
            stats = item.get("stats") or {}
            if iid in SNOWBALL_STACK_IDS:
                adj += 450.0
            elif iid in SNOWBALL_SPIKE_IDS and snowball_count < 4:
                adj += 280.0
                snowball_count += 1
            if float(stats.get("ap_multiplier", 0.0)) > 0 or iid == "3031":
                adj += 420.0
            if float(stats.get("lethality", 0.0)) > 0 or float(stats.get("magic_pen_flat", 0.0)) > 0:
                adj += 220.0
            if not profile.get("is_tank"):
                if float(stats.get("ap", 0.0)) == 0.0 and float(stats.get("ad", 0.0)) == 0.0:
                    pure_tank_detours += 1
                elif (
                    float(stats.get("armor", 0.0)) >= 35.0
                    or float(stats.get("mr", 0.0)) >= 35.0
                    or float(stats.get("hp", 0.0)) >= 350.0
                ):
                    defensive_detours += 1

        adj += burst_val * 0.25 - pure_tank_detours * 220.0 - defensive_detours * 220.0
        return round(adj, 2)

    return 0.0


def select_game_state_boot_override(
    all_items: List[Dict[str, Any]],
    profile: Dict[str, Any],
    base_boot: Optional[Dict[str, Any]],
    game_state: str,
    rules: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """Switches Tier-2 boots toward defensive/tempo options when playing from behind."""
    if (game_state or "even").lower() != "behind" or rules.get("tier3_boots"):
        return base_boot

    boots_map: Dict[str, Dict[str, Any]] = {}
    for item in all_items:
        tags = set(item.get("tags") or [])
        ug = set(item.get("unique_groups") or [])
        if ("Boots" in tags or "Boots" in ug) and int(item.get("gold_total", 0)) >= 900:
            boots_map[str(item["item_id"])] = item

    if not boots_map:
        return base_boot

    preferred = ["3158", "3111", "3047"] if profile.get("is_ap_user") and not profile.get("is_ad_user") else ["3047", "3111", "3158"]
    chosen = next((boots_map[pid] for pid in preferred if pid in boots_map), None)
    if not chosen:
        return base_boot

    slot_type = "role_quest_boot" if rules.get("separate_boot_slot") else "standard_boot"
    return {
        "item_id": str(chosen["item_id"]),
        "name": chosen["name"],
        "gold_total": int(chosen.get("gold_total", 0)),
        "stats": {k: v for k, v in (chosen.get("stats") or {}).items() if not k.startswith("_")},
        "unique_groups": chosen.get("unique_groups") or ["Boots"],
        "icon_url": chosen.get("icon_url"),
        "is_boot": True,
        "slot_type": slot_type,
    }


def _quick_item_score(
    item: Dict[str, Any],
    profile: Dict[str, Any],
    target_state: str,
    rules: Dict[str, Any],
) -> float:
    iid = str(item.get("item_id", ""))
    gold = int(item.get("gold_total", 3000))
    stats = item.get("stats") or {}

    ap = float(stats.get("ap", 0.0))
    ap_mult = float(stats.get("ap_multiplier", 0.0))
    ad = float(stats.get("ad", 0.0))
    hp = float(stats.get("hp", 0.0))
    armor = float(stats.get("armor", 0.0))
    mr = float(stats.get("mr", 0.0))
    mana = float(stats.get("mana", 0.0))
    ah = float(stats.get("ability_haste", 0.0))
    as_val = float(stats.get("attack_speed", 0.0))
    crit = float(stats.get("crit_chance", 0.0))
    leth = float(stats.get("lethality", 0.0))
    mpen_f = float(stats.get("magic_pen_flat", 0.0))
    mpen_p = float(stats.get("magic_pen_percent", 0.0))
    apen_p = float(stats.get("armor_pen_percent", 0.0))

    mana_bonus = 90.0 if (profile.get("uses_mana") and mana >= 400.0) else 0.0
    if profile.get("is_tank"):
        base = hp * 0.45 + armor * 3.1 + mr * 3.1 + ah * 1.8
    elif profile.get("is_ap_user") and not profile.get("is_ad_user"):
        base = ap * 2.1 + ap_mult * 1400.0 + mpen_f * 6.5 + mpen_p * 280.0 + ah * 1.6 + mana_bonus
        if target_state == "even" and (armor >= 35.0 or mr >= 35.0 or hp >= 300.0):
            base += 45.0
    elif profile.get("is_marksman"):
        base = ad * 2.1 + crit * 220.0 + as_val * 160.0 + apen_p * 240.0 + leth * 2.0 + mana_bonus
    else:
        base = ad * 2.1 + leth * 4.5 + ah * 1.9 + apen_p * 240.0 + mana_bonus
        if target_state == "even" and (armor >= 35.0 or mr >= 35.0 or hp >= 300.0):
            base += 45.0

    if rules.get("game_map") == "aram" and profile.get("uses_mana") and mana >= 400.0:
        base += 55.0

    # Include single-item state delta heuristic
    avg_ehp_proxy = hp * 2.2 + (armor + mr) * 35.0
    burst_proxy = ap * 2.2 + ap_mult * 1500.0 + ad * 2.5 + leth * 10.0 + mpen_f * 10.0
    state_adj = compute_game_state_score_adjustment(
        [item], profile, avg_ehp_11=avg_ehp_proxy, burst_val=burst_proxy, ah=ah, game_state=target_state, rules=rules
    )
    if target_state == "behind" and 2450 <= gold <= 3100:
        state_adj += (3200 - gold) * 0.25
    if iid in SNOWBALL_STACK_IDS and target_state == "ahead":
        state_adj += 220.0
    return base + state_adj


class GameStatePivotEngine:
    """
    Audits completed items for win-rate / survivorship bias traps and builds a
    3-way Ahead / Even / Behind dynamic pivot tree for any champion & map context.
    """

    @classmethod
    def _find_comeback_alternative(
        cls,
        trap_item: Dict[str, Any],
        filtered_items: List[Dict[str, Any]],
        profile: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        trap_id = str(trap_item.get("item_id", ""))
        trap_gold = int(trap_item.get("gold_total", 3000))
        trap_stats = trap_item.get("stats") or {}

        candidates: List[Tuple[float, Dict[str, Any]]] = []
        tags = set(profile.get("tags") or [])
        for cand in filtered_items:
            cid = str(cand.get("item_id", ""))
            if cid == trap_id or classify_item_winrate_trap(cand) is not None:
                continue
            cstats = cand.get("stats") or {}
            cgold = int(cand.get("gold_total", 3000))
            if not is_comeback_anchor_item(cand) and cgold > 3100:
                continue
            # Exclude cheap Enchanter/Support items (<2450g) for non-support carries
            if cgold < 2450 and "Support" not in tags:
                continue

            sim_score = 180.0 if cid in COMEBACK_ANCHOR_IDS else 0.0
            if profile.get("is_ap_user") and float(cstats.get("ap", 0.0)) > 0:
                sim_score += float(cstats.get("ap", 0.0)) * 1.2 + float(cstats.get("magic_pen_percent", 0.0)) * 220.0
            if profile.get("is_ad_user") and float(cstats.get("ad", 0.0)) > 0:
                sim_score += float(cstats.get("ad", 0.0)) * 1.6 + float(cstats.get("armor_pen_percent", 0.0)) * 220.0
            if float(cstats.get("hp", 0.0)) > 0 or float(cstats.get("armor", 0.0)) > 0 or float(cstats.get("mr", 0.0)) > 0:
                sim_score += 90.0
            if float(trap_stats.get("mana", 0.0)) >= 400 and float(cstats.get("mana", 0.0)) >= 400:
                sim_score += 60.0
            sim_score += max(-150.0, float(trap_gold - cgold) * 0.20)
            candidates.append((sim_score, cand))

        if not candidates:
            return None
        candidates.sort(key=lambda pair: pair[0], reverse=True)
        best = candidates[0][1]
        return {
            "item_id": str(best["item_id"]),
            "name": best["name"],
            "gold_total": int(best.get("gold_total", 0)),
            "icon_url": best.get("icon_url"),
            "gold_saved": int(trap_gold - int(best.get("gold_total", 0))),
        }

    @classmethod
    def audit_traps_and_build_pivot_tree(
        cls,
        champion_key: str,
        base_stats: Dict[str, float],
        base_abilities: Dict[str, Any],
        all_items: List[Dict[str, Any]],
        filtered_items: List[Dict[str, Any]],
        profile: Dict[str, Any],
        rules: Dict[str, Any],
        target_profile_key: str,
        primary_variation: Optional[Dict[str, Any]],
        active_game_state: str = "even",
    ) -> Dict[str, Any]:
        """Generates Win-Rate Trap warnings and Ahead / Even / Behind 6/7-item build pivots."""
        from app.engine.build_optimizer import (
            _has_unique_conflict,
            order_build_items,
            select_optimal_boot,
        )

        # 1. Identify Win-Rate Traps prioritizing traps seen in recommended items
        seen_trap_ids: set[str] = set()
        trap_warnings: List[Dict[str, Any]] = []

        ordered_scan = list((primary_variation or {}).get("items") or []) + list(filtered_items)
        for item in ordered_scan:
            iid = str(item.get("item_id", ""))
            if not iid or iid in seen_trap_ids or item.get("is_boot"):
                continue
            trap = classify_item_winrate_trap(item)
            if not trap:
                continue
            seen_trap_ids.add(iid)
            alt = cls._find_comeback_alternative(item, filtered_items, profile)
            trap_warnings.append(
                {
                    "item_id": iid,
                    "item_name": item.get("name", iid),
                    "gold_total": int(item.get("gold_total", 0)),
                    "icon_url": item.get("icon_url"),
                    **trap,
                    "comeback_alternative": alt,
                }
            )
            if len(trap_warnings) >= 4:
                break

        risk_rank = {"HIGH": 2, "MODERATE": 1}
        trap_warnings.sort(key=lambda w: (risk_rank.get(w["risk_level"], 0), w["gold_total"]), reverse=True)

        # 2. Build 3-state Pivot Tree ("behind", "even", "ahead")
        max_leg = int(rules.get("legendary_slots", 5))
        eff_slots = min(max_leg, len(filtered_items))
        resolved_role = str(rules.get("role", "mid"))
        game_map = str(rules.get("game_map", "sr"))
        base_keystone = (
            ((primary_variation or {}).get("keystone") or {}).get("key")
            or "Electrocute"
        )
        base_boot = (primary_variation or {}).get("boot") or select_optimal_boot(
            all_items, profile, "burst", target_profile_key, rules
        )

        pivots: Dict[str, Dict[str, Any]] = {}
        for state in ("behind", "even", "ahead"):
            if primary_variation and state == active_game_state:
                var_items = primary_variation["items"]
                var_metrics = primary_variation["metrics"]
                total_gold = int(primary_variation["total_gold"])
                ks_key = base_keystone
            else:
                scored_legs = sorted(
                    filtered_items,
                    key=lambda it: _quick_item_score(it, profile, state, rules),
                    reverse=True,
                )
                chosen_legs: List[Dict[str, Any]] = []
                mana_count = 0
                max_mana = 2 if game_map == "aram" else 1
                total_crit = 0.0

                for cand in scored_legs:
                    if len(chosen_legs) >= eff_slots:
                        break
                    if _has_unique_conflict(chosen_legs, cand):
                        continue
                    cstats = cand.get("stats") or {}
                    c_mana = float(cstats.get("mana", 0.0))
                    c_crit = float(cstats.get("crit_chance", 0.0))
                    if c_mana >= 400.0 and mana_count >= max_mana:
                        continue
                    if c_crit > 0.0 and total_crit + c_crit > 1.0 + 1e-6:
                        continue
                    chosen_legs.append(cand)
                    if c_mana >= 400.0:
                        mana_count += 1
                    total_crit += c_crit

                if len(chosen_legs) < eff_slots:
                    for cand in scored_legs:
                        if len(chosen_legs) >= eff_slots:
                            break
                        if _has_unique_conflict(chosen_legs, cand):
                            continue
                        chosen_legs.append(cand)

                state_boot = select_game_state_boot_override(all_items, profile, base_boot, state, rules)
                var_items = order_build_items(chosen_legs, state_boot, profile, rules, game_state=state)
                sim = CombatSimulator.run_simulation(
                    champion_key=champion_key,
                    base_stats=base_stats,
                    base_abilities=base_abilities,
                    patch_diff=None,
                    items=var_items,
                    target_profile_key=target_profile_key,
                    keystone_key=base_keystone,
                    role=resolved_role,
                    game_map=game_map,
                )
                curves = sim["level_curves"]
                stat_vecs = StatAggregator.compute_level_vectors(
                    base_stats, var_items, max_level=int(rules.get("max_level", 18))
                )
                ehp_bonus = 1.0 + float((sim.get("active_effects") or {}).get("ehp_bonus_pct", 0.0)) / 100.0
                phys_ehp_11 = float(stat_vecs["total_hp"][10] * (1.0 + stat_vecs["armor"][10] / 100.0) * ehp_bonus)
                magic_ehp_11 = float(stat_vecs["total_hp"][10] * (1.0 + stat_vecs["mr"][10] / 100.0) * ehp_bonus)
                var_metrics = {
                    "lvl11_burst": curves[10]["new_burst"],
                    "lvl18_burst": curves[17]["new_burst"],
                    "lvl11_dps": curves[10]["new_dps"],
                    "lvl18_dps": curves[17]["new_dps"],
                    "phys_ehp_lvl11": round(phys_ehp_11, 1),
                    "magic_ehp_lvl11": round(magic_ehp_11, 1),
                }
                total_gold = sum(int(i.get("gold_total", 0)) for i in var_items)
                ks_key = base_keystone

            avg_ehp = round(
                0.5 * (float(var_metrics.get("phys_ehp_lvl11", 0.0)) + float(var_metrics.get("magic_ehp_lvl11", 0.0))),
                1,
            )
            pivots[state] = {
                "game_state": state,
                "state_label": STATE_LABELS_EN[state],
                "tactical_rule": STATE_TACTICAL_RULES_EN[state],
                "items": var_items,
                "keystone_key": ks_key,
                "total_gold": total_gold,
                "gold_diff_vs_even": 0,
                "lvl11_burst": round(float(var_metrics.get("lvl11_burst", 0.0)), 1),
                "lvl18_burst": round(float(var_metrics.get("lvl18_burst", 0.0)), 1),
                "lvl11_dps": round(float(var_metrics.get("lvl11_dps", 0.0)), 1),
                "lvl18_dps": round(float(var_metrics.get("lvl18_dps", 0.0)), 1),
                "avg_ehp_lvl11": avg_ehp,
                "swapped_in_items": [],
            }

        even_pivot = pivots.get("even")
        even_gold = int(even_pivot["total_gold"]) if even_pivot else 0
        even_item_ids = {str(i["item_id"]) for i in (even_pivot or {}).get("items", [])}

        for state, node in pivots.items():
            node["gold_diff_vs_even"] = int(node["total_gold"] - even_gold)
            if state != "even":
                node["swapped_in_items"] = [
                    {
                        "item_id": str(it["item_id"]),
                        "name": it["name"],
                        "gold_total": int(it.get("gold_total", 0)),
                        "icon_url": it.get("icon_url"),
                    }
                    for it in node["items"]
                    if str(it["item_id"]) not in even_item_ids
                ]

        return {
            "active_game_state": active_game_state,
            "active_state_label": STATE_LABELS_EN.get(active_game_state, STATE_LABELS_EN["even"]),
            "strategy_summary": STATE_TACTICAL_RULES_EN.get(active_game_state, STATE_TACTICAL_RULES_EN["even"]),
            "winrate_trap_warnings": trap_warnings,
            "pivots": pivots,
        }
