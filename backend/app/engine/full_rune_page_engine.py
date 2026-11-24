from typing import Any, Dict, List, Optional, Tuple

from app.engine.game_rules import resolve_effective_rules

# Season 16 (26.23) official Riot rune catalog used as an offline fallback when DB runes are omitted
DEFAULT_SEASON16_RUNES: List[Dict[str, Any]] = [
    # Domination
    {"rune_id": 8112, "key": "Electrocute", "name": "Electrocute", "tree_key": "Domination", "tree_name": "Domination", "slot_index": 0},
    {"rune_id": 8128, "key": "DarkHarvest", "name": "Dark Harvest", "tree_key": "Domination", "tree_name": "Domination", "slot_index": 0},
    {"rune_id": 9923, "key": "HailOfBlades", "name": "Hail of Blades", "tree_key": "Domination", "tree_name": "Domination", "slot_index": 0},
    {"rune_id": 8126, "key": "CheapShot", "name": "Cheap Shot", "tree_key": "Domination", "tree_name": "Domination", "slot_index": 1},
    {"rune_id": 8139, "key": "TasteOfBlood", "name": "Taste of Blood", "tree_key": "Domination", "tree_name": "Domination", "slot_index": 1},
    {"rune_id": 8143, "key": "SuddenImpact", "name": "Sudden Impact", "tree_key": "Domination", "tree_name": "Domination", "slot_index": 1},
    {"rune_id": 8137, "key": "SixthSense", "name": "Sixth Sense", "tree_key": "Domination", "tree_name": "Domination", "slot_index": 2},
    {"rune_id": 8140, "key": "GrislyMementos", "name": "Grisly Mementos", "tree_key": "Domination", "tree_name": "Domination", "slot_index": 2},
    {"rune_id": 8141, "key": "DeepWard", "name": "Deep Ward", "tree_key": "Domination", "tree_name": "Domination", "slot_index": 2},
    {"rune_id": 8105, "key": "RelentlessHunter", "name": "Relentless Hunter", "tree_key": "Domination", "tree_name": "Domination", "slot_index": 3},
    {"rune_id": 8106, "key": "UltimateHunter", "name": "Ultimate Hunter", "tree_key": "Domination", "tree_name": "Domination", "slot_index": 3},
    {"rune_id": 8135, "key": "TreasureHunter", "name": "Treasure Hunter", "tree_key": "Domination", "tree_name": "Domination", "slot_index": 3},
    # Precision
    {"rune_id": 8005, "key": "PressTheAttack", "name": "Press the Attack", "tree_key": "Precision", "tree_name": "Precision", "slot_index": 0},
    {"rune_id": 8008, "key": "LethalTempo", "name": "Lethal Tempo", "tree_key": "Precision", "tree_name": "Precision", "slot_index": 0},
    {"rune_id": 8010, "key": "Conqueror", "name": "Conqueror", "tree_key": "Precision", "tree_name": "Precision", "slot_index": 0},
    {"rune_id": 8021, "key": "FleetFootwork", "name": "Fleet Footwork", "tree_key": "Precision", "tree_name": "Precision", "slot_index": 0},
    {"rune_id": 8009, "key": "PresenceOfMind", "name": "Presence of Mind", "tree_key": "Precision", "tree_name": "Precision", "slot_index": 1},
    {"rune_id": 9101, "key": "AbsorbLife", "name": "Absorb Life", "tree_key": "Precision", "tree_name": "Precision", "slot_index": 1},
    {"rune_id": 9111, "key": "Triumph", "name": "Triumph", "tree_key": "Precision", "tree_name": "Precision", "slot_index": 1},
    {"rune_id": 9103, "key": "LegendBloodline", "name": "Legend: Bloodline", "tree_key": "Precision", "tree_name": "Precision", "slot_index": 2},
    {"rune_id": 9104, "key": "LegendAlacrity", "name": "Legend: Alacrity", "tree_key": "Precision", "tree_name": "Precision", "slot_index": 2},
    {"rune_id": 9105, "key": "LegendHaste", "name": "Legend: Haste", "tree_key": "Precision", "tree_name": "Precision", "slot_index": 2},
    {"rune_id": 8014, "key": "CoupDeGrace", "name": "Coup de Grâce", "tree_key": "Precision", "tree_name": "Precision", "slot_index": 3},
    {"rune_id": 8017, "key": "CutDown", "name": "Cut Down", "tree_key": "Precision", "tree_name": "Precision", "slot_index": 3},
    {"rune_id": 8299, "key": "LastStand", "name": "Last Stand", "tree_key": "Precision", "tree_name": "Precision", "slot_index": 3},
    # Sorcery
    {"rune_id": 8214, "key": "SummonAery", "name": "Summon Aery", "tree_key": "Sorcery", "tree_name": "Sorcery", "slot_index": 0},
    {"rune_id": 8229, "key": "ArcaneComet", "name": "Arcane Comet", "tree_key": "Sorcery", "tree_name": "Sorcery", "slot_index": 0},
    {"rune_id": 8230, "key": "PhaseRush", "name": "Phase Rush", "tree_key": "Sorcery", "tree_name": "Sorcery", "slot_index": 0},
    {"rune_id": 8224, "key": "NullifyingOrb", "name": "Axiom Arcanist", "tree_key": "Sorcery", "tree_name": "Sorcery", "slot_index": 1},
    {"rune_id": 8226, "key": "ManaflowBand", "name": "Manaflow Band", "tree_key": "Sorcery", "tree_name": "Sorcery", "slot_index": 1},
    {"rune_id": 8275, "key": "NimbusCloak", "name": "Nimbus Cloak", "tree_key": "Sorcery", "tree_name": "Sorcery", "slot_index": 1},
    {"rune_id": 8210, "key": "Transcendence", "name": "Transcendence", "tree_key": "Sorcery", "tree_name": "Sorcery", "slot_index": 2},
    {"rune_id": 8233, "key": "AbsoluteFocus", "name": "Absolute Focus", "tree_key": "Sorcery", "tree_name": "Sorcery", "slot_index": 2},
    {"rune_id": 8234, "key": "Celerity", "name": "Celerity", "tree_key": "Sorcery", "tree_name": "Sorcery", "slot_index": 2},
    {"rune_id": 8232, "key": "Waterwalking", "name": "Waterwalking", "tree_key": "Sorcery", "tree_name": "Sorcery", "slot_index": 3},
    {"rune_id": 8236, "key": "GatheringStorm", "name": "Gathering Storm", "tree_key": "Sorcery", "tree_name": "Sorcery", "slot_index": 3},
    {"rune_id": 8237, "key": "Scorch", "name": "Scorch", "tree_key": "Sorcery", "tree_name": "Sorcery", "slot_index": 3},
    # Resolve
    {"rune_id": 8437, "key": "GraspOfTheUndying", "name": "Grasp of the Undying", "tree_key": "Resolve", "tree_name": "Resolve", "slot_index": 0},
    {"rune_id": 8439, "key": "Aftershock", "name": "Aftershock", "tree_key": "Resolve", "tree_name": "Resolve", "slot_index": 0},
    {"rune_id": 8465, "key": "Guardian", "name": "Guardian", "tree_key": "Resolve", "tree_name": "Resolve", "slot_index": 0},
    {"rune_id": 8401, "key": "ShieldBash", "name": "Shield Bash", "tree_key": "Resolve", "tree_name": "Resolve", "slot_index": 1},
    {"rune_id": 8446, "key": "Demolish", "name": "Demolish", "tree_key": "Resolve", "tree_name": "Resolve", "slot_index": 1},
    {"rune_id": 8463, "key": "FontOfLife", "name": "Font of Life", "tree_key": "Resolve", "tree_name": "Resolve", "slot_index": 1},
    {"rune_id": 8429, "key": "Conditioning", "name": "Conditioning", "tree_key": "Resolve", "tree_name": "Resolve", "slot_index": 2},
    {"rune_id": 8444, "key": "SecondWind", "name": "Second Wind", "tree_key": "Resolve", "tree_name": "Resolve", "slot_index": 2},
    {"rune_id": 8473, "key": "BonePlating", "name": "Bone Plating", "tree_key": "Resolve", "tree_name": "Resolve", "slot_index": 2},
    {"rune_id": 8242, "key": "Unflinching", "name": "Unflinching", "tree_key": "Resolve", "tree_name": "Resolve", "slot_index": 3},
    {"rune_id": 8451, "key": "Overgrowth", "name": "Overgrowth", "tree_key": "Resolve", "tree_name": "Resolve", "slot_index": 3},
    {"rune_id": 8453, "key": "Revitalize", "name": "Revitalize", "tree_key": "Resolve", "tree_name": "Resolve", "slot_index": 3},
    # Inspiration
    {"rune_id": 8351, "key": "GlacialAugment", "name": "Glacial Augment", "tree_key": "Inspiration", "tree_name": "Inspiration", "slot_index": 0},
    {"rune_id": 8360, "key": "UnsealedSpellbook", "name": "Unsealed Spellbook", "tree_key": "Inspiration", "tree_name": "Inspiration", "slot_index": 0},
    {"rune_id": 8369, "key": "FirstStrike", "name": "First Strike", "tree_key": "Inspiration", "tree_name": "Inspiration", "slot_index": 0},
    {"rune_id": 8304, "key": "MagicalFootwear", "name": "Magical Footwear", "tree_key": "Inspiration", "tree_name": "Inspiration", "slot_index": 1},
    {"rune_id": 8306, "key": "HextechFlashtraption", "name": "Hextech Flashtraption", "tree_key": "Inspiration", "tree_name": "Inspiration", "slot_index": 1},
    {"rune_id": 8321, "key": "CashBack", "name": "Cash Back", "tree_key": "Inspiration", "tree_name": "Inspiration", "slot_index": 1},
    {"rune_id": 8313, "key": "PerfectTiming", "name": "Triple Tonic", "tree_key": "Inspiration", "tree_name": "Inspiration", "slot_index": 2},
    {"rune_id": 8345, "key": "BiscuitDelivery", "name": "Biscuit Delivery", "tree_key": "Inspiration", "tree_name": "Inspiration", "slot_index": 2},
    {"rune_id": 8352, "key": "TimeWarpTonic", "name": "Time Warp Tonic", "tree_key": "Inspiration", "tree_name": "Inspiration", "slot_index": 2},
    {"rune_id": 8316, "key": "JackOfAllTrades", "name": "Jack of All Trades", "tree_key": "Inspiration", "tree_name": "Inspiration", "slot_index": 3},
    {"rune_id": 8347, "key": "CosmicInsight", "name": "Cosmic Insight", "tree_key": "Inspiration", "tree_name": "Inspiration", "slot_index": 3},
    {"rune_id": 8410, "key": "ApproachVelocity", "name": "Approach Velocity", "tree_key": "Inspiration", "tree_name": "Inspiration", "slot_index": 3},
]


def _index_runes(db_runes: Optional[List[Dict[str, Any]]]) -> Dict[str, Dict[str, Any]]:
    source = db_runes if db_runes else DEFAULT_SEASON16_RUNES
    return {str(r["key"]): r for r in source}


def _build_item_context(
    items: List[Dict[str, Any]],
    profile: Dict[str, Any],
    game_rules: Dict[str, Any],
) -> Dict[str, Any]:
    total_mana = sum(float((i.get("stats") or {}).get("mana", 0.0)) for i in items)
    total_ah = sum(float((i.get("stats") or {}).get("ability_haste", 0.0)) for i in items)
    total_as = sum(float((i.get("stats") or {}).get("attack_speed", 0.0)) for i in items)
    total_hp = sum(float((i.get("stats") or {}).get("hp", 0.0)) for i in items)
    total_resists = sum(
        float((i.get("stats") or {}).get("armor", 0.0)) + float((i.get("stats") or {}).get("mr", 0.0))
        for i in items
    )
    total_lifesteal = sum(
        float((i.get("stats") or {}).get("lifesteal", 0.0))
        + float((i.get("stats") or {}).get("omnivamp", 0.0))
        for i in items
    )
    total_gold = sum(int(i.get("gold_total", 0)) for i in items)

    distinct_stats = set()
    for it in items:
        for k, v in (it.get("stats") or {}).items():
            if not k.startswith("_") and isinstance(v, (int, float)) and v > 0:
                distinct_stats.add(k)

    uses_mana = bool(profile.get("uses_mana", True))
    is_aram = game_rules.get("game_map") == "aram"
    is_mana_caster = bool(profile.get("is_ap_user")) and not bool(profile.get("is_marksman"))
    needs_mana = uses_mana and (
        (total_mana < 400.0 and (is_mana_caster or is_aram))
        or (is_aram and total_mana < 800.0)
    )

    return {
        "total_mana": total_mana,
        "total_ah": total_ah,
        "total_as": total_as,
        "total_hp": total_hp,
        "total_resists": total_resists,
        "total_lifesteal": total_lifesteal,
        "total_gold": total_gold,
        "distinct_stats_count": len(distinct_stats),
        "needs_mana": needs_mana,
        "is_aram": is_aram,
        "is_swiftplay": game_rules.get("game_map") == "swiftplay",
        "role": game_rules.get("role", "mid"),
        "legendary_slots": int(game_rules.get("legendary_slots", 5)),
    }


def _score_minor_rune(
    rune_key: str,
    ctx: Dict[str, Any],
    profile: Dict[str, Any],
    playstyle: str,
    target_profile: str,
) -> Tuple[float, Optional[str]]:
    """Scores a single minor rune against the item build, champion profile, target dummy, and map rules."""
    tags = set(profile.get("tags") or [])
    is_melee_bruiser = bool(tags & {"Fighter", "Tank"})
    is_assassin = "Assassin" in tags
    is_marksman = bool(profile.get("is_marksman"))
    is_ap = bool(profile.get("is_ap_user"))

    # --- DOMINATION ---
    if rune_key == "SuddenImpact":
        sc = 85.0 if (is_assassin or playstyle == "burst") else 55.0
        return sc, ("Amplifies burst and dash trades alongside item penetration." if sc >= 80 else None)
    if rune_key == "TasteOfBlood":
        sc = 88.0 if (ctx["is_aram"] or playstyle == "balanced") else 62.0
        return sc, ("Provides reliable lane and ARAM health sustain during repeated trades." if sc >= 80 else None)
    if rune_key == "CheapShot":
        sc = 72.0 if (is_ap and not is_assassin) else 50.0
        return sc, None
    if rune_key == "GrislyMementos":
        return (80.0 if ctx["role"] != "support" else 65.0), None
    if rune_key == "DeepWard":
        return (85.0 if ctx["role"] in ("jungle", "support") else 55.0), None
    if rune_key == "SixthSense":
        return 60.0, None
    if rune_key == "UltimateHunter":
        sc = 88.0 if (is_ap or ctx["is_aram"] or playstyle == "burst") else 68.0
        return sc, ("Shortens ultimate cooldown to maximize high-AP/AD ability rotations." if sc >= 85 else None)
    if rune_key == "TreasureHunter":
        sc = 86.0 if (ctx["total_gold"] >= 16500 or ctx["is_swiftplay"]) else 66.0
        return sc, ("Accelerates reaching expensive core item spikes earlier." if sc >= 85 else None)
    if rune_key == "RelentlessHunter":
        return (84.0 if ctx["role"] in ("jungle", "support") else 58.0), None

    # --- PRECISION ---
    if rune_key == "PresenceOfMind":
        sc = 96.0 if ctx["needs_mana"] else (40.0 if not profile.get("uses_mana") else 65.0)
        return sc, ("Offsets missing mana in items to keep abilities flowing continuously." if sc >= 90 else None)
    if rune_key == "Triumph":
        sc = 86.0 if (is_melee_bruiser or ctx["is_aram"] or not profile.get("uses_mana")) else 70.0
        return sc, ("Grants clutch takedown healing and bonus gold in extended teamfights." if sc >= 85 else None)
    if rune_key == "AbsorbLife":
        return (76.0 if is_marksman and not ctx["is_aram"] else 58.0), None
    if rune_key == "LegendAlacrity":
        sc = 92.0 if (is_marksman or playstyle == "dps" or ctx["total_as"] >= 0.4) else 50.0
        return sc, ("Stacks with Crit and On-Hit items to maximize sustained auto-attack DPS." if sc >= 85 else None)
    if rune_key == "LegendHaste":
        sc = 90.0 if (is_ap or (not is_marksman and ctx["total_ah"] < 45)) else 60.0
        return sc, ("Supplements item Ability Haste for faster basic ability rotations." if sc >= 85 else None)
    if rune_key == "LegendBloodline":
        sc = 85.0 if (is_marksman and ctx["total_lifesteal"] == 0 and playstyle == "balanced") else 55.0
        return sc, ("Covers lifesteal sustain when defensive items are prioritized over Bloodthirster." if sc >= 84 else None)
    if rune_key == "CutDown":
        sc = 92.0 if target_profile in ("tank", "bruiser") else 62.0
        return sc, ("Synergizes directly with percentage armor/magic pen against high-HP targets." if sc >= 85 else None)
    if rune_key == "CoupDeGrace":
        sc = 88.0 if (target_profile == "squishy" or playstyle == "burst") else 66.0
        return sc, ("Secures one-shot lethal thresholds against squishy targets." if sc >= 85 else None)
    if rune_key == "LastStand":
        sc = 88.0 if (is_melee_bruiser or playstyle == "balanced") else 55.0
        return sc, None

    # --- SORCERY ---
    if rune_key == "ManaflowBand":
        sc = 96.0 if ctx["needs_mana"] else (20.0 if not profile.get("uses_mana") else 72.0)
        return sc, ("Secures laning and late-game mana sustain when items lack flat mana." if sc >= 90 else None)
    if rune_key == "NullifyingOrb":  # Season 16: Axiom Arcanist
        sc = 88.0 if (not ctx["needs_mana"] and (is_ap or is_assassin)) else 62.0
        return sc, ("Axiom Arcanist boosts ultimate damage and refunds cooldown on takedowns." if sc >= 85 else None)
    if rune_key == "NimbusCloak":
        return (80.0 if ctx["role"] == "jungle" or not profile.get("uses_mana") else 55.0), None
    if rune_key == "Transcendence":
        sc = 90.0 if (ctx["total_ah"] >= 20 or is_ap or playstyle != "burst") else 72.0
        return sc, ("Pairs with item Ability Haste for faster mid-fight spell resets." if sc >= 85 else None)
    if rune_key == "AbsoluteFocus":
        sc = 86.0 if (playstyle == "burst" and not is_melee_bruiser) else 60.0
        return sc, None
    if rune_key == "Celerity":
        return (72.0 if ctx["role"] == "jungle" else 52.0), None
    if rune_key == "GatheringStorm":
        sc = 90.0 if (not ctx["is_swiftplay"] and (playstyle != "burst" or ctx["legendary_slots"] == 6)) else 65.0
        return sc, ("Grants scaling AP/AD that multiplies alongside Rabadon or Critical Strike in 6/7-item games." if sc >= 85 else None)
    if rune_key == "Scorch":
        sc = 84.0 if (ctx["is_swiftplay"] or playstyle == "burst") else 62.0
        return sc, None
    if rune_key == "Waterwalking":
        return (86.0 if ctx["role"] == "jungle" else 40.0), None

    # --- RESOLVE ---
    if rune_key == "Demolish":
        return (86.0 if ctx["role"] == "top" else 55.0), None
    if rune_key == "FontOfLife":
        return (84.0 if (ctx["role"] == "support" or ctx["is_aram"]) else 52.0), None
    if rune_key == "ShieldBash":
        return (78.0 if profile.get("is_tank") else 58.0), None
    if rune_key == "Conditioning":
        sc = 90.0 if (ctx["total_resists"] >= 60 or profile.get("is_tank")) else 62.0
        return sc, ("Amplifies item Armor and Magic Resist by a percentage to maximize durability." if sc >= 85 else None)
    if rune_key == "BonePlating":
        return (82.0 if target_profile == "squishy" and not ctx["is_aram"] else 62.0), None
    if rune_key == "SecondWind":
        return (85.0 if ctx["is_aram"] else 68.0), None
    if rune_key == "Overgrowth":
        sc = 90.0 if (ctx["total_hp"] >= 400 or profile.get("is_tank") or playstyle == "balanced") else 72.0
        return sc, ("Scales maximum health higher alongside HP-heavy items." if sc >= 85 else None)
    if rune_key == "Revitalize":
        return (82.0 if ctx["role"] == "support" else 58.0), None
    if rune_key == "Unflinching":
        return 66.0, None

    # --- INSPIRATION ---
    if rune_key == "CashBack":
        sc = 92.0 if (ctx["legendary_slots"] == 6 or ctx["total_gold"] >= 16500) else 68.0
        return sc, ("Refunds gold on every completed legendary in expensive 6/7-item builds." if sc >= 88 else None)
    if rune_key == "MagicalFootwear":
        sc = 84.0 if ctx["role"] in ("jungle", "mid", "adc") else 70.0
        return sc, ("Saves 300g on boots to accelerate your first core item completion." if sc >= 82 else None)
    if rune_key == "HextechFlashtraption":
        return (76.0 if ctx["role"] == "support" else 42.0), None
    if rune_key == "BiscuitDelivery":
        sc = 86.0 if (ctx["needs_mana"] or not ctx["is_aram"]) else 60.0
        return sc, None
    if rune_key == "PerfectTiming":  # Season 16: Triple Tonic
        return (82.0 if playstyle == "burst" or ctx["is_swiftplay"] else 65.0), None
    if rune_key == "TimeWarpTonic":
        return 52.0, None
    if rune_key == "CosmicInsight":
        sc = 88.0 if (ctx["role"] in ("jungle", "support", "mid") or is_ap) else 74.0
        return sc, ("Lowers Summoner Spell and active item cooldowns (Zhonya / Flash)." if sc >= 85 else None)
    if rune_key == "JackOfAllTrades":
        sc = 90.0 if ctx["distinct_stats_count"] >= 6 else 52.0
        return sc, ("Unlocks bonus Ability Haste and Adaptive Force from diverse item stats." if sc >= 88 else None)
    if rune_key == "ApproachVelocity":
        return (78.0 if is_melee_bruiser else 54.0), None

    return 50.0, None


class FullRunePageEngine:
    """
    Constructs a complete League of Legends rune page (1 Keystone + 3 Primary + 2 Secondary + 3 Stat Shards)
    tightly synchronized with the selected item build, champion profile, role, and map rules.
    """

    @staticmethod
    def _pick_secondary_tree(
        primary_tree: str,
        ctx: Dict[str, Any],
        profile: Dict[str, Any],
        playstyle: str,
    ) -> str:
        # 1. If the item build lacks mana (or in ARAM), prioritize a mana-sustaining secondary tree
        if ctx["needs_mana"]:
            if primary_tree != "Sorcery" and profile.get("is_ap_user"):
                return "Sorcery"
            if primary_tree != "Precision":
                return "Precision"
            if primary_tree != "Sorcery":
                return "Sorcery"

        # 2. Tank / Balanced / Survivability -> Resolve
        if (profile.get("is_tank") or playstyle == "balanced") and primary_tree != "Resolve":
            return "Resolve"

        # 3. Expensive 7-slot ADC builds -> Inspiration (Cash Back / Footwear) or Sorcery (Gathering Storm)
        if profile.get("is_marksman") or ctx["legendary_slots"] == 6:
            return "Inspiration" if primary_tree != "Inspiration" else "Sorcery"

        # 4. AP Mages -> Sorcery or Inspiration
        if profile.get("is_ap_user"):
            if primary_tree != "Sorcery":
                return "Sorcery"
            return "Inspiration" if playstyle != "burst" else "Domination"

        # 5. AD Fighters / Assassins
        if primary_tree != "Precision":
            return "Precision"
        return "Resolve" if playstyle == "balanced" else "Domination"

    @staticmethod
    def _pick_stat_shards(
        ctx: Dict[str, Any],
        profile: Dict[str, Any],
        playstyle: str,
        target_profile: str,
    ) -> List[Dict[str, str]]:
        # Row 1: Offense
        if profile.get("is_marksman") or (playstyle == "dps" and not profile.get("is_ap_user")):
            row1 = {"slot": "Offense", "key": "attack_speed", "label": "+10% Attack Speed"}
        elif ctx["total_ah"] < 25 and profile.get("is_ap_user") and playstyle == "balanced":
            row1 = {"slot": "Offense", "key": "ability_haste", "label": "+8 Ability Haste"}
        else:
            row1 = {"slot": "Offense", "key": "adaptive_force", "label": "+9 Adaptive Force"}

        # Row 2: Flex
        if profile.get("is_tank"):
            row2 = {"slot": "Flex", "key": "scaling_hp", "label": "+10–180 Scaling HP"}
        elif ctx["role"] == "jungle" and playstyle == "balanced":
            row2 = {"slot": "Flex", "key": "move_speed", "label": "+2% Move Speed"}
        else:
            row2 = {"slot": "Flex", "key": "adaptive_force", "label": "+9 Adaptive Force"}

        # Row 3: Defense
        if ctx["is_swiftplay"] or (playstyle == "burst" and target_profile == "squishy"):
            row3 = {"slot": "Defense", "key": "flat_hp", "label": "+65 Health"}
        elif profile.get("is_tank") and target_profile != "squishy":
            row3 = {"slot": "Defense", "key": "tenacity", "label": "+10% Tenacity & Slow Resist"}
        else:
            row3 = {"slot": "Defense", "key": "scaling_hp", "label": "+10–180 Scaling HP"}

        return [row1, row2, row3]

    @classmethod
    def build_full_rune_page(
        cls,
        keystone_key: str,
        items: List[Dict[str, Any]],
        profile: Dict[str, Any],
        playstyle: str = "burst",
        target_profile: str = "squishy",
        role: str = "mid",
        game_map: str = "sr",
        db_runes: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Builds a full rune page for a given keystone and item build:
        - Primary Tree (1 Keystone + 3 Minor Runes, one per slot)
        - Secondary Tree (2 Minor Runes from distinct slots)
        - 3 Stat Shards (Offense, Flex, Defense)
        - Item-Rune Synergy notes and aggregated stat bonuses
        """
        rune_index = _index_runes(db_runes)
        ks_entry = rune_index.get(keystone_key) or next(
            (r for r in DEFAULT_SEASON16_RUNES if r["key"] == keystone_key),
            DEFAULT_SEASON16_RUNES[0],
        )
        primary_tree = ks_entry["tree_key"]
        primary_tree_name = ks_entry["tree_name"]

        game_rules = resolve_effective_rules(role=role, game_map=game_map)
        ctx = _build_item_context(items, profile, game_rules)

        # Group runes by tree key and slot index
        by_tree_slot: Dict[str, Dict[int, List[Dict[str, Any]]]] = {}
        for r in rune_index.values():
            tk = r["tree_key"]
            sl = int(r["slot_index"])
            by_tree_slot.setdefault(tk, {}).setdefault(sl, []).append(r)

        synergy_notes: List[str] = []

        # 1. Primary Tree: highest-synergy minor rune in slots 1, 2, 3
        primary_minors: List[Dict[str, Any]] = []
        for slot_idx in (1, 2, 3):
            candidates = by_tree_slot.get(primary_tree, {}).get(slot_idx, [])
            if not candidates:
                continue
            scored = []
            for cand in candidates:
                sc, note = _score_minor_rune(cand["key"], ctx, profile, playstyle, target_profile)
                scored.append((sc, cand, note))
            scored.sort(key=lambda x: x[0], reverse=True)
            _, best_r, best_note = scored[0]
            primary_minors.append(
                {
                    "rune_id": best_r["rune_id"],
                    "key": best_r["key"],
                    "name": best_r["name"],
                    "slot_index": slot_idx,
                }
            )
            if best_note and len(synergy_notes) < 3:
                synergy_notes.append(f"{best_r['name']}: {best_note}")

        # 2. Secondary Tree: pick best tree != primary and best 2 distinct slots
        secondary_tree = cls._pick_secondary_tree(primary_tree, ctx, profile, playstyle)
        sec_slots_map = by_tree_slot.get(secondary_tree, {})
        sec_tree_name = next(
            (r["tree_name"] for lst in sec_slots_map.values() for r in lst),
            secondary_tree,
        )

        best_per_sec_slot: List[Tuple[float, int, Dict[str, Any], Optional[str]]] = []
        for slot_idx in (1, 2, 3):
            cands = sec_slots_map.get(slot_idx, [])
            if not cands:
                continue
            slot_scored = []
            for cand in cands:
                sc, note = _score_minor_rune(cand["key"], ctx, profile, playstyle, target_profile)
                slot_scored.append((sc, cand, note))
            slot_scored.sort(key=lambda x: x[0], reverse=True)
            b_sc, b_r, b_note = slot_scored[0]
            best_per_sec_slot.append((b_sc, slot_idx, b_r, b_note))

        best_per_sec_slot.sort(key=lambda x: x[0], reverse=True)
        chosen_sec = sorted(best_per_sec_slot[:2], key=lambda x: x[1])
        secondary_runes: List[Dict[str, Any]] = []
        for _, s_idx, r_obj, note in chosen_sec:
            secondary_runes.append(
                {
                    "rune_id": r_obj["rune_id"],
                    "key": r_obj["key"],
                    "name": r_obj["name"],
                    "slot_index": s_idx,
                }
            )
            if note and len(synergy_notes) < 4:
                synergy_notes.append(f"{r_obj['name']}: {note}")

        # 3. Stat Shards
        stat_shards = cls._pick_stat_shards(ctx, profile, playstyle, target_profile)

        # 4. Mid/late average stat bonuses propagated into CombatSimulator
        stat_bonuses = cls.compute_stat_bonuses(primary_minors + secondary_runes, stat_shards, profile)

        return {
            "primary_tree": {
                "key": primary_tree,
                "name": primary_tree_name,
                "keystone": {
                    "rune_id": ks_entry["rune_id"],
                    "key": ks_entry["key"],
                    "name": ks_entry["name"],
                },
                "runes": primary_minors,
            },
            "secondary_tree": {
                "key": secondary_tree,
                "name": sec_tree_name,
                "runes": secondary_runes,
            },
            "stat_shards": stat_shards,
            "synergy_notes": synergy_notes,
            "stat_bonuses": stat_bonuses,
        }

    @staticmethod
    def compute_stat_bonuses(
        minor_runes: List[Dict[str, Any]],
        stat_shards: List[Dict[str, str]],
        profile: Dict[str, Any],
    ) -> Dict[str, float]:
        """Summarizes mid/late game stat contributions from minor runes and 3 stat shards."""
        is_ap = bool(profile.get("is_ap_user") and not profile.get("is_ad_user"))
        bonuses: Dict[str, float] = {
            "ap": 0.0,
            "ad": 0.0,
            "hp": 0.0,
            "attack_speed": 0.0,
            "ability_haste": 0.0,
            "lifesteal": 0.0,
            "armor": 0.0,
            "mr": 0.0,
        }

        keys = {r["key"] for r in minor_runes}
        if "LegendAlacrity" in keys:
            bonuses["attack_speed"] += 0.15
        if "LegendHaste" in keys:
            bonuses["ability_haste"] += 15.0
        if "LegendBloodline" in keys:
            bonuses["lifesteal"] += 0.0525
            bonuses["hp"] += 85.0
        if "Transcendence" in keys:
            bonuses["ability_haste"] += 10.0
        if "AbsoluteFocus" in keys:
            if is_ap:
                bonuses["ap"] += 20.0
            else:
                bonuses["ad"] += 12.0
        if "GatheringStorm" in keys:
            if is_ap:
                bonuses["ap"] += 24.0
            else:
                bonuses["ad"] += 14.4
        if "Conditioning" in keys:
            bonuses["armor"] += 12.0
            bonuses["mr"] += 12.0
        if "Overgrowth" in keys:
            bonuses["hp"] += 160.0
        if "JackOfAllTrades" in keys:
            bonuses["ability_haste"] += 10.0
            if is_ap:
                bonuses["ap"] += 15.0
            else:
                bonuses["ad"] += 9.0

        for shard in stat_shards:
            sk = shard["key"]
            if sk == "attack_speed":
                bonuses["attack_speed"] += 0.10
            elif sk == "ability_haste":
                bonuses["ability_haste"] += 8.0
            elif sk == "adaptive_force":
                if is_ap:
                    bonuses["ap"] += 9.0
                else:
                    bonuses["ad"] += 5.4
            elif sk == "flat_hp":
                bonuses["hp"] += 65.0
            elif sk == "scaling_hp":
                bonuses["hp"] += 120.0

        return {k: round(v, 4) for k, v in bonuses.items() if v > 0.0}
