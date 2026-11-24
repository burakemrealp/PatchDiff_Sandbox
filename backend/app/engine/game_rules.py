from typing import Any, Dict, List, Literal

RoleKey = Literal["top", "jungle", "mid", "adc", "support"]
MapKey = Literal["sr", "aram", "swiftplay"]

ROLE_CONFIGS: Dict[str, Dict[str, Any]] = {
    "top": {
        "key": "top",
        "label": "Top Lane",
        "max_level": 20,
        "legendary_slots": 5,
        "separate_boot_slot": False,
        "total_item_slots": 6,
        "tier3_boots": False,
        "quest_reward": "Level 20 Cap + Bonus XP + Empowered Teleport (TP)",
    },
    "jungle": {
        "key": "jungle",
        "label": "Jungle",
        "max_level": 18,
        "legendary_slots": 5,
        "separate_boot_slot": False,
        "total_item_slots": 6,
        "tier3_boots": False,
        "quest_reward": "Primal Smite + Jungle/River Move Speed",
    },
    "mid": {
        "key": "mid",
        "label": "Mid Lane",
        "max_level": 18,
        "legendary_slots": 5,
        "separate_boot_slot": False,
        "total_item_slots": 6,
        "tier3_boots": True,
        "quest_reward": "Free Tier 3 Boots + Empowered Recall",
    },
    "adc": {
        "key": "adc",
        "label": "Bot Lane (ADC)",
        "max_level": 18,
        "legendary_slots": 6,
        "separate_boot_slot": True,
        "total_item_slots": 7,
        "tier3_boots": False,
        "quest_reward": "Dedicated Boot Role Slot (6 Legendaries + 1 Boot = 7 Items) + Bonus Gold",
    },
    "support": {
        "key": "support",
        "label": "Support",
        "max_level": 18,
        "legendary_slots": 5,
        "separate_boot_slot": False,
        "total_item_slots": 6,
        "tier3_boots": False,
        "quest_reward": "Dedicated Control Ward Slot (40g Discount)",
    },
}

MAP_CONFIGS: Dict[str, Dict[str, Any]] = {
    "sr": {
        "key": "sr",
        "label": "Summoner's Rift (5v5)",
        "role_quests_enabled": True,
        "start_level": 1,
        "mana_priority_weight": 1.0,
        "sustain_priority_weight": 1.0,
        "early_spike_weight": 1.0,
        "description": "Standard 5v5 Summoner's Rift; Season 16 Role Quests active.",
    },
    "aram": {
        "key": "aram",
        "label": "ARAM (Howling Abyss)",
        "role_quests_enabled": False,
        "start_level": 3,
        "mana_priority_weight": 1.8,
        "sustain_priority_weight": 1.6,
        "early_spike_weight": 1.1,
        "description": "Single-lane continuous teamfight mode; no base recall, Mana & Sustain critical.",
    },
    "swiftplay": {
        "key": "swiftplay",
        "label": "Swiftplay (Fast 5v5)",
        "role_quests_enabled": True,
        "start_level": 3,
        "mana_priority_weight": 0.9,
        "sustain_priority_weight": 0.9,
        "early_spike_weight": 1.5,
        "description": "Level 3 and 1400g start; fast tempo focused on early power spikes.",
    },
}


def infer_default_role(tags: List[str] | None = None) -> str:
    """Infers a default Summoner's Rift lane role from champion class tags."""
    tags_set = set(tags or [])
    if "Marksman" in tags_set:
        return "adc"
    if "Support" in tags_set and "Mage" not in tags_set:
        return "support"
    if "Mage" in tags_set or "Assassin" in tags_set:
        return "mid"
    if "Tank" in tags_set or "Fighter" in tags_set:
        return "top"
    return "mid"


def resolve_effective_rules(role: str = "mid", game_map: str = "sr") -> Dict[str, Any]:
    """
    Resolves active Season 16 game rules for the selected Role and Map/Mode combination.
    Example: Summoner's Rift Role Quests are disabled in ARAM (ADC reverts to 6 slots, Top to Level 18).
    """
    r_cfg = ROLE_CONFIGS.get(role.lower(), ROLE_CONFIGS["mid"])
    m_cfg = MAP_CONFIGS.get(game_map.lower(), MAP_CONFIGS["sr"])

    quests_on = bool(m_cfg["role_quests_enabled"])

    return {
        "role": r_cfg["key"],
        "role_label": r_cfg["label"] if quests_on else "Single Lane (ARAM)",
        "game_map": m_cfg["key"],
        "map_label": m_cfg["label"],
        "role_quests_enabled": quests_on,
        "quest_reward": (
            r_cfg["quest_reward"]
            if quests_on
            else "ARAM is a single-lane map — Role Quests disabled (6 Items, Max Level 18). Mana & Sustain prioritized."
        ),
        "max_level": r_cfg["max_level"] if quests_on else 18,
        "legendary_slots": r_cfg["legendary_slots"] if quests_on else 5,
        "separate_boot_slot": r_cfg["separate_boot_slot"] if quests_on else False,
        "total_item_slots": r_cfg["total_item_slots"] if quests_on else 6,
        "tier3_boots": r_cfg["tier3_boots"] if quests_on else False,
        "start_level": m_cfg["start_level"],
        "mana_priority_weight": m_cfg["mana_priority_weight"],
        "sustain_priority_weight": m_cfg["sustain_priority_weight"],
        "early_spike_weight": m_cfg["early_spike_weight"],
    }
