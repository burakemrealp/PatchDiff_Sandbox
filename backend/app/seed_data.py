import httpx
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import SessionLocal, engine, Base
from app.models.entities import Champion, Item

# Verified champion seed definitions representing the 4 core combat archetypes
CHAMPION_SEED_DATA = {
    "Ahri": {
        "name": "Ahri",
        "title": "the Nine-Tailed Fox",
        "base_stats": {
            "base_hp": 590.0,
            "hp_growth": 104.0,
            "base_ad": 53.0,
            "ad_growth": 3.0,
            "base_armor": 21.0,
            "armor_growth": 4.7,
            "base_mr": 30.0,
            "mr_growth": 1.3,
            "base_attack_speed": 0.668,
            "attack_speed_growth": 2.2,
            "move_speed": 330.0,
        },
        "abilities": {
            "Q": {
                "name": "Orb of Deception (Outbound + Return)",
                "damage_type": "magic",
                "base_damage": [80.0, 130.0, 180.0, 230.0, 280.0],
                "cooldown": [7.0, 7.0, 7.0, 7.0, 7.0],
                "scaling": {"ap": 0.90},
            },
            "W": {
                "name": "Fox-Fire (Single Target Total)",
                "damage_type": "magic",
                "base_damage": [72.0, 112.0, 152.0, 192.0, 232.0],
                "cooldown": [9.0, 8.0, 7.0, 6.0, 5.0],
                "scaling": {"ap": 0.48},
            },
            "E": {
                "name": "Charm",
                "damage_type": "magic",
                "base_damage": [80.0, 120.0, 160.0, 200.0, 240.0],
                "cooldown": [12.0, 12.0, 12.0, 12.0, 12.0],
                "scaling": {"ap": 0.75},
            },
            "R": {
                "name": "Spirit Rush (3 Dashes Total)",
                "damage_type": "magic",
                "base_damage": [180.0, 270.0, 360.0],
                "cooldown": [130.0, 105.0, 80.0],
                "scaling": {"ap": 1.05},
            },
        },
    },
    "Zed": {
        "name": "Zed",
        "title": "the Master of Shadows",
        "base_stats": {
            "base_hp": 654.0,
            "hp_growth": 99.0,
            "base_ad": 63.0,
            "ad_growth": 3.4,
            "base_armor": 32.0,
            "armor_growth": 4.7,
            "base_mr": 29.0,
            "mr_growth": 2.05,
            "base_attack_speed": 0.651,
            "attack_speed_growth": 3.3,
            "move_speed": 345.0,
        },
        "abilities": {
            "Q": {
                "name": "Razor Shuriken",
                "damage_type": "physical",
                "base_damage": [80.0, 115.0, 150.0, 185.0, 220.0],
                "cooldown": [6.0, 6.0, 6.0, 6.0, 6.0],
                "scaling": {"bonus_ad": 1.10},
            },
            "W": {
                "name": "Living Shadow",
                "damage_type": "physical",
                "base_damage": [0.0, 0.0, 0.0, 0.0, 0.0],
                "cooldown": [20.0, 18.5, 17.0, 15.5, 14.0],
                "scaling": {},
            },
            "E": {
                "name": "Shadow Slash",
                "damage_type": "physical",
                "base_damage": [65.0, 90.0, 115.0, 140.0, 165.0],
                "cooldown": [5.0, 4.5, 4.0, 3.5, 3.0],
                "scaling": {"bonus_ad": 0.65},
            },
            "R": {
                "name": "Death Mark (Base Detonation)",
                "damage_type": "physical",
                "base_damage": [65.0, 65.0, 65.0],
                "cooldown": [120.0, 100.0, 80.0],
                "scaling": {"total_ad": 1.00},
            },
        },
    },
    "Jinx": {
        "name": "Jinx",
        "title": "the Loose Cannon",
        "base_stats": {
            "base_hp": 630.0,
            "hp_growth": 105.0,
            "base_ad": 59.0,
            "ad_growth": 3.15,
            "base_armor": 26.0,
            "armor_growth": 4.7,
            "base_mr": 30.0,
            "mr_growth": 1.3,
            "base_attack_speed": 0.625,
            "attack_speed_growth": 1.4,
            "move_speed": 325.0,
        },
        "abilities": {
            "Q": {
                "name": "Switcheroo! (Fishbones Rocket Bonus)",
                "damage_type": "physical",
                "base_damage": [0.0, 0.0, 0.0, 0.0, 0.0],
                "cooldown": [0.9, 0.9, 0.9, 0.9, 0.9],
                "scaling": {"total_ad": 0.10},
            },
            "W": {
                "name": "Zap!",
                "damage_type": "physical",
                "base_damage": [10.0, 60.0, 110.0, 160.0, 210.0],
                "cooldown": [8.0, 7.0, 6.0, 5.0, 4.0],
                "scaling": {"total_ad": 1.60},
            },
            "E": {
                "name": "Flame Chompers!",
                "damage_type": "magic",
                "base_damage": [70.0, 120.0, 170.0, 220.0, 270.0],
                "cooldown": [24.0, 20.5, 17.0, 13.5, 10.0],
                "scaling": {"ap": 1.00},
            },
            "R": {
                "name": "Super Mega Death Rocket!",
                "damage_type": "physical",
                "base_damage": [300.0, 450.0, 600.0],
                "cooldown": [70.0, 60.0, 50.0],
                "scaling": {"bonus_ad": 1.55},
            },
        },
    },
    "Ornn": {
        "name": "Ornn",
        "title": "The Fire below the Mountain",
        "base_stats": {
            "base_hp": 660.0,
            "hp_growth": 109.0,
            "base_ad": 69.0,
            "ad_growth": 3.5,
            "base_armor": 33.0,
            "armor_growth": 5.2,
            "base_mr": 32.0,
            "mr_growth": 2.05,
            "base_attack_speed": 0.625,
            "attack_speed_growth": 2.0,
            "move_speed": 335.0,
        },
        "abilities": {
            "Q": {
                "name": "Volcanic Rupture",
                "damage_type": "physical",
                "base_damage": [20.0, 45.0, 70.0, 95.0, 120.0],
                "cooldown": [9.0, 8.5, 8.0, 7.5, 7.0],
                "scaling": {"total_ad": 1.10},
            },
            "W": {
                "name": "Bellows Breath",
                "damage_type": "magic",
                "base_damage": [125.0, 150.0, 175.0, 200.0, 225.0],
                "cooldown": [12.0, 11.5, 11.0, 10.5, 10.0],
                "scaling": {"target_max_hp": 0.14},
            },
            "E": {
                "name": "Searing Charge",
                "damage_type": "physical",
                "base_damage": [80.0, 125.0, 170.0, 215.0, 260.0],
                "cooldown": [16.0, 15.0, 14.0, 13.0, 12.0],
                "scaling": {"bonus_hp": 0.10},
            },
            "R": {
                "name": "Call of the Forge God",
                "damage_type": "magic",
                "base_damage": [250.0, 350.0, 450.0],
                "cooldown": [140.0, 120.0, 100.0],
                "scaling": {"ap": 0.40},
            },
        },
    },
}

# Six core reference items used for fallback simulation seeding
ITEM_SEED_DATA = [
    {
        "item_id": "3089",
        "name": "Rabadon's Deathcap",
        "gold_total": 3600,
        "stats": {"ap": 130.0, "ap_multiplier": 0.30},
    },
    {
        "item_id": "3135",
        "name": "Void Staff",
        "gold_total": 3000,
        "stats": {"ap": 95.0, "magic_pen_percent": 0.40},
    },
    {
        "item_id": "4645",
        "name": "Shadowflame",
        "gold_total": 3200,
        "stats": {"ap": 110.0, "magic_pen_flat": 15.0},
    },
    {
        "item_id": "3142",
        "name": "Youmuu's Ghostblade",
        "gold_total": 2800,
        "stats": {"ad": 60.0, "lethality": 18.0},
    },
    {
        "item_id": "3036",
        "name": "Lord Dominik's Regards",
        "gold_total": 3000,
        "stats": {"ad": 35.0, "armor_pen_percent": 0.35, "crit_chance": 0.25},
    },
    {
        "item_id": "3031",
        "name": "Infinity Edge",
        "gold_total": 3600,
        "stats": {"ad": 70.0, "crit_chance": 0.25, "crit_damage_bonus": 0.40},
    },
]


def sync_ddragon_stats(champ_key: str, fallback_stats: dict) -> dict:
    """Fetches live base stats from Riot Data Dragon CDN, falling back to verified local stats if offline."""
    url = f"https://ddragon.leagueoflegends.com/cdn/{settings.DDRAGON_VERSION}/data/{settings.DDRAGON_LANG}/champion/{champ_key}.json"
    try:
        with httpx.Client(timeout=5.0) as client:
            resp = client.get(url)
            if resp.status_code == 200:
                raw_stats = resp.json()["data"][champ_key]["stats"]
                return {
                    "base_hp": float(raw_stats.get("hp", fallback_stats["base_hp"])),
                    "hp_growth": float(raw_stats.get("hpperlevel", fallback_stats["hp_growth"])),
                    "base_ad": float(raw_stats.get("attackdamage", fallback_stats["base_ad"])),
                    "ad_growth": float(raw_stats.get("attackdamageperlevel", fallback_stats["ad_growth"])),
                    "base_armor": float(raw_stats.get("armor", fallback_stats["base_armor"])),
                    "armor_growth": float(raw_stats.get("armorperlevel", fallback_stats["armor_growth"])),
                    "base_mr": float(raw_stats.get("spellblock", fallback_stats["base_mr"])),
                    "mr_growth": float(raw_stats.get("spellblockperlevel", fallback_stats["mr_growth"])),
                    "base_attack_speed": float(raw_stats.get("attackspeed", fallback_stats["base_attack_speed"])),
                    "attack_speed_growth": float(raw_stats.get("attackspeedperlevel", fallback_stats["attack_speed_growth"])),
                    "move_speed": float(raw_stats.get("movespeed", fallback_stats["move_speed"])),
                }
    except Exception as exc:
        print(f"   ⚠️ Data Dragon CDN warning ({champ_key}): {exc}. Using verified local fallback data.")
    return fallback_stats


def seed_database() -> None:
    print("🌱 Starting static database seeding...\n")
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()

    try:
        # 1. Insert or Update Champions
        for key, data in CHAMPION_SEED_DATA.items():
            live_stats = sync_ddragon_stats(key, data["base_stats"])
            existing = db.query(Champion).filter(Champion.key == key).first()

            if existing:
                existing.base_stats = live_stats
                existing.abilities = data["abilities"]
                existing.patch_version = settings.DDRAGON_VERSION
                print(f"🔄 Updated champion: {key} ({data['title']}) - Base HP: {live_stats['base_hp']}")
            else:
                new_champ = Champion(
                    key=key,
                    name=data["name"],
                    title=data["title"],
                    patch_version=settings.DDRAGON_VERSION,
                    base_stats=live_stats,
                    abilities=data["abilities"],
                )
                db.add(new_champ)
                print(f"✅ Added champion: {key} ({data['title']}) - Base HP: {live_stats['base_hp']}")

        # 2. Insert or Update Items
        print("")
        for item_data in ITEM_SEED_DATA:
            existing_item = db.query(Item).filter(Item.item_id == item_data["item_id"]).first()
            if existing_item:
                existing_item.name = item_data["name"]
                existing_item.gold_total = item_data["gold_total"]
                existing_item.stats = item_data["stats"]
                print(f"🔄 Updated item: [{item_data['item_id']}] {item_data['name']} ({item_data['gold_total']}g)")
            else:
                new_item = Item(
                    item_id=item_data["item_id"],
                    name=item_data["name"],
                    gold_total=item_data["gold_total"],
                    stats=item_data["stats"],
                )
                db.add(new_item)
                print(f"✅ Added item: [{item_data['item_id']}] {item_data['name']} ({item_data['gold_total']}g)")

        db.commit()

        champ_count = db.query(Champion).count()
        item_count = db.query(Item).count()
        print(f"\n🎉 Seeding complete! {champ_count} champions and {item_count} items are ready in the database.")

    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
