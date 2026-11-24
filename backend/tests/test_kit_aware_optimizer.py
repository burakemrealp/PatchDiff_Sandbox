from app.engine.build_optimizer import (
    analyze_patch_diff_signals,
    filter_candidate_items,
    infer_champion_profile,
)


def test_analyze_patch_diff_signals_detects_nerfs_and_buffs_generically():
    # Syndra-like CD + Mana nerf
    syndra_like_diff = {
        "ability_deltas": [
            {
                "slot": "E",
                "old_cooldown": [15, 15, 15, 15, 15],
                "new_cooldown": [17, 16.5, 16, 15.5, 15],
                "old_mana_cost": [50, 50, 50, 50, 50],
                "new_mana_cost": [60, 60, 60, 60, 60],
                "scaling_changes": [],
            }
        ],
        "stat_deltas": [],
        "mechanic_deltas": [],
    }
    sig_cd = analyze_patch_diff_signals(syndra_like_diff)
    assert sig_cd["cd_or_mana_nerfed"] is True
    assert len(sig_cd["adaptation_notes"]) >= 1

    # Azir-like Attack Range + On-Hit buff
    azir_like_diff = {
        "stat_deltas": [{"stat_name": "attack_range", "direction": "BUFF"}],
        "ability_deltas": [],
        "mechanic_deltas": [
            {"spell_name": "AzirW", "field_name": "OnHitMultiplier", "direction": "BUFF"}
        ],
    }
    sig_onhit = analyze_patch_diff_signals(azir_like_diff)
    assert sig_onhit["range_buffed"] is True
    assert sig_onhit["onhit_buffed"] is True


def test_ranged_control_mage_blocks_lich_bane_and_nashors_while_onhit_and_melee_keep_them():
    pool = [
        {
            "item_id": "6655",
            "name": "Luden'in Feryadı",
            "gold_total": 2850,
            "stats": {"ap": 100, "mana": 600, "ability_haste": 10},
            "unique_groups": [],
        },
        {
            "item_id": "3100",
            "name": "Lich Boğan",
            "gold_total": 3100,
            "stats": {"ap": 100, "ability_haste": 10},
            "unique_groups": ["Spellblade"],
        },
        {
            "item_id": "3115",
            "name": "Nashor'un Dişi",
            "gold_total": 3000,
            "stats": {"ap": 80, "attack_speed": 0.5, "ability_haste": 15},
            "unique_groups": [],
        },
        {
            "item_id": "4645",
            "name": "Gölgealev",
            "gold_total": 3200,
            "stats": {"ap": 110, "magic_pen_flat": 15},
            "unique_groups": [],
        },
    ]

    mage_abilities = {
        "Q": {"cooldown": [7, 7, 7, 7, 7], "mana_cost": [40, 45, 50, 55, 60], "scaling": {"ap": 0.7}},
        "W": {"cooldown": [10, 9.5, 9, 8.5, 8], "mana_cost": [60, 65, 70, 75, 80], "scaling": {"ap": 0.65}},
        "E": {"cooldown": [15, 15, 15, 15, 15], "mana_cost": [50, 50, 50, 50, 50], "scaling": {"ap": 0.45}},
        "R": {"cooldown": [120, 100, 80], "mana_cost": [100, 100, 100], "scaling": {"ap": 0.8}},
    }

    # 1. Long-range control mage -> Lich Bane and Nashor's Tooth must be filtered out
    ctrl_profile = infer_champion_profile(
        mage_abilities,
        tags=["Mage"],
        partype="Mana",
        base_stats={"attack_range": 550.0},
    )
    assert ctrl_profile["is_ranged_control_mage"] is True
    ctrl_ids = {i["item_id"] for i in filter_candidate_items(pool, ctrl_profile)}
    assert "3100" not in ctrl_ids
    assert "3115" not in ctrl_ids
    assert {"6655", "4645"}.issubset(ctrl_ids)

    # 2. On-Hit Mage / Marksman (Azir archetype) -> Nashor's Tooth must stay eligible
    onhit_profile = infer_champion_profile(
        mage_abilities,
        tags=["Mage", "Marksman"],
        partype="Mana",
        base_stats={"attack_range": 550.0},
        patch_signals={"onhit_buffed": True},
    )
    assert onhit_profile["is_aa_onhit_mage"] is True
    onhit_ids = {i["item_id"] for i in filter_candidate_items(pool, onhit_profile)}
    assert "3115" in onhit_ids

    # 3. Melee AP Assassin/Fighter (Diana/Sylas archetype) -> Keep Lich Bane & Nashor's Tooth
    melee_ap_profile = infer_champion_profile(
        mage_abilities,
        tags=["Fighter", "Assassin"],
        partype="Mana",
        base_stats={"attack_range": 150.0},
    )
    assert melee_ap_profile["is_melee"] is True
    melee_ids = {i["item_id"] for i in filter_candidate_items(pool, melee_ap_profile)}
    assert "3100" in melee_ids
    assert "3115" in melee_ids


def test_spell_caster_adc_profile_blocks_zero_ad_zeal_items():
    ezreal_like_abilities = {
        "Q": {"cooldown": [5.5, 5.25, 5.0, 4.75, 4.5], "mana_cost": [28, 31, 34, 37, 40], "scaling": {"total_ad": 1.3, "ap": 0.15}},
        "W": {"cooldown": [8, 8, 8, 8, 8], "mana_cost": [50, 50, 50, 50, 50], "scaling": {"bonus_ad": 1.15, "ap": 1.0}},
        "E": {"cooldown": [20, 18, 16, 14, 12], "mana_cost": [70, 70, 70, 70, 70], "scaling": {"bonus_ad": 0.5, "ap": 0.75}},
        "R": {"cooldown": [120, 105, 90], "mana_cost": [100, 100, 100], "scaling": {"bonus_ad": 1.1, "ap": 1.2}},
    }
    profile = infer_champion_profile(
        ezreal_like_abilities,
        tags=["Marksman", "Mage"],
        partype="Mana",
        base_stats={"attack_range": 550.0},
    )
    assert profile["is_spell_caster_adc"] is True

    items = [
        {"item_id": "3078", "name": "Üçlü Kuvvet", "gold_total": 3333, "stats": {"ad": 36, "attack_speed": 0.3, "ability_haste": 15}, "unique_groups": ["Spellblade"]},
        {"item_id": "3004", "name": "Manaveren", "gold_total": 2900, "stats": {"ad": 35, "mana": 500, "ability_haste": 15}, "unique_groups": []},
        {"item_id": "3046", "name": "Hayalet Dansçı", "gold_total": 2650, "stats": {"attack_speed": 0.6, "crit_chance": 0.25}, "unique_groups": []},
    ]
    filtered_ids = {i["item_id"] for i in filter_candidate_items(items, profile)}
    assert "3078" in filtered_ids
    assert "3004" in filtered_ids
    assert "3046" not in filtered_ids
