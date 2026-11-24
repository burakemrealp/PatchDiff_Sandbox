from app.engine.build_optimizer import infer_champion_profile
from app.engine.full_rune_page_engine import FullRunePageEngine
from app.seed_data import CHAMPION_SEED_DATA


def test_full_rune_page_structure_is_complete_and_legal():
    ahri = CHAMPION_SEED_DATA["Ahri"]
    profile = infer_champion_profile(ahri["abilities"], tags=["Mage", "Assassin"], partype="Mana")
    no_mana_items = [
        {"item_id": "4645", "name": "Gölgealev", "gold_total": 3200, "stats": {"ap": 110.0, "magic_pen_flat": 15.0}},
        {"item_id": "3089", "name": "Rabadon'un Şapkası", "gold_total": 3500, "stats": {"ap": 130.0, "ap_multiplier": 0.30}},
    ]

    page = FullRunePageEngine.build_full_rune_page(
        keystone_key="Electrocute",
        items=no_mana_items,
        profile=profile,
        playstyle="burst",
        target_profile="squishy",
        role="mid",
        game_map="sr",
    )

    # Primary tree: 1 keystone + 3 distinct minor slots (1, 2, 3)
    assert page["primary_tree"]["key"] == "Domination"
    assert page["primary_tree"]["keystone"]["key"] == "Electrocute"
    assert [r["slot_index"] for r in page["primary_tree"]["runes"]] == [1, 2, 3]

    # Secondary tree: MUST be different from primary, 2 distinct slots
    assert page["secondary_tree"]["key"] != page["primary_tree"]["key"]
    assert len(page["secondary_tree"]["runes"]) == 2
    sec_slots = [r["slot_index"] for r in page["secondary_tree"]["runes"]]
    assert len(set(sec_slots)) == 2

    # 3 Stat Shards (Offense / Flex / Defense)
    assert [s["slot"] for s in page["stat_shards"]] == ["Offense", "Flex", "Defense"]

    # Item-Rune synergy: Zero-mana AP build on Mana Mage MUST pick Sorcery + ManaflowBand!
    assert page["secondary_tree"]["key"] == "Sorcery"
    sec_keys = {r["key"] for r in page["secondary_tree"]["runes"]}
    assert "ManaflowBand" in sec_keys
    assert len(page["synergy_notes"]) >= 1


def test_full_rune_page_adapts_to_adc_7_slot_and_tank_target():
    jinx = CHAMPION_SEED_DATA["Jinx"]
    profile = infer_champion_profile(jinx["abilities"], tags=["Marksman"], partype="Mana")
    expensive_adc_items = [
        {"item_id": "6672", "name": "Kraken", "gold_total": 3100, "stats": {"ad": 45.0, "attack_speed": 0.40}},
        {"item_id": "3031", "name": "Ebedi Kılıç", "gold_total": 3500, "stats": {"ad": 75.0, "crit_chance": 0.25}},
        {"item_id": "3036", "name": "Dominik Efendi", "gold_total": 3300, "stats": {"ad": 35.0, "armor_pen_percent": 0.35}},
        {"item_id": "3094", "name": "Bombardıman Topu", "gold_total": 2650, "stats": {"attack_speed": 0.35, "crit_chance": 0.25}},
        {"item_id": "3072", "name": "Kanasusamış", "gold_total": 3400, "stats": {"ad": 80.0, "lifesteal": 0.15}},
        {"item_id": "3026", "name": "Koruyucu Melek", "gold_total": 3200, "stats": {"ad": 55.0, "armor": 45.0}},
    ]

    page = FullRunePageEngine.build_full_rune_page(
        keystone_key="LethalTempo",
        items=expensive_adc_items,
        profile=profile,
        playstyle="dps",
        target_profile="tank",
        role="adc",
        game_map="sr",
    )

    prim_keys = {r["key"] for r in page["primary_tree"]["runes"]}
    assert "LegendAlacrity" in prim_keys
    assert "CutDown" in prim_keys
    # Expensive 6-legendary ADC build selects Inspiration + CashBack!
    assert page["secondary_tree"]["key"] == "Inspiration"
    assert "CashBack" in {r["key"] for r in page["secondary_tree"]["runes"]}
    assert page["stat_shards"][0]["key"] == "attack_speed"
