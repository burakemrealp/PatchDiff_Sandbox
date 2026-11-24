from app.engine.build_optimizer import (
    BuildOptimizerEngine,
    filter_candidate_items,
    infer_champion_profile,
)
from app.seed_data import CHAMPION_SEED_DATA

SAMPLE_ITEMS = [
    {"item_id": "3089", "name": "Rabadon'un Şapkası", "gold_total": 3500, "tags": ["SpellDamage"], "unique_groups": [], "stats": {"ap": 130.0, "ap_multiplier": 0.30}},
    {"item_id": "3135", "name": "Hiçlik Değneği", "gold_total": 3000, "tags": ["SpellDamage", "MagicPenetration"], "unique_groups": ["MagicPenPercent"], "stats": {"ap": 95.0, "magic_pen_percent": 0.40}},
    {"item_id": "3137", "name": "Mezar Çiçeği (Cryptbloom)", "gold_total": 2850, "tags": ["SpellDamage", "MagicPenetration"], "unique_groups": ["MagicPenPercent"], "stats": {"ap": 75.0, "magic_pen_percent": 0.30, "ability_haste": 20.0}},
    {"item_id": "4645", "name": "Gölgealev", "gold_total": 3200, "tags": ["SpellDamage", "MagicPenetration"], "unique_groups": [], "stats": {"ap": 110.0, "magic_pen_flat": 15.0}},
    {"item_id": "6655", "name": "Luden'in Feryadı", "gold_total": 2750, "tags": ["SpellDamage", "Mana"], "unique_groups": [], "stats": {"ap": 100.0, "mana": 600.0, "ability_haste": 10.0}},
    {"item_id": "6653", "name": "Liandry'nin Eziyeti", "gold_total": 3000, "tags": ["SpellDamage", "Health"], "unique_groups": [], "stats": {"ap": 70.0, "hp": 300.0}},
    {"item_id": "3157", "name": "Zhonya'nın Kumsaati", "gold_total": 3250, "tags": ["SpellDamage", "Armor"], "unique_groups": [], "stats": {"ap": 105.0, "armor": 50.0}},
    {"item_id": "3100", "name": "Lich Boğan", "gold_total": 2900, "tags": ["SpellDamage"], "unique_groups": ["Spellblade"], "stats": {"ap": 100.0, "ability_haste": 10.0}},
    {"item_id": "3031", "name": "Ebedi Kılıç", "gold_total": 3500, "tags": ["Damage", "CriticalStrike"], "unique_groups": [], "stats": {"ad": 75.0, "crit_chance": 0.25, "crit_damage_bonus": 0.30}},
    {"item_id": "3036", "name": "Dominik Efendi", "gold_total": 3300, "tags": ["Damage", "ArmorPenetration"], "unique_groups": ["ArmorPen"], "stats": {"ad": 35.0, "crit_chance": 0.25, "armor_pen_percent": 0.35}},
    {"item_id": "3071", "name": "Kara Balta", "gold_total": 3000, "tags": ["Damage", "Health"], "unique_groups": ["ArmorPen"], "stats": {"ad": 45.0, "hp": 400.0, "ability_haste": 20.0}},
    {"item_id": "3142", "name": "Youmuu", "gold_total": 2800, "tags": ["Damage"], "unique_groups": [], "stats": {"ad": 55.0, "lethality": 18.0}},
    {"item_id": "6672", "name": "Kraken Katili", "gold_total": 3100, "tags": ["Damage", "AttackSpeed"], "unique_groups": [], "stats": {"ad": 45.0, "attack_speed": 0.40}},
    {"item_id": "3153", "name": "Mahvolmuş Kralın Kılıcı", "gold_total": 3200, "tags": ["Damage", "AttackSpeed"], "unique_groups": [], "stats": {"ad": 40.0, "attack_speed": 0.25}},
    {"item_id": "3053", "name": "Sterak'ın Güvencesi", "gold_total": 3200, "tags": ["Health", "Damage"], "unique_groups": ["Lifeline"], "stats": {"hp": 400.0, "ad": 40.0}},
    {"item_id": "3072", "name": "Kanasusamış", "gold_total": 3400, "tags": ["Damage", "LifeSteal"], "unique_groups": [], "stats": {"ad": 80.0, "lifesteal": 0.15}},
    {"item_id": "3094", "name": "Bombardıman Topu", "gold_total": 2650, "tags": ["AttackSpeed", "CriticalStrike"], "unique_groups": [], "stats": {"attack_speed": 0.35, "crit_chance": 0.25}},
    {"item_id": "3026", "name": "Koruyucu Melek", "gold_total": 3200, "tags": ["Damage", "Armor"], "unique_groups": [], "stats": {"ad": 55.0, "armor": 45.0}},
    {"item_id": "3020", "name": "Sihirbaz Pabuçları", "gold_total": 1100, "tags": ["Boots"], "unique_groups": ["Boots"], "stats": {"magic_pen_flat": 12.0}},
    {"item_id": "3006", "name": "Savaşçı Çizmeleri", "gold_total": 1100, "tags": ["Boots"], "unique_groups": ["Boots"], "stats": {"attack_speed": 0.25}},
]


def test_filter_candidate_items_blocks_nonsense_items_and_boots():
    ahri = CHAMPION_SEED_DATA["Ahri"]
    ahri_profile = infer_champion_profile(ahri["abilities"], tags=["Mage", "Assassin"], partype="Mana")
    ahri_items = filter_candidate_items(SAMPLE_ITEMS, ahri_profile)
    ahri_ids = {i["item_id"] for i in ahri_items}

    # Ahri should get AP items, NOT Infinity Edge, LDR, Youmuu, or Boots
    assert "3089" in ahri_ids
    assert "4645" in ahri_ids
    assert "3031" not in ahri_ids
    assert "3142" not in ahri_ids
    assert "3020" not in ahri_ids

    # Energy user Zed should NOT get high-Mana items or AP items
    zed = CHAMPION_SEED_DATA["Zed"]
    zed_profile = infer_champion_profile(zed["abilities"], tags=["Assassin"], partype="Energy")
    zed_items = filter_candidate_items(SAMPLE_ITEMS, zed_profile)
    zed_ids = {i["item_id"] for i in zed_items}
    assert "3142" in zed_ids
    assert "6655" not in zed_ids
    assert "3089" not in zed_ids


def test_optimizer_produces_full_6_item_mid_and_7_item_adc_builds_with_full_rune_pages():
    ahri = CHAMPION_SEED_DATA["Ahri"]
    result_mid = BuildOptimizerEngine.optimize_builds(
        champion_key="Ahri",
        base_stats=ahri["base_stats"],
        base_abilities=ahri["abilities"],
        candidate_items=SAMPLE_ITEMS,
        tags=["Mage", "Assassin"],
        partype="Mana",
        target_profile_key="squishy",
        role="mid",
        game_map="sr",
    )

    variations = result_mid["variations"]
    assert len(variations) == 3
    assert [v["playstyle"] for v in variations] == ["burst", "dps", "balanced"]

    for var in variations:
        # Mid: 5 Legendaries + 1 Tier-3 Boot = 6 items total!
        assert len(var["items"]) == 6
        item_ids = [i["item_id"] for i in var["items"]]
        assert len(set(item_ids)) == 6
        assert any(i["is_boot"] and i["slot_type"] == "tier3_boot" for i in var["items"])
        # Void Staff (3135) and Cryptbloom (3137) share MagicPenPercent unique group -> never together
        assert not ("3135" in item_ids and "3137" in item_ids)
        # Full rune page present (1+3 primary, 2 secondary, 3 stat shards)
        rp = var["rune_page"]
        assert len(rp["primary_tree"]["runes"]) == 3
        assert len(rp["secondary_tree"]["runes"]) == 2
        assert len(rp["stat_shards"]) == 3

    # ADC on Summoner's Rift: 6 Legendaries + 1 Role-Quest Boot = 7 items total!
    jinx = CHAMPION_SEED_DATA["Jinx"]
    result_adc = BuildOptimizerEngine.optimize_builds(
        champion_key="Jinx",
        base_stats=jinx["base_stats"],
        base_abilities=jinx["abilities"],
        candidate_items=SAMPLE_ITEMS,
        tags=["Marksman"],
        partype="Mana",
        target_profile_key="tank",
        role="adc",
        game_map="sr",
    )
    assert result_adc["game_context"]["separate_boot_slot"] is True
    for var in result_adc["variations"]:
        assert len(var["items"]) == 7
        assert any(i["is_boot"] and i["slot_type"] == "role_quest_boot" for i in var["items"])
