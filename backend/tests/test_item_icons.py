from app.core.versioning import build_item_icon_url
from app.engine.build_optimizer import order_build_items, select_optimal_boot


def test_build_item_icon_url_uses_official_ddragon_cdn():
    assert (
        build_item_icon_url("16.23.1", "3089", "3089.png")
        == "https://ddragon.leagueoflegends.com/cdn/16.23.1/img/item/3089.png"
    )
    assert (
        build_item_icon_url("16.23.1", "3175")
        == "https://ddragon.leagueoflegends.com/cdn/16.23.1/img/item/3175.png"
    )
    assert build_item_icon_url(None, "3089") is None


def test_optimizer_preserves_item_icon_urls_on_boots_and_legendaries():
    boot_url = "https://ddragon.leagueoflegends.com/cdn/16.23.1/img/item/3175.png"
    rabadon_url = "https://ddragon.leagueoflegends.com/cdn/16.23.1/img/item/3089.png"
    luden_url = "https://ddragon.leagueoflegends.com/cdn/16.23.1/img/item/6655.png"

    all_items = [
        {
            "item_id": "3175",
            "name": "Büyülü Çizmeler",
            "gold_total": 1100,
            "stats": {"magic_pen_flat": 19},
            "tags": ["Boots"],
            "unique_groups": ["Boots"],
            "icon_url": boot_url,
        },
        {
            "item_id": "3089",
            "name": "Rabadon'un Şapkası",
            "gold_total": 3600,
            "stats": {"ap": 130, "ap_multiplier": 0.30},
            "tags": ["SpellDamage"],
            "unique_groups": [],
            "icon_url": rabadon_url,
        },
        {
            "item_id": "6655",
            "name": "Luden'in Yoldaşı",
            "gold_total": 2850,
            "stats": {"ap": 100, "mana": 600, "ability_haste": 10},
            "tags": ["SpellDamage", "Mana"],
            "unique_groups": [],
            "icon_url": luden_url,
        },
    ]
    profile = {
        "is_tank": False,
        "is_marksman": False,
        "is_ap_user": True,
        "is_ad_user": False,
        "uses_mana": True,
    }
    rules = {"role": "mid", "tier3_boots": True, "separate_boot_slot": False}

    boot = select_optimal_boot(all_items, profile, "burst", "squishy", rules)
    assert boot is not None
    assert boot["icon_url"] == boot_url

    ordered = order_build_items(all_items[1:], boot, profile, rules)
    assert len(ordered) == 3
    assert [i["icon_url"] for i in ordered] == [luden_url, boot_url, rabadon_url]
