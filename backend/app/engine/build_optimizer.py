from typing import Any, Dict, List, Optional, Set, Tuple

from app.engine.combat_simulator import CombatSimulator
from app.engine.full_rune_page_engine import FullRunePageEngine
from app.engine.game_rules import infer_default_role, resolve_effective_rules
from app.engine.passive_and_rune_engine import SUPPORTED_KEYSTONES
from app.engine.stat_aggregator import StatAggregator
from app.schemas.patch_contracts import ChampionPatchDiff

PLAYSTYLE_LABELS: Dict[str, str] = {
    "burst": "Burst / One-Shot",
    "dps": "Sustained DPS",
    "balanced": "Balanced & Survivability (Durability + Tempo)",
}

# Lane/tempo rush items prioritized for Slot 1
FIRST_ITEM_PRIORITY_IDS = {
    "6655",  # Luden's Companion
    "2503",  # Blackfire Torch
    "6657",  # Rod of Ages
    "3003",  # Archangel's Staff
    "6653",  # Liandry's Torment
    "3078",  # Trinity Force
    "3153",  # Blade of the Ruined King
    "6672",  # Kraken Slayer
    "3142",  # Youmuu's Ghostblade
    "6697",  # Hubris
    "6699",  # Voltaic Cyclosword
    "3068",  # Sunfire Aegis
    "3084",  # Heartsteel
    "6664",  # Hollow Radiance
    "3071",  # Black Cleaver
}

# Late-game multiplier, percentage penetration, and defensive capstone items (Slots 3-6)
LATE_CAPSTONE_IDS = {
    "3089",  # Rabadon's Deathcap
    "3135",  # Void Staff
    "3137",  # Cryptbloom
    "3036",  # Lord Dominik's Regards
    "3033",  # Mortal Reminder
    "6694",  # Serylda's Grudge
    "3026",  # Guardian Angel
    "3157",  # Zhonya's Hourglass
    "3102",  # Banshee's Veil
    "6665",  # Jak'Sho, The Protean
}


def analyze_patch_diff_signals(
    champion_patch_diff: Optional[Any],
) -> Dict[str, Any]:
    """
    Inspects recent champion deltas (StatDelta, AbilityDelta, MechanicDelta) to derive
    patch-agnostic and champion-name-independent adaptation signals.
    """
    signals: Dict[str, Any] = {
        "ap_scaling_buffed": False,
        "ad_scaling_buffed": False,
        "onhit_buffed": False,
        "cd_or_mana_nerfed": False,
        "defensive_buffed": False,
        "range_buffed": False,
        "adaptation_notes": [],
    }
    if not champion_patch_diff:
        return signals

    diff_dict = (
        champion_patch_diff.model_dump()
        if hasattr(champion_patch_diff, "model_dump")
        else (champion_patch_diff if isinstance(champion_patch_diff, dict) else {})
    )

    for st in diff_dict.get("stat_deltas") or []:
        sname = str(st.get("stat_name", "")).lower()
        direction = str(st.get("direction", "")).upper()
        if sname == "attack_range" and direction == "BUFF":
            signals["range_buffed"] = True
        if sname in ("base_hp", "hp_growth", "base_armor", "armor_growth", "base_mr", "mr_growth") and direction == "BUFF":
            signals["defensive_buffed"] = True

    for ab in diff_dict.get("ability_deltas") or []:
        old_cd = ab.get("old_cooldown") or []
        new_cd = ab.get("new_cooldown") or []
        if old_cd and new_cd and (sum(new_cd) / len(new_cd)) > (sum(old_cd) / len(old_cd)) + 1e-3:
            signals["cd_or_mana_nerfed"] = True

        old_mana = ab.get("old_mana_cost") or []
        new_mana = ab.get("new_mana_cost") or []
        if old_mana and new_mana and (sum(new_mana) / len(new_mana)) > (sum(old_mana) / len(old_mana)) + 1e-3:
            signals["cd_or_mana_nerfed"] = True

        for sc in ab.get("scaling_changes") or []:
            sc_stat = str(sc.get("scaling_stat", "")).lower()
            old_r = float(sc.get("old_ratio", 0.0))
            new_r = float(sc.get("new_ratio", 0.0))
            if new_r > old_r + 1e-4:
                if sc_stat == "ap":
                    signals["ap_scaling_buffed"] = True
                elif sc_stat in ("ad", "total_ad", "bonus_ad"):
                    signals["ad_scaling_buffed"] = True

    for mc in diff_dict.get("mechanic_deltas") or []:
        fname = str(mc.get("field_name", "")).lower()
        direction = str(mc.get("direction", "")).upper()
        if direction == "BUFF":
            if "onhit" in fname:
                signals["onhit_buffed"] = True
            if any(tok in fname for tok in ("shield", "heal", "hp", "armor", "mr")):
                signals["defensive_buffed"] = True
            if "ap" in fname and "ratio" in fname:
                signals["ap_scaling_buffed"] = True
            if "ad" in fname and "ratio" in fname:
                signals["ad_scaling_buffed"] = True

    notes: List[str] = []
    if signals["cd_or_mana_nerfed"]:
        notes.append("Ability Haste and Mana items were prioritized to offset increased cooldown / mana costs.")
    if signals["onhit_buffed"]:
        notes.append("Attack speed and On-Hit items were prioritized following the On-Hit buff.")
    if signals["range_buffed"]:
        notes.append("Sustained DPS items were rewarded to leverage the increased attack range.")
    if signals["ap_scaling_buffed"]:
        notes.append("High-AP and Magic Penetration synergies were boosted following the AP ratio buff.")
    if signals["ad_scaling_buffed"]:
        notes.append("High-AD and Ability Haste synergies were boosted following the AD ratio buff.")
    if signals["defensive_buffed"]:
        notes.append("Survivability items received higher weight in balanced builds following the shield/durability buff.")
    signals["adaptation_notes"] = notes
    return signals


def infer_champion_profile(
    abilities: Dict[str, Any],
    tags: Optional[List[str]] = None,
    partype: Optional[str] = None,
    base_stats: Optional[Dict[str, Any]] = None,
    patch_signals: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Infers a complete gameplay kit profile from ability scalings, attack range,
    cooldown cadence, mana burn, raw mechanic keys, and recent patch signals.
    """
    tags_set = set(tags or [])
    base_stats = base_stats or {}
    patch_signals = patch_signals or {}

    sum_ap = 0.0
    sum_ad = 0.0
    sum_tank = 0.0
    basic_max_cds: List[float] = []
    basic_max_manas: List[float] = []

    for slot in ("Q", "W", "E", "R"):
        ab = (abilities or {}).get(slot) or {}
        scaling = ab.get("scaling") or {}
        sum_ap += float(scaling.get("ap", 0.0))
        sum_ad += float(scaling.get("total_ad", 0.0)) + float(scaling.get("bonus_ad", 0.0))
        sum_tank += (
            float(scaling.get("armor", 0.0))
            + float(scaling.get("mr", 0.0))
            + float(scaling.get("bonus_hp", 0.0))
        )
        if slot in ("Q", "W", "E"):
            cds = [float(x) for x in (ab.get("cooldown") or []) if float(x) > 0]
            # Exclude sub-2s toggle/charge abilities (e.g., Jinx Q, Azir W) from base cooldown average
            if cds and cds[-1] >= 2.0:
                basic_max_cds.append(cds[-1])
            manas = [float(x) for x in (ab.get("mana_cost") or []) if float(x) > 0]
            if manas:
                basic_max_manas.append(manas[-1])

    # Detect on-hit and shield/heal kit mechanics from CDragon _raw_spells
    raw_spells = (abilities or {}).get("_raw_spells") or {}
    has_onhit_kit = bool(patch_signals.get("onhit_buffed"))
    has_shield_or_heal = False
    for sp_data in raw_spells.values():
        if not isinstance(sp_data, dict):
            continue
        all_keys = list((sp_data.get("data_values") or {}).keys()) + list(
            (sp_data.get("calculations") or {}).keys()
        )
        for k in all_keys:
            kl = str(k).lower()
            if "onhit" in kl:
                has_onhit_kit = True
            if "shield" in kl or "heal" in kl:
                has_shield_or_heal = True

    is_marksman = "Marksman" in tags_set
    is_tank = "Tank" in tags_set and sum_ap < 1.3 and sum_ad < 1.8
    # Pure AP marksman/mage kits (e.g., Mage+Marksman with sum_ad=0 and sum_ap>=0.8) must not be flagged as AD
    is_ap_only_marksman = is_marksman and "Mage" in tags_set and sum_ap >= 0.8 and sum_ad < 0.3
    # A minor AP utility ratio on an AD marksman (e.g., traps) must not classify them as an AP user
    is_ap_user = (sum_ap >= 0.65 and not (is_marksman and sum_ad >= sum_ap)) or (
        "Mage" in tags_set and sum_ap >= sum_ad
    )
    is_ad_user = (
        sum_ad >= 0.65
        or (is_marksman and not is_ap_only_marksman)
        or (bool(tags_set & {"Fighter", "Assassin"}) and sum_ad >= sum_ap)
    )

    if not is_ap_user and not is_ad_user:
        if "Mage" in tags_set or "Support" in tags_set:
            is_ap_user = True
        else:
            is_ad_user = True

    uses_mana = (partype or "Mana").strip().lower() == "mana"

    default_range = 175.0 if (tags_set & {"Tank", "Fighter", "Assassin"} and not (tags_set & {"Marksman", "Mage"})) else 550.0
    attack_range = float(base_stats.get("attack_range", default_range))
    is_melee = attack_range <= 300.0
    is_ranged = not is_melee

    min_basic_cd = round(min(basic_max_cds), 2) if basic_max_cds else 7.0
    avg_basic_cd = round(sum(basic_max_cds) / len(basic_max_cds), 2) if basic_max_cds else 9.0
    mana_burn_per_sec = round(sum(basic_max_manas) / max(3.0, avg_basic_cd), 2) if (uses_mana and basic_max_manas) else 0.0

    # Data-driven gameplay archetypes (zero champion-name hardcoding)
    is_aa_onhit_mage = is_ap_user and ("Marksman" in tags_set or has_onhit_kit)
    is_ranged_control_mage = (
        is_ap_user
        and not is_ad_user
        and is_ranged
        and not is_aa_onhit_mage
        and "Assassin" not in tags_set
        and "Fighter" not in tags_set
    )
    is_spell_caster_adc = (
        is_marksman
        and is_ad_user
        and uses_mana
        and ("Mage" in tags_set or "Assassin" in tags_set or sum_ad >= 2.8)
    )
    is_crit_marksman = is_marksman and is_ad_user and not is_spell_caster_adc
    is_ap_bruiser_or_tank = is_melee and is_ap_user and bool(tags_set & {"Tank", "Fighter"})

    if is_aa_onhit_mage:
        kit_archetype_label = "On-Hit Mage / Marksman"
    elif is_ranged_control_mage:
        kit_archetype_label = "Long-Range Control / Burst Mage"
    elif is_spell_caster_adc:
        kit_archetype_label = "Spell-Caster ADC"
    elif is_crit_marksman:
        kit_archetype_label = "Crit & Sustained DPS Marksman"
    elif is_ap_bruiser_or_tank:
        kit_archetype_label = "Melee AP Fighter / Tank"
    elif is_tank:
        kit_archetype_label = "Frontline Tank"
    elif is_ap_user and "Assassin" in tags_set:
        kit_archetype_label = "Mobile AP Assassin"
    elif is_ad_user and "Assassin" in tags_set:
        kit_archetype_label = "AD Assassin / Skirmisher"
    elif is_ad_user:
        kit_archetype_label = "AD Fighter"
    else:
        kit_archetype_label = "Hybrid / Versatile Champion"

    return {
        "sum_ap": round(sum_ap, 3),
        "sum_ad": round(sum_ad, 3),
        "sum_tank": round(sum_tank, 3),
        "is_ap_user": is_ap_user,
        "is_ad_user": is_ad_user,
        "is_hybrid": is_ap_user and is_ad_user,
        "is_marksman": is_marksman,
        "is_tank": is_tank,
        "uses_mana": uses_mana,
        "attack_range": attack_range,
        "is_melee": is_melee,
        "is_ranged": is_ranged,
        "min_basic_cd": min_basic_cd,
        "avg_basic_cd": avg_basic_cd,
        "mana_burn_per_sec": mana_burn_per_sec,
        "has_onhit_kit": has_onhit_kit,
        "has_shield_or_heal": has_shield_or_heal,
        "is_aa_onhit_mage": is_aa_onhit_mage,
        "is_ranged_control_mage": is_ranged_control_mage,
        "is_spell_caster_adc": is_spell_caster_adc,
        "is_crit_marksman": is_crit_marksman,
        "is_ap_bruiser_or_tank": is_ap_bruiser_or_tank,
        "kit_archetype_label": kit_archetype_label,
        "patch_signals": patch_signals,
        "tags": sorted(tags_set),
    }


def _is_boot_item(item: Dict[str, Any]) -> bool:
    tags = set(item.get("tags") or [])
    ug = set(item.get("unique_groups") or [])
    return "Boots" in tags or "Boots" in ug


def filter_candidate_items(
    items: List[Dict[str, Any]],
    profile: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Filters out items incompatible with the champion kit (e.g., Rabadon on zero-AP AD champions,
    Lich Bane / Nashor's Tooth on long-range control mages, heavy mana items on resourceless champs,
    boots, and component items). Returns completed legendary item candidates only.
    """
    valid: List[Dict[str, Any]] = []
    seen_ids: Set[str] = set()

    for item in items:
        iid = str(item.get("item_id", ""))
        if not iid or iid in seen_ids:
            continue
        seen_ids.add(iid)

        gold = int(item.get("gold_total", 0))
        stats = {k: v for k, v in (item.get("stats") or {}).items() if not k.startswith("_")}
        ug = set(item.get("unique_groups") or [])

        if gold < 2000 or _is_boot_item(item):
            continue
        if not stats:
            continue

        ap = float(stats.get("ap", 0.0))
        ad = float(stats.get("ad", 0.0))
        hp = float(stats.get("hp", 0.0))
        armor = float(stats.get("armor", 0.0))
        mr = float(stats.get("mr", 0.0))
        mana = float(stats.get("mana", 0.0))
        attack_speed = float(stats.get("attack_speed", 0.0))
        crit = float(stats.get("crit_chance", 0.0))
        lethality = float(stats.get("lethality", 0.0))
        armor_pen = float(stats.get("armor_pen_percent", 0.0))
        magic_pen = float(stats.get("magic_pen_flat", 0.0)) + float(stats.get("magic_pen_percent", 0.0))

        # Avoid recommending heavy mana items on resourceless champions
        if not profile["uses_mana"] and mana >= 400.0:
            continue

        is_pure_ap_item = (ap > 0.0 or magic_pen > 0.0) and ad == 0.0 and lethality == 0.0 and crit == 0.0
        is_pure_ad_item = (ad > 0.0 or lethality > 0.0 or armor_pen > 0.0 or crit > 0.0) and ap == 0.0

        # Pure AP champion: require AP / Magic Pen items only
        if profile["is_ap_user"] and not profile["is_ad_user"] and not profile["is_tank"]:
            if is_pure_ad_item:
                continue
            if ap == 0.0 and magic_pen == 0.0:
                continue
            # Long-range control/burst mages avoid auto-attack range items (Lich Bane / Nashor's Tooth);
            # On-Hit mages/marksmen (e.g., Azir archetype) retain access to Nashor's Tooth.
            if profile.get("is_ranged_control_mage"):
                if "Spellblade" in ug or iid == "3100":
                    continue
                if attack_speed >= 0.25 or iid == "3115":
                    continue
            elif (
                attack_speed >= 0.35
                and not profile.get("is_aa_onhit_mage")
                and "Assassin" not in profile["tags"]
                and "Fighter" not in profile["tags"]
            ):
                continue

        # Pure AD / Marksman champion: require AD / AS / Crit / Lethality items only
        if profile["is_ad_user"] and not profile["is_ap_user"] and not profile["is_tank"]:
            if is_pure_ap_item:
                continue
            if ad == 0.0 and attack_speed == 0.0 and crit == 0.0 and lethality == 0.0:
                continue
            # Spell-caster ADCs (e.g., Ezreal archetype) prefer AD/Haste/Spellblade over 0-AD Zeal items
            if profile.get("is_spell_caster_adc") and ad == 0.0 and attack_speed >= 0.35 and crit > 0.0:
                continue
            # Exclude Support/Assassin utility vision items (Umbral Glaive) and pure lethality clutter for crit marksmen
            if profile.get("is_marksman") and "Assassin" not in profile["tags"]:
                if iid == "3179":  # Umbral Glaive
                    continue
                if profile.get("is_crit_marksman") and lethality > 0.0 and crit == 0.0 and attack_speed == 0.0:
                    continue

        # Pure Tank champion: block glass-cannon AP/Lethality/Crit items
        if profile["is_tank"]:
            has_tank_stat = hp >= 200.0 or armor >= 25.0 or mr >= 25.0
            if not has_tank_stat:
                continue
            if lethality > 0.0 or crit > 0.0:
                continue
            if ap > 0.0 and profile["sum_ap"] < 0.4:
                continue

        valid.append(item)

    return valid


def select_optimal_boot(
    all_items: List[Dict[str, Any]],
    profile: Dict[str, Any],
    playstyle: str,
    target_profile: str,
    rules: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """
    Selects the best boot item for the champion profile, playstyle, and Season 16 Role Quest.
    When Mid Role Quest is active (tier3_boots=True), selects Tier-3 upgraded boots (317x);
    otherwise selects standard Tier-2 boots (3006, 3020, 3047, 3111, 3158, 3009).
    """
    boots = {
        str(i["item_id"]): i
        for i in all_items
        if _is_boot_item(i) and int(i.get("gold_total", 0)) >= 900
    }
    if not boots:
        return None

    use_tier3 = bool(rules.get("tier3_boots"))

    if use_tier3:
        if profile["is_tank"] or (playstyle == "balanced" and not profile["is_marksman"] and not profile["is_ap_user"]):
            preferred = ["3174", "3173", "3171", "3047", "3111"]
        elif profile["is_ap_user"] and not profile["is_ad_user"]:
            if profile.get("is_aa_onhit_mage") and playstyle == "dps":
                preferred = ["3175", "3172", "3171", "3020", "3006"]
            else:
                preferred = ["3171", "3175", "3173", "3158", "3020"] if playstyle == "balanced" else ["3175", "3171", "3020"]
        elif profile.get("is_spell_caster_adc"):
            preferred = ["3171", "3158", "3172", "3006", "3174"]
        elif profile["is_marksman"] or (playstyle == "dps" and profile["is_ad_user"] and not profile["is_ap_user"]):
            preferred = ["3172", "3006", "3171", "3174"]
        else:
            preferred = ["3171", "3174", "3173", "3170", "3158", "3047"]
    else:
        if profile["is_tank"] or (playstyle == "balanced" and not profile["is_marksman"] and not profile["is_ap_user"]):
            preferred = ["3047", "3111", "3158", "3009"] if target_profile != "squishy" else ["3111", "3047", "3158"]
        elif profile["is_ap_user"] and not profile["is_ad_user"]:
            if profile.get("is_aa_onhit_mage") and playstyle == "dps":
                preferred = ["3020", "3006", "3158"]
            else:
                preferred = ["3158", "3020", "3111"] if playstyle == "balanced" else ["3020", "3158", "3009"]
        elif profile.get("is_spell_caster_adc"):
            preferred = ["3158", "3006", "3047", "3111"]
        elif profile["is_marksman"] or (playstyle == "dps" and profile["is_ad_user"] and not profile["is_ap_user"]):
            preferred = ["3006", "3158", "3047", "3111", "3009"]
        elif rules.get("role") == "support":
            preferred = ["3158", "3009", "3111", "3047"]
        else:
            preferred = ["3158", "3047", "3111", "3006", "3009"]

    chosen = next((boots[pid] for pid in preferred if pid in boots), next(iter(boots.values())))
    slot_type = (
        "role_quest_boot"
        if rules.get("separate_boot_slot")
        else ("tier3_boot" if use_tier3 else "standard_boot")
    )
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


def order_build_items(
    legendaries: List[Dict[str, Any]],
    boot: Optional[Dict[str, Any]],
    profile: Dict[str, Any],
    rules: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Orders the selected 5 (or 6 for ADC) legendary items and boots into a realistic match buy order:
    1st Core -> Boots -> 2nd -> 3rd -> 4th -> 5th (-> 6th).
    """
    def _buy_priority(item: Dict[str, Any]) -> Tuple[int, int]:
        iid = str(item.get("item_id", ""))
        stats = item.get("stats") or {}
        mana = float(stats.get("mana", 0.0))
        gold = int(item.get("gold_total", 3000))

        # 0: Core rush item (Mana/Tempo item or Spell-Caster ADC core)
        if profile.get("uses_mana") and profile.get("is_ap_user") and mana >= 400.0:
            return (0, gold)
        if profile.get("is_spell_caster_adc") and iid in ("3078", "3004"):
            return (0, gold)
        if profile.get("is_aa_onhit_mage") and iid == "3115":
            return (0, gold)
        if iid in FIRST_ITEM_PRIORITY_IDS:
            return (1, gold)
        # 3: Late-game multiplier / % penetration / defensive capstone
        if iid in LATE_CAPSTONE_IDS or float(stats.get("ap_multiplier", 0.0)) > 0:
            return (3, gold)
        # 2: Mid-game power spike
        return (2, gold)

    sorted_legs = sorted(legendaries, key=_buy_priority)
    formatted_legs = [
        {
            "item_id": str(i["item_id"]),
            "name": i["name"],
            "gold_total": int(i.get("gold_total", 0)),
            "stats": {k: v for k, v in (i.get("stats") or {}).items() if not k.startswith("_")},
            "icon_url": i.get("icon_url"),
            "is_boot": False,
            "slot_type": "legendary",
        }
        for i in sorted_legs
    ]

    ordered: List[Dict[str, Any]] = []
    if formatted_legs:
        ordered.append(formatted_legs[0])
    if boot:
        ordered.append(boot)
    ordered.extend(formatted_legs[1:])

    for idx, entry in enumerate(ordered, start=1):
        entry["buy_order"] = idx
    return ordered


def select_candidate_keystones(profile: Dict[str, Any]) -> List[str]:
    """Selects 4-5 best-fitting keystone candidates for the champion's archetype."""
    tags = set(profile.get("tags") or [])
    candidates: List[str] = []

    if profile["is_tank"]:
        candidates = ["GraspOfTheUndying", "Aftershock", "Conqueror", "PhaseRush"]
    elif profile.get("is_aa_onhit_mage"):
        candidates = ["LethalTempo", "Conqueror", "PressTheAttack", "FirstStrike", "Electrocute"]
    elif profile.get("is_spell_caster_adc"):
        candidates = ["PressTheAttack", "Conqueror", "FirstStrike", "LethalTempo", "FleetFootwork"]
    elif profile["is_marksman"]:
        candidates = ["LethalTempo", "PressTheAttack", "FleetFootwork", "Conqueror", "HailOfBlades"]
    elif profile["is_ap_user"] and not profile["is_ad_user"]:
        candidates = ["Electrocute", "ArcaneComet", "FirstStrike", "DarkHarvest", "Conqueror"]
    elif "Assassin" in tags:
        candidates = ["Electrocute", "FirstStrike", "Conqueror", "DarkHarvest", "HailOfBlades"]
    elif "Fighter" in tags:
        candidates = ["Conqueror", "PressTheAttack", "GraspOfTheUndying", "LethalTempo", "Electrocute"]
    else:
        candidates = ["Conqueror", "Electrocute", "PressTheAttack", "FirstStrike", "ArcaneComet"]

    return [k for k in candidates if k in SUPPORTED_KEYSTONES]


def _has_unique_conflict(existing_items: List[Dict[str, Any]], candidate: Dict[str, Any]) -> bool:
    cand_id = str(candidate.get("item_id"))
    cand_groups = set(candidate.get("unique_groups") or [])
    for it in existing_items:
        if str(it.get("item_id")) == cand_id:
            return True
        if cand_groups and (cand_groups & set(it.get("unique_groups") or [])):
            return True
    return False


class BuildOptimizerEngine:
    """
    Constrained Beam Search optimizer aware of Season 16 Role Quests
    (6 items / 7 items with dedicated boot slot for ADC, Level 20 cap for Top)
    and game mode rules (Summoner's Rift / ARAM / Swiftplay).
    Produces 3 complete builds with buy order and synchronized full rune pages.
    """

    @staticmethod
    def _score_simulation(
        sim: Dict[str, Any],
        base_stats: Dict[str, float],
        items: List[Dict[str, Any]],
        objective: str,
        profile: Dict[str, Any],
        rules: Dict[str, Any],
    ) -> Tuple[float, Dict[str, Any]]:
        curves = sim["level_curves"]
        max_idx = len(curves) - 1
        lvl11 = curves[10]
        lvl_late = curves[max_idx]  # Level 20 for Top Lane, Level 18 for all other roles
        total_gold = max(1, sum(int(i.get("gold_total", 0)) for i in items))

        early_w = float(rules.get("early_spike_weight", 1.0))
        mid_share = min(0.65, 0.45 * early_w)
        late_share = 1.0 - mid_share

        burst_val = mid_share * lvl11["new_burst"] + late_share * lvl_late["new_burst"]
        dps_val = mid_share * lvl11["new_dps"] + late_share * lvl_late["new_dps"]
        ttk_val = mid_share * lvl11["new_ttk_sec"] + late_share * lvl_late["new_ttk_sec"]

        stat_vecs = StatAggregator.compute_level_vectors(
            base_stats, items, max_level=int(rules.get("max_level", 18))
        )
        ehp_bonus = 1.0 + float(sim.get("active_effects", {}).get("ehp_bonus_pct", 0.0)) / 100.0
        phys_ehp_11 = float(stat_vecs["total_hp"][10] * (1.0 + stat_vecs["armor"][10] / 100.0) * ehp_bonus)
        magic_ehp_11 = float(stat_vecs["total_hp"][10] * (1.0 + stat_vecs["mr"][10] / 100.0) * ehp_bonus)
        avg_ehp_11 = 0.5 * (phys_ehp_11 + magic_ehp_11)
        ah = float(stat_vecs["ability_haste"][0])

        # Map + Champion Kit + Patch Diff Synergy Score
        real_items = [i for i in items if i.get("item_id") != "rune_page_bonuses" and not i.get("is_boot")]
        item_ids = {str(i.get("item_id", "")) for i in real_items}
        total_mana = sum(float((i.get("stats") or {}).get("mana", 0.0)) for i in real_items)
        total_crit = sum(float((i.get("stats") or {}).get("crit_chance", 0.0)) for i in real_items)
        total_ap = sum(float((i.get("stats") or {}).get("ap", 0.0)) for i in real_items)
        total_ad = sum(float((i.get("stats") or {}).get("ad", 0.0)) for i in real_items)
        total_as = sum(float((i.get("stats") or {}).get("attack_speed", 0.0)) for i in real_items)
        mana_item_count = sum(1 for i in real_items if float((i.get("stats") or {}).get("mana", 0.0)) >= 400.0)
        has_spellblade = any(
            "Spellblade" in (i.get("unique_groups") or []) or str(i.get("item_id")) in ("3078", "3100", "6662")
            for i in real_items
        )

        mana_bonus = 0.0
        if profile.get("uses_mana") and (
            profile.get("is_ap_user") or profile.get("is_spell_caster_adc") or rules.get("game_map") == "aram"
        ):
            mana_bonus = min(600.0, total_mana) * 0.24 * float(rules.get("mana_priority_weight", 1.0))
            # Slightly penalize stacking 3+ redundant mana items
            if mana_item_count >= 3:
                mana_bonus -= (mana_item_count - 2) * 140.0

        kit_bonus = 0.0
        patch_signals = profile.get("patch_signals") or {}

        # 1. On-Hit Mage / Marksman -> Attack Speed + AP synergy
        if profile.get("is_aa_onhit_mage"):
            if total_as >= 0.35:
                kit_bonus += 260.0 if patch_signals.get("onhit_buffed") else 150.0
            if "3115" in item_ids:
                kit_bonus += 240.0 if patch_signals.get("onhit_buffed") else 120.0

        # 2. Spell-Caster ADC -> Spellblade (Trinity Force) + Manamune + Ability Haste
        if profile.get("is_spell_caster_adc"):
            if has_spellblade:
                kit_bonus += 320.0
            if "3004" in item_ids:
                kit_bonus += 280.0
            kit_bonus += min(65.0, ah) * 6.0
            # Favor Spellblade+Mana+Pen over stacking pure assassin lethality items
            pure_leth_count = sum(
                1
                for i in real_items
                if float((i.get("stats") or {}).get("lethality", 0.0)) > 0
                and float((i.get("stats") or {}).get("crit_chance", 0.0)) == 0
                and str(i.get("item_id")) != "6694"
            )
            if pure_leth_count >= 2:
                kit_bonus -= (pure_leth_count - 1) * 260.0

        # 3. Crit Marksman -> penalize over-capping >100% crit, reward Infinity Edge + Crit scaling
        if profile.get("is_crit_marksman"):
            if total_crit > 1.01:
                kit_bonus -= (total_crit - 1.0) * 650.0
            elif total_crit >= 0.75:
                kit_bonus += 180.0
            if "3031" in item_ids and total_crit >= 0.50:
                kit_bonus += 180.0

        # 4. Dynamic adaptation to latest patch deltas
        if patch_signals.get("cd_or_mana_nerfed"):
            kit_bonus += min(65.0, ah) * 4.5
            if mana_item_count >= 1:
                kit_bonus += 120.0
        if patch_signals.get("ap_scaling_buffed"):
            kit_bonus += min(500.0, total_ap) * 0.25
        if patch_signals.get("ad_scaling_buffed"):
            kit_bonus += min(320.0, total_ad) * 0.40
        if patch_signals.get("range_buffed") and objective == "dps":
            kit_bonus += min(1.0, total_as) * 140.0
        if patch_signals.get("defensive_buffed") and objective == "balanced":
            kit_bonus += avg_ehp_11 * 0.05

        ref_gold = 16500.0 if int(rules.get("legendary_slots", 5)) == 5 else 19500.0
        gold_factor = ref_gold / max(9000.0, float(total_gold))
        gold_eff = round((burst_val + dps_val * 2.5) / (total_gold / 1000.0), 1)

        if objective == "burst":
            score = (
                burst_val * 1.15
                + dps_val * 0.85
                + (1000.0 / max(0.5, ttk_val))
                + mana_bonus
                + kit_bonus
            ) * (0.85 + 0.15 * gold_factor)
        elif objective == "dps":
            score = (
                dps_val * 3.8
                + burst_val * 0.35
                + (800.0 / max(0.5, ttk_val))
                + mana_bonus
                + kit_bonus
            ) * (0.85 + 0.15 * gold_factor)
        else:
            ehp_weight = 0.45 if profile["is_tank"] else 0.14 * float(rules.get("sustain_priority_weight", 1.0))
            score = (
                burst_val * 0.65
                + dps_val * 2.00
                + avg_ehp_11 * ehp_weight
                + ah * 7.5
                + mana_bonus
                + kit_bonus
            ) * (0.85 + 0.15 * gold_factor)

        metrics = {
            "lvl11_burst": lvl11["new_burst"],
            "lvl18_burst": curves[17]["new_burst"],
            "lvl_max_burst": lvl_late["new_burst"],
            "lvl11_dps": lvl11["new_dps"],
            "lvl18_dps": curves[17]["new_dps"],
            "lvl_max_dps": lvl_late["new_dps"],
            "lvl11_ttk_sec": lvl11["new_ttk_sec"],
            "lvl18_ttk_sec": curves[17]["new_ttk_sec"],
            "max_level": int(rules.get("max_level", 18)),
            "phys_ehp_lvl11": round(phys_ehp_11, 1),
            "magic_ehp_lvl11": round(magic_ehp_11, 1),
            "ability_haste": round(ah, 1),
            "gold_efficiency_index": gold_eff,
        }
        return round(float(score), 2), metrics

    @classmethod
    def optimize_builds(
        cls,
        champion_key: str,
        base_stats: Dict[str, float],
        base_abilities: Dict[str, Any],
        candidate_items: List[Dict[str, Any]],
        tags: Optional[List[str]] = None,
        partype: Optional[str] = None,
        patch_diff: Optional[ChampionPatchDiff] = None,
        champion_patch_diff: Optional[Dict[str, Any]] = None,
        target_profile_key: str = "squishy",
        role: Optional[str] = None,
        game_map: str = "sr",
        db_runes: Optional[List[Dict[str, Any]]] = None,
        core_slots: Optional[int] = None,
        beam_width: int = 4,
        top_pool_size: int = 14,
    ) -> Dict[str, Any]:
        """
        Discovers 3 distinct full-build variations (6 items total, or 7 for SR ADC) with
        realistic buy order and full rune pages tailored to champion, role, map, and patch diffs.
        """
        patch_signals = analyze_patch_diff_signals(champion_patch_diff or patch_diff)
        profile = infer_champion_profile(
            base_abilities,
            tags=tags,
            partype=partype,
            base_stats=base_stats,
            patch_signals=patch_signals,
        )
        resolved_role = role or infer_default_role(tags)
        rules = resolve_effective_rules(role=resolved_role, game_map=game_map)

        filtered_items = filter_candidate_items(candidate_items, profile)
        candidate_keystones = select_candidate_keystones(profile)
        default_keystone = candidate_keystones[0] if candidate_keystones else "Electrocute"

        target_leg_slots = int(core_slots if core_slots is not None else rules["legendary_slots"])
        # Safely cap target slots when running unit tests with small item pools
        effective_slots = min(target_leg_slots, len(filtered_items))

        if effective_slots < 1:
            return {
                "champion_key": champion_key,
                "target_profile": target_profile_key,
                "game_context": rules,
                "profile": profile,
                "candidate_pool_size": len(filtered_items),
                "variations": [],
            }

        objectives = ["burst", "dps", "balanced"]
        selected_variations: List[Dict[str, Any]] = []
        used_signatures: Set[Tuple[Tuple[str, ...], Optional[str]]] = set()

        for obj in objectives:
            boot = select_optimal_boot(candidate_items, profile, obj, target_profile_key, rules)
            boot_list = [boot] if boot else []

            # 1. Fast 1-item pre-ranking to prune pool down to top_pool_size items
            single_scored: List[Tuple[float, Dict[str, Any]]] = []
            for it in filtered_items:
                sim = CombatSimulator.run_simulation(
                    champion_key=champion_key,
                    base_stats=base_stats,
                    base_abilities=base_abilities,
                    patch_diff=patch_diff,
                    items=boot_list + [it],
                    target_profile_key=target_profile_key,
                    keystone_key=default_keystone,
                    role=resolved_role,
                    game_map=game_map,
                )
                sc, _ = cls._score_simulation(sim, base_stats, boot_list + [it], obj, profile, rules)
                single_scored.append((sc, it))

            single_scored.sort(key=lambda x: x[0], reverse=True)
            pool = [it for _, it in single_scored[:top_pool_size]]

            # 2. Beam Search: expand 1 -> effective_slots (5, or 6 for SR ADC) legendary items
            beam: List[Tuple[float, List[Dict[str, Any]]]] = [
                (sc, [it]) for sc, it in single_scored[:beam_width]
            ]

            for _depth in range(2, effective_slots + 1):
                next_candidates: List[Tuple[float, List[Dict[str, Any]]]] = []
                seen_combos: Set[Tuple[str, ...]] = set()

                for _, current_build in beam:
                    for cand in pool:
                        if _has_unique_conflict(current_build, cand):
                            continue
                        combo = current_build + [cand]
                        sig = tuple(sorted(str(i["item_id"]) for i in combo))
                        if sig in seen_combos:
                            continue
                        seen_combos.add(sig)

                        full_items = boot_list + combo
                        sim = CombatSimulator.run_simulation(
                            champion_key=champion_key,
                            base_stats=base_stats,
                            base_abilities=base_abilities,
                            patch_diff=patch_diff,
                            items=full_items,
                            target_profile_key=target_profile_key,
                            keystone_key=default_keystone,
                            role=resolved_role,
                            game_map=game_map,
                        )
                        sc, _ = cls._score_simulation(sim, base_stats, full_items, obj, profile, rules)
                        next_candidates.append((sc, combo))

                if not next_candidates:
                    break
                next_candidates.sort(key=lambda x: x[0], reverse=True)
                beam = next_candidates[:beam_width]

            # 3. Evaluate all candidate Keystones & Full Rune Pages across top complete builds
            final_ranked: List[Dict[str, Any]] = []
            for _, leg_items in beam[:3]:
                ordered_items = order_build_items(leg_items, boot, profile, rules)
                item_sig = tuple(sorted(str(i["item_id"]) for i in ordered_items))

                for ks in candidate_keystones:
                    rune_page = FullRunePageEngine.build_full_rune_page(
                        keystone_key=ks,
                        items=ordered_items,
                        profile=profile,
                        playstyle=obj,
                        target_profile=target_profile_key,
                        role=resolved_role,
                        game_map=game_map,
                        db_runes=db_runes,
                    )
                    # Include minor rune & stat shard bonuses in the final combat simulation
                    rune_stat_entry = {
                        "item_id": "rune_page_bonuses",
                        "name": "Rune Page Bonuses",
                        "gold_total": 0,
                        "stats": rune_page["stat_bonuses"],
                    }
                    sim_items = ordered_items + [rune_stat_entry]

                    sim = CombatSimulator.run_simulation(
                        champion_key=champion_key,
                        base_stats=base_stats,
                        base_abilities=base_abilities,
                        patch_diff=patch_diff,
                        items=sim_items,
                        target_profile_key=target_profile_key,
                        keystone_key=ks,
                        role=resolved_role,
                        game_map=game_map,
                    )
                    sc, metrics = cls._score_simulation(sim, base_stats, sim_items, obj, profile, rules)
                    final_ranked.append(
                        {
                            "signature": (item_sig, ks),
                            "playstyle": obj,
                            "playstyle_label": PLAYSTYLE_LABELS[obj],
                            "score": sc,
                            "total_gold": sum(int(i.get("gold_total", 0)) for i in ordered_items),
                            "item_count": len(ordered_items),
                            "items": ordered_items,
                            "boot": boot,
                            "keystone": {
                                "key": ks,
                                "label": rune_page["primary_tree"]["keystone"]["name"],
                                "tree": rune_page["primary_tree"]["name"],
                            },
                            "rune_page": rune_page,
                            "active_effects": sim.get("active_effects") or {},
                            "metrics": metrics,
                        }
                    )

            final_ranked.sort(key=lambda x: x["score"], reverse=True)
            chosen = next(
                (cand for cand in final_ranked if cand["signature"] not in used_signatures),
                final_ranked[0] if final_ranked else None,
            )
            if chosen:
                used_signatures.add(chosen["signature"])
                chosen_clean = {k: v for k, v in chosen.items() if k != "signature"}
                selected_variations.append(chosen_clean)

        return {
            "champion_key": champion_key,
            "target_profile": target_profile_key,
            "game_context": rules,
            "profile": profile,
            "candidate_pool_size": len(filtered_items),
            "variations": selected_variations,
        }
