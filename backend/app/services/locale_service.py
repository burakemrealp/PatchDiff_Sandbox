import copy
import json
import logging
from typing import Any, Dict, List, Optional, Tuple

import httpx

from app.core.redis_client import redis_client
from app.services.readable_formatter import format_field_label, split_camel_case

logger = logging.getLogger(__name__)

DDRAGON_CDN = "https://ddragon.leagueoflegends.com/cdn"
LOCALE_CACHE_TTL_SEC = 86400  # 24 hours

# Official 25 leagueoflegends.com / Riot Data Dragon locales -> (lang_bundle, LLM language name)
SUPPORTED_LOCALES: Dict[str, Tuple[str, str]] = {
    "tr_TR": ("tr", "Turkish"),
    "en_US": ("en", "English"),
    "en_GB": ("en", "English"),
    "en_AU": ("en", "English"),
    "en_PH": ("en", "English"),
    "en_SG": ("en", "English"),
    "de_DE": ("de", "German"),
    "es_ES": ("es", "Spanish"),
    "es_MX": ("es", "Spanish (Latin America)"),
    "fr_FR": ("fr", "French"),
    "it_IT": ("it", "Italian"),
    "pt_BR": ("pt", "Portuguese (Brazil)"),
    "pl_PL": ("pl", "Polish"),
    "ru_RU": ("ru", "Russian"),
    "cs_CZ": ("cs", "Czech"),
    "el_GR": ("el", "Greek"),
    "hu_HU": ("hu", "Hungarian"),
    "ro_RO": ("ro", "Romanian"),
    "ar_AE": ("ar", "Arabic"),
    "ja_JP": ("ja", "Japanese"),
    "ko_KR": ("ko", "Korean"),
    "zh_TW": ("zh-TW", "Traditional Chinese"),
    "th_TH": ("th", "Thai"),
    "vi_VN": ("vi", "Vietnamese"),
    "id_ID": ("id", "Indonesian"),
}

_MEMORY_CACHE: Dict[str, Dict[str, Any]] = {}

STAT_LABELS_EN: Dict[str, str] = {
    "base_hp": "Base Health",
    "hp_growth": "Health Growth",
    "base_mp": "Base Mana",
    "mp_growth": "Mana Growth",
    "base_ad": "Base Attack Damage (AD)",
    "ad_growth": "AD Growth",
    "base_armor": "Base Armor",
    "armor_growth": "Armor Growth",
    "base_mr": "Base Magic Resist (MR)",
    "mr_growth": "MR Growth",
    "base_attack_speed": "Base Attack Speed",
    "attack_speed_growth": "Attack Speed Growth",
    "attack_range": "Attack Range",
    "move_speed": "Move Speed",
    "base_hp_regen": "Base Health Regen",
    "hp_regen_growth": "Health Regen Growth",
    "base_mp_regen": "Base Mana Regen",
    "mp_regen_growth": "Mana Regen Growth",
}

TARGET_LABELS_I18N: Dict[str, Dict[str, str]] = {
    "tr": {"squishy": "Kırılgan (ADC/Büyücü)", "bruiser": "Dövüşçü (Bruiser)", "tank": "Ağır Tank"},
    "en": {"squishy": "Squishy (ADC/Mage)", "bruiser": "Bruiser", "tank": "Heavy Tank"},
    "de": {"squishy": "Fragil (ADC/Magier)", "bruiser": "Kämpfer", "tank": "Schwerer Tank"},
    "es": {"squishy": "Frágil (ADC/Mago)", "bruiser": "Luchador", "tank": "Tanque Pesado"},
    "fr": {"squishy": "Fragile (ADC/Mage)", "bruiser": "Combattant", "tank": "Tank Lourd"},
    "it": {"squishy": "Fragile (ADC/Mago)", "bruiser": "Combattente", "tank": "Tank Pesante"},
    "pt": {"squishy": "Frágil (ADC/Mago)", "bruiser": "Lutador", "tank": "Tanque Pesado"},
    "pl": {"squishy": "Kruchy (ADC/Mag)", "bruiser": "Wojownik", "tank": "Ciężki Tank"},
    "ru": {"squishy": "Хрупкий (ADC/Маг)", "bruiser": "Боец", "tank": "Тяжёлый танк"},
    "cs": {"squishy": "Křehký (ADC/Mág)", "bruiser": "Bojovník", "tank": "Těžký Tank"},
    "el": {"squishy": "Εύθραυστος", "bruiser": "Μαχητής", "tank": "Βαρύ Tank"},
    "hu": {"squishy": "Törékeny", "bruiser": "Harcos", "tank": "Nehéz Tank"},
    "ro": {"squishy": "Fragil", "bruiser": "Luptător", "tank": "Tanc Greu"},
    "ar": {"squishy": "هش", "bruiser": "مقاتل", "tank": "مدرع ثقيل"},
    "ja": {"squishy": "柔らかい敵", "bruiser": "ファイター", "tank": "重タンク"},
    "ko": {"squishy": "물몸 (딜러)", "bruiser": "브루저", "tank": "하드 탱커"},
    "zh-TW": {"squishy": "脆皮", "bruiser": "鬥士", "tank": "重裝坦克"},
    "th": {"squishy": "ตัวบาง", "bruiser": "ไฟต์เตอร์", "tank": "แทงก์หนา"},
    "vi": {"squishy": "Máu giấy", "bruiser": "Đấu sĩ", "tank": "Đỡ đòn nặng"},
    "id": {"squishy": "Tipis (Squishy)", "bruiser": "Fighter", "tank": "Tank Berat"},
}

ROLE_LABELS_I18N: Dict[str, Dict[str, str]] = {
    "tr": {
        "top": "Üst Koridor (Top)",
        "jungle": "Orman (Jungle)",
        "mid": "Orta Koridor (Mid)",
        "adc": "Alt Koridor (ADC / Bot)",
        "support": "Destek (Support)",
        "aram": "Tek Koridor (ARAM)",
    },
    "en": {
        "top": "Top Lane",
        "jungle": "Jungle",
        "mid": "Mid Lane",
        "adc": "Bot Lane (ADC)",
        "support": "Support",
        "aram": "Single Lane (ARAM)",
    },
    "de": {"top": "Top-Lane", "jungle": "Jungle", "mid": "Mid-Lane", "adc": "Bot-Lane (ADC)", "support": "Support", "aram": "Einzel-Lane (ARAM)"},
    "es": {"top": "Carril Superior", "jungle": "Jungla", "mid": "Carril Central", "adc": "Carril Inferior (ADC)", "support": "Soporte", "aram": "Un solo carril (ARAM)"},
    "fr": {"top": "Voie du haut", "jungle": "Jungle", "mid": "Voie du milieu", "adc": "Voie du bas (ADC)", "support": "Support", "aram": "Voie unique (ARAM)"},
    "it": {"top": "Corsia Superiore", "jungle": "Giungla", "mid": "Corsia Centrale", "adc": "Corsia Inferiore (ADC)", "support": "Supporto", "aram": "Corsia unica (ARAM)"},
    "pt": {"top": "Rota do Topo", "jungle": "Selva", "mid": "Rota do Meio", "adc": "Atirador (ADC)", "support": "Suporte", "aram": "Rota Única (ARAM)"},
    "pl": {"top": "Góra (Top)", "jungle": "Dżungla", "mid": "Środek (Mid)", "adc": "Dół (ADC)", "support": "Wsparcie", "aram": "Jedna Aleja (ARAM)"},
    "ru": {"top": "Верхняя линия", "jungle": "Лес", "mid": "Центральная линия", "adc": "Нижняя линия (ADC)", "support": "Поддержка", "aram": "Одна линия (ARAM)"},
    "cs": {"top": "Horní lajna", "jungle": "Džungle", "mid": "Středová lajna", "adc": "Spodní lajna (ADC)", "support": "Podpora", "aram": "Jedna lajna (ARAM)"},
    "el": {"top": "Πάνω (Top)", "jungle": "Ζούγκλα", "mid": "Μέση (Mid)", "adc": "Κάτω (ADC)", "support": "Υποστήριξη", "aram": "Μονή Λωρίδα (ARAM)"},
    "hu": {"top": "Felső ösvény", "jungle": "Dzsungel", "mid": "Középső ösvény", "adc": "Alsó ösvény (ADC)", "support": "Támogató", "aram": "Egy ösvény (ARAM)"},
    "ro": {"top": "Sus (Top)", "jungle": "Junglă", "mid": "Mijloc (Mid)", "adc": "Jos (ADC)", "support": "Suport", "aram": "Un singur culoar (ARAM)"},
    "ar": {"top": "المسار العلوي", "jungle": "الغابة", "mid": "المسار الأوسط", "adc": "المسار السفلي (ADC)", "support": "الدعم", "aram": "مسار واحد (ARAM)"},
    "ja": {"top": "トップ", "jungle": "ジャングル", "mid": "ミッド", "adc": "ボット (ADC)", "support": "サポート", "aram": "単一レーン (ARAM)"},
    "ko": {"top": "탑", "jungle": "정글", "mid": "미드", "adc": "원딜 (ADC)", "support": "서포터", "aram": "단일 공격로 (ARAM)"},
    "zh-TW": {"top": "上路", "jungle": "打野", "mid": "中路", "adc": "下路 (ADC)", "support": "輔助", "aram": "單線 (ARAM)"},
    "th": {"top": "เลนบน (Top)", "jungle": "ป่า", "mid": "เลนกลาง (Mid)", "adc": "เลนล่าง (ADC)", "support": "ซัพพอร์ต", "aram": "เลนเดียว (ARAM)"},
    "vi": {"top": "Đường Trên", "jungle": "Đi Rừng", "mid": "Đường Giữa", "adc": "Đường Dưới (ADC)", "support": "Hỗ Trợ", "aram": "Một Đường (ARAM)"},
    "id": {"top": "Top Lane", "jungle": "Jungle", "mid": "Mid Lane", "adc": "Bot Lane (ADC)", "support": "Support", "aram": "Satu Jalur (ARAM)"},
}

MAP_LABELS_I18N: Dict[str, Dict[str, str]] = {
    "tr": {"sr": "Sihirdar Vadisi (5v5)", "aram": "ARAM (Sonsuz Uçurum)", "swiftplay": "Swiftplay (Hızlı Oyun)"},
    "en": {"sr": "Summoner's Rift (5v5)", "aram": "ARAM (Howling Abyss)", "swiftplay": "Swiftplay (Fast 5v5)"},
    "de": {"sr": "Kluft der Beschwörer (5v5)", "aram": "ARAM (Heulende Schlucht)", "swiftplay": "Swiftplay (Schnelles 5v5)"},
    "es": {"sr": "Grieta del Invocador (5v5)", "aram": "ARAM (Abismo de los Lamentos)", "swiftplay": "Partida Rápida (5v5)"},
    "fr": {"sr": "Faille de l'invocateur (5v5)", "aram": "ARAM (Abîme hurlant)", "swiftplay": "Partie Rapide (5v5)"},
    "it": {"sr": "Landa degli Evocatori (5v5)", "aram": "ARAM (Abisso Ululante)", "swiftplay": "Partita Rapida (5v5)"},
    "pt": {"sr": "Summoner's Rift (5v5)", "aram": "ARAM (Howling Abyss)", "swiftplay": "Jogo Rápido (5v5)"},
    "pl": {"sr": "Summoner's Rift (5v5)", "aram": "ARAM (Howling Abyss)", "swiftplay": "Szybka Gra (5v5)"},
    "ru": {"sr": "Ущелье призывателей (5v5)", "aram": "ARAM (Воющая бездна)", "swiftplay": "Быстрая игра (5v5)"},
    "cs": {"sr": "Vyvolávačův žleb (5v5)", "aram": "ARAM (Kvílející propast)", "swiftplay": "Rychlá hra (5v5)"},
    "el": {"sr": "Φαράγγι των Επικαλεστών (5v5)", "aram": "ARAM (Μαινόμενη Άβυσσος)", "swiftplay": "Γρήγορο Παιχνίδι (5v5)"},
    "hu": {"sr": "Idézők szurdoka (5v5)", "aram": "ARAM (Ordító szakadék)", "swiftplay": "Gyorsjáték (5v5)"},
    "ro": {"sr": "Riftul Invocatorului (5v5)", "aram": "ARAM (Abisul Urletelor)", "swiftplay": "Joc Rapid (5v5)"},
    "ar": {"sr": "ساحة الاستدعاء (5v5)", "aram": "ARAM (الهاوية العاوية)", "swiftplay": "اللعب السريع (5v5)"},
    "ja": {"sr": "サモナーズリフト (5v5)", "aram": "ARAM (ハウリングアビス)", "swiftplay": "スイフトプレイ (5v5)"},
    "ko": {"sr": "소환사의 협곡 (5v5)", "aram": "칼바람 나락 (ARAM)", "swiftplay": "신속 대전 (5v5)"},
    "zh-TW": {"sr": "召喚峽谷 (5v5)", "aram": "隨機單中 (ARAM)", "swiftplay": "快速對戰 (5v5)"},
    "th": {"sr": "Summoner's Rift (5v5)", "aram": "ARAM (Howling Abyss)", "swiftplay": "Swiftplay (5v5)"},
    "vi": {"sr": "Summoner's Rift (5v5)", "aram": "ARAM (Vực Gió Hú)", "swiftplay": "Đấu Nhanh (5v5)"},
    "id": {"sr": "Summoner's Rift (5v5)", "aram": "ARAM (Howling Abyss)", "swiftplay": "Swiftplay (5v5)"},
}

QUEST_REWARD_EN: Dict[str, str] = {
    "top": "Level 20 Cap + Bonus XP + Empowered Teleport (TP)",
    "jungle": "Primal Smite + Jungle/River Move Speed",
    "mid": "Free Tier 3 Boots + Empowered Recall",
    "adc": "Dedicated Boot Role Slot (6 Legendaries + 1 Boot = 7 Items) + Bonus Gold",
    "support": "Dedicated Control Ward Slot (40g Discount)",
    "aram": "ARAM is a single-lane map — Role Quests disabled (6 Items, Max Level 18). Mana & Sustain prioritized.",
}

QUEST_REWARD_TR: Dict[str, str] = {
    "top": "Seviye 20 Sınırı + İlave XP + Güçlendirilmiş Işınlan (TP)",
    "jungle": "İlkel Çarp (Primal Smite) + Orman/Nehir Hareket Hızı",
    "mid": "Ücretsiz 3. Aşama (Tier 3) Ayakkabı + Güçlendirilmiş Üsse Dönüş",
    "adc": "Ayrı Ayakkabı Rol Slotu (6 Efsanevi + 1 Ayakkabı = 7 Eşya) + Ek Altın",
    "support": "Ayrı Kontrol Totemi Slotu (40g İndirimli)",
    "aram": "ARAM tek koridorlu haritadır — Rol Görevi kapalı (6 Eşya, En Yüksek Seviye 18). Mana ve Can Yenileme önceliklidir.",
}

PLAYSTYLE_LABEL_TR: Dict[str, str] = {
    "burst": "Anlık Patlama (Burst / One-Shot)",
    "dps": "Sürekli Hasar (Sustained DPS)",
    "balanced": "Dengeli & Hayatta Kalma (EHP + Tempo)",
}

KIT_ARCHETYPE_EN: Dict[str, str] = {
    "İsabet Etkili (On-Hit) Büyücü / Nişancı": "On-Hit Mage / Marksman",
    "Uzak Menzilli Kontrol / Patlama Büyücüsü": "Long-Range Control / Burst Mage",
    "Yetenek Odaklı Nişancı (Spell-Caster ADC)": "Spell-Caster ADC",
    "Kritik & Sürekli Hasar Nişancısı": "Crit & Sustained DPS Marksman",
    "Yakın Dövüş AP Dövüşçü / Tank": "Melee AP Fighter / Tank",
    "Ön Saf Tankı": "Frontline Tank",
    "Hareketli AP Suikastçı": "Mobile AP Assassin",
    "Fiziksel Suikastçı / Düellocu": "AD Assassin / Skirmisher",
    "Fiziksel Dövüşçü": "AD Fighter",
    "Hibrit / Çok Yönlü Şampiyon": "Hybrid / Versatile Champion",
}

KIT_ARCHETYPE_TR: Dict[str, str] = {v: k for k, v in KIT_ARCHETYPE_EN.items()}

SHARD_SLOT_EN: Dict[str, str] = {
    "Saldırı": "Offense",
    "Esnek": "Flex",
    "Savunma": "Defense",
}
SHARD_SLOT_TR: Dict[str, str] = {v: k for k, v in SHARD_SLOT_EN.items()}

SHARD_LABEL_EN: Dict[str, str] = {
    "adaptive_force": "+9 Adaptive Force",
    "attack_speed": "+10% Attack Speed",
    "ability_haste": "+8 Ability Haste",
    "move_speed": "+2% Move Speed",
    "scaling_hp": "+10–180 Scaling HP",
    "flat_hp": "+65 Health",
    "tenacity": "+10% Tenacity & Slow Resist",
}

SHARD_LABEL_TR: Dict[str, str] = {
    "adaptive_force": "+9 Değişken Kuvvet",
    "attack_speed": "+%10 Saldırı Hızı",
    "ability_haste": "+8 Yetenek Hızı",
    "move_speed": "+%2 Hareket Hızı",
    "scaling_hp": "+10–180 Can (Seviyeye Göre)",
    "flat_hp": "+65 Sabit Can",
    "tenacity": "+%10 Sıvışma ve Yavaşlatma Direnci",
}

ADAPTATION_NOTE_EN: Dict[str, str] = {
    "Yetenek bekleme süresi / mana maliyeti arttığı için Yetenek Hızı ve Mana eşyaları önceliklendirildi.": (
        "Ability Haste and Mana items were prioritized to offset increased cooldown / mana costs."
    ),
    "İsabet (On-Hit) etkisi güçlendiği için saldırı hızı ve isabet etkili eşyalar öne çıkarıldı.": (
        "Attack speed and On-Hit items were prioritized following the On-Hit buff."
    ),
    "Saldırı menzili arttığı için sürekli hasar ve pozisyon avantajı sunan eşyalar ödüllendirildi.": (
        "Sustained DPS items were rewarded to leverage the increased attack range."
    ),
    "Yetenek Gücü (AP) oranı güçlendiği için yüksek AP ve büyü nüfuzu sinerjisi öne çıkarıldı.": (
        "High-AP and Magic Penetration synergies were boosted following the AP ratio buff."
    ),
    "Saldırı Gücü (AD) oranı güçlendiği için yüksek AD ve yetenek döngüsü eşyaları ödüllendirildi.": (
        "High-AD and Ability Haste synergies were boosted following the AD ratio buff."
    ),
    "Kalkan / dayanıklılık mekaniği güçlendiği için dengeli dizilimde hayatta kalma değeri artırıldı.": (
        "Survivability items received higher weight in balanced builds following the shield/durability buff."
    ),
}
ADAPTATION_NOTE_TR: Dict[str, str] = {v: k for k, v in ADAPTATION_NOTE_EN.items()}

SYNERGY_NOTE_TR_MAP: Dict[str, str] = {
    "Amplifies burst and dash trades alongside item penetration.": "Ani patlama/atılma hasarını eşya penetrasyonuyla katlar.",
    "Provides reliable lane and ARAM health sustain during repeated trades.": "Sürekli çatışmada/ARAM'da hayatta kalma ve can yenilenmesi sağlar.",
    "Shortens ultimate cooldown to maximize high-AP/AD ability rotations.": "Ulti bekleme süresini kısaltarak yüksek AP/AD eşya rotasyonunu sıklaştırır.",
    "Accelerates reaching expensive core item spikes earlier.": "Yüksek maliyetli çekirdek eşyalara daha erken ulaşmayı hızlandırır.",
    "Offsets missing mana in items to keep abilities flowing continuously.": "Eşya dizilimindeki mana açığını kapatarak kesintisiz yetenek kullanımı sağlar.",
    "Grants clutch takedown healing and bonus gold in extended teamfights.": "Takım savaşlarında skor sonrası hayatta kalma ve altın kazancı sunar.",
    "Stacks with Crit and On-Hit items to maximize sustained auto-attack DPS.": "Kritik/İsabet eşyalarıyla birleşerek sürekli düz vuruş DPS'ini maksimize eder.",
    "Supplements item Ability Haste for faster basic ability rotations.": "Eşyalardan gelen Yetenek Hızını tamamlayarak daha hızlı kombo döngüsü sağlar.",
    "Covers lifesteal sustain when defensive items are prioritized over Bloodthirster.": "Dizilimde can çalma eşyası bulunmadığı için sürdürülebilirlik açığını kapatır.",
    "Synergizes directly with percentage armor/magic pen against high-HP targets.": "Yüksek canlı hedeflere karşı % delme/yakma eşyalarıyla doğrudan sinerji kurar.",
    "Secures one-shot lethal thresholds against squishy targets.": "Kırılgan hedeflerde bitirici kombo (One-Shot) eşiğini garantiler.",
    "Secures laning and late-game mana sustain when items lack flat mana.": "Eşyalarda yeterli mana olmadığı için koridor ve geç oyun mana ekonomisini güvenceye alır.",
    "Axiom Arcanist boosts ultimate damage and refunds cooldown on takedowns.": "Aksiyom Üstadı ile ulti hasarını ve bekleme süresi dönüşünü doğrudan güçlendirir.",
    "Pairs with item Ability Haste for faster mid-fight spell resets.": "Eşya Yetenek Hızı ile birleşerek savaş içi yetenek sıfırlanmasını hızlandırır.",
    "Grants scaling AP/AD that multiplies alongside Rabadon or Critical Strike in 6/7-item games.": "Geç oyun 6/7 eşyalı ölçeklenmede Rabadon/Kritik çarpanlarıyla katlanan saf AP/AD verir.",
    "Amplifies item Armor and Magic Resist by a percentage to maximize durability.": "Eşyalardan gelen Zırh/MR değerlerini yüzdesel olarak artırarak dayanıklılığı katlar.",
    "Scales maximum health higher alongside HP-heavy items.": "Can veren eşyalarla birleşerek maksimum canı ölçekler.",
    "Refunds gold on every completed legendary in expensive 6/7-item builds.": "6/7 eşyalık pahalı dizilimlerde her efsanevi eşya sonrası altın iadesiyle tempoyu hızlandırır.",
    "Saves 300g on boots to accelerate your first core item completion.": "300g ayakkabı tasarrufu ile 1. çekirdek eşyaya daha erken ulaşmayı sağlar.",
    "Lowers Summoner Spell and active item cooldowns (Zhonya / Flash).": "Eşya ve sihirdar büyüsü bekleme sürelerini düşürerek Zhonya/aktif eşya sinerjisi kurar.",
    "Unlocks bonus Ability Haste and Adaptive Force from diverse item stats.": "Çok çeşitli stat içeren bu dizilimde ek Yetenek Hızı ve Değişken Kuvvet açar.",
}


def normalize_locale(lang: Optional[str]) -> Tuple[str, str, str]:
    """
    Validates and normalizes a user-requested locale string.
    Returns: (riot_locale, lang_bundle_key, llm_language_name)
    """
    if not lang:
        return "tr_TR", "tr", "Turkish"
    cleaned = lang.strip().replace("-", "_")
    if cleaned in SUPPORTED_LOCALES:
        bkey, lname = SUPPORTED_LOCALES[cleaned]
        return cleaned, bkey, lname
    lower_map = {k.lower(): k for k in SUPPORTED_LOCALES}
    if cleaned.lower() in lower_map:
        canon = lower_map[cleaned.lower()]
        bkey, lname = SUPPORTED_LOCALES[canon]
        return canon, bkey, lname
    return "tr_TR", "tr", "Turkish"


def get_ddragon_localization(version: Optional[str], lang: Optional[str]) -> Optional[Dict[str, Any]]:
    """
    Fetches localized champion, item, rune, and rune tree names from Riot Data Dragon CDN
    with RAM + Redis 24-hour caching.
    Returns None for 'tr_TR' because the primary database snapshots are stored in 'tr_TR'.
    """
    riot_locale, _, _ = normalize_locale(lang)
    if not version or riot_locale == "tr_TR":
        return None

    cache_key = f"patchdiff:i18n:{version}:{riot_locale}"
    if cache_key in _MEMORY_CACHE:
        return _MEMORY_CACHE[cache_key]

    try:
        cached_raw = redis_client.get(cache_key)
        if cached_raw:
            parsed = json.loads(cached_raw)
            _MEMORY_CACHE[cache_key] = parsed
            return parsed
    except Exception:
        pass

    base = f"{DDRAGON_CDN}/{version}/data/{riot_locale}"
    try:
        with httpx.Client(timeout=12.0) as client:
            c_resp = client.get(f"{base}/champion.json")
            i_resp = client.get(f"{base}/item.json")
            r_resp = client.get(f"{base}/runesReforged.json")
            c_resp.raise_for_status()
            i_resp.raise_for_status()
            r_resp.raise_for_status()

            champs_raw = c_resp.json().get("data") or {}
            items_raw = i_resp.json().get("data") or {}
            runes_raw = r_resp.json() or []

        champs_map = {
            k: {"name": v.get("name", k), "title": v.get("title", "")}
            for k, v in champs_raw.items()
        }
        items_map = {str(iid): v.get("name", str(iid)) for iid, v in items_raw.items()}
        trees_map: Dict[str, str] = {}
        runes_key_map: Dict[str, str] = {}
        runes_id_map: Dict[str, str] = {}

        for tree in runes_raw:
            tkey = str(tree.get("key") or "")
            tname = str(tree.get("name") or tkey)
            if tkey:
                trees_map[tkey] = tname
            for slot in tree.get("slots") or []:
                for rn in slot.get("runes") or []:
                    rkey = str(rn.get("key") or "")
                    rid = str(rn.get("id") or "")
                    rname = str(rn.get("name") or rkey)
                    if rkey:
                        runes_key_map[rkey] = rname
                    if rid:
                        runes_id_map[rid] = rname

        bundle = {
            "locale": riot_locale,
            "champions": champs_map,
            "items": items_map,
            "trees": trees_map,
            "runes": runes_key_map,
            "rune_ids": runes_id_map,
        }
        _MEMORY_CACHE[cache_key] = bundle
        try:
            redis_client.setex(cache_key, LOCALE_CACHE_TTL_SEC, json.dumps(bundle, ensure_ascii=False))
        except Exception:
            pass
        return bundle
    except Exception as exc:
        logger.warning("Failed to fetch Riot DDragon localization (%s / %s): %s", version, riot_locale, exc)
        return None


def localize_target_label(target_profile: str, lang: Optional[str]) -> str:
    _, bkey, _ = normalize_locale(lang)
    table = TARGET_LABELS_I18N.get(bkey) or TARGET_LABELS_I18N["en"]
    return table.get(target_profile, target_profile)


def localize_game_context(gc: Optional[Dict[str, Any]], lang: Optional[str]) -> Optional[Dict[str, Any]]:
    if not gc:
        return gc
    _, bkey, _ = normalize_locale(lang)

    out = dict(gc)
    role_key = "aram" if not out.get("role_quests_enabled") else str(out.get("role", "mid"))
    map_key = str(out.get("game_map", "sr"))

    role_table = ROLE_LABELS_I18N.get(bkey) or ROLE_LABELS_I18N["en"]
    map_table = MAP_LABELS_I18N.get(bkey) or MAP_LABELS_I18N["en"]
    quest_table = QUEST_REWARD_TR if bkey == "tr" else QUEST_REWARD_EN

    out["role_label"] = role_table.get(role_key, out.get("role_label"))
    out["map_label"] = map_table.get(map_key, out.get("map_label"))
    out["quest_reward"] = quest_table.get(role_key, out.get("quest_reward"))
    return out


def localize_diff_payload(
    entity_type: str,
    diff_payload: Dict[str, Any],
    lang: Optional[str],
    loc_bundle: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Localizes DB patch diff payloads into clean English or DDragon-localized labels for non-Turkish locales."""
    riot_locale, _, _ = normalize_locale(lang)
    if riot_locale == "tr_TR":
        return diff_payload

    out = copy.deepcopy(diff_payload)
    if entity_type == "champion":
        st_deltas = out.get("stat_deltas") or []
        ab_deltas = out.get("ability_deltas") or []
        mc_deltas = out.get("mechanic_deltas") or []
        for st in st_deltas:
            sname = str(st.get("stat_name", ""))
            st["stat_label"] = STAT_LABELS_EN.get(sname, split_camel_case(sname))
        for mc in mc_deltas:
            fname = str(mc.get("field_name", ""))
            mc["field_label"] = split_camel_case(fname)
            if mc.get("spell_label") and "Pasif" in str(mc["spell_label"]):
                mc["spell_label"] = str(mc["spell_label"]).replace("Pasif", "Passive")
            if mc.get("display_old") and str(mc["display_old"]).startswith("%"):
                mc["display_old"] = "/".join(
                    f"{p[1:]}%" if p.startswith("%") else p for p in str(mc["display_old"]).split("/")
                )
            if mc.get("display_new") and str(mc["display_new"]).startswith("%"):
                mc["display_new"] = "/".join(
                    f"{p[1:]}%" if p.startswith("%") else p for p in str(mc["display_new"]).split("/")
                )
        if str(out.get("summary") or "").startswith("Otomatik yama farkı"):
            parts_en: List[str] = []
            if st_deltas:
                parts_en.append(f"{len(st_deltas)} base stat(s)")
            if ab_deltas:
                slots_str = "/".join(str(a.get("slot", "")) for a in ab_deltas)
                parts_en.append(f"{len(ab_deltas)} ability ({slots_str})")
            if mc_deltas:
                uniq_spells = sorted({str(m.get("spell_name", "")) for m in mc_deltas})[:4]
                parts_en.append(f"{len(mc_deltas)} mechanic/parameter ({', '.join(uniq_spells)})")
            if parts_en:
                out["summary"] = f"Auto patch diff: {', '.join(parts_en)} updated."
    elif entity_type == "item":
        if loc_bundle and out.get("item_id"):
            out["name"] = (loc_bundle.get("items") or {}).get(str(out["item_id"]), out.get("name"))
        pchanges = out.get("passive_data_changes") or []
        parts: List[str] = []
        gc = out.get("gold_change")
        if gc:
            sign = "+" if gc.get("delta", 0) > 0 else ""
            parts.append(f"Gold {sign}{gc.get('delta')}g")
        if out.get("stat_changes"):
            parts.append(f"{len(out['stat_changes'])} stat change(s)")
        if pchanges:
            pairs = []
            for p in pchanges[:3]:
                flabel = split_camel_case(str(p.get("field_name", "")))
                p["field_label"] = flabel
                d_old = str(p.get("display_old", p.get("old_value")))
                d_new = str(p.get("display_new", p.get("new_value")))
                if d_old.startswith("%"):
                    d_old = f"{d_old[1:]}%"
                if d_new.startswith("%"):
                    d_new = f"{d_new[1:]}%"
                pairs.append(f"{flabel}: {d_old} → {d_new}")
            parts.append(f"Passive ({', '.join(pairs)})")
        if parts:
            out["summary"] = ", ".join(parts)
    elif entity_type == "rune":
        if loc_bundle:
            rkey = str(out.get("key") or "")
            rid = str(out.get("rune_id") or "")
            if rkey in (loc_bundle.get("runes") or {}):
                out["name"] = loc_bundle["runes"][rkey]
            elif rid in (loc_bundle.get("rune_ids") or {}):
                out["name"] = loc_bundle["rune_ids"][rid]
        eff_changes = out.get("effect_changes") or []
        if eff_changes:
            pairs = ", ".join(
                f"{split_camel_case(str(c['field_name']))}: {c['old_value']} → {c['new_value']}"
                for c in eff_changes[:4]
            )
            out["summary"] = f"Rune adjustment ({pairs})"
        elif out.get("changed_numbers"):
            pairs = ", ".join(f"{p['old']}->{p['new']}" for p in out["changed_numbers"][:4])
            out["summary"] = f"Rune adjustment ({pairs})"
    return out


def localize_recommend_report(
    report: Dict[str, Any],
    lang: Optional[str],
    version: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Translates champion, item, rune, role, map, gameplay archetype, playstyle, and stat shard
    labels inside a MetaShiftAnalyzer report into the requested official LoL locale.
    """
    riot_locale, bkey, _ = normalize_locale(lang)
    out = copy.deepcopy(report)

    out["game_context"] = localize_game_context(out.get("game_context"), riot_locale)

    if riot_locale == "tr_TR":
        # Localize internal pure-English engine strings into Turkish for tr_TR users
        prof = out.get("profile")
        if isinstance(prof, dict):
            ka = prof.get("kit_archetype_label")
            if ka in KIT_ARCHETYPE_TR:
                prof["kit_archetype_label"] = KIT_ARCHETYPE_TR[ka]
            ps = prof.get("patch_signals")
            if isinstance(ps, dict) and ps.get("adaptation_notes"):
                ps["adaptation_notes"] = [
                    ADAPTATION_NOTE_TR.get(n, n) for n in ps["adaptation_notes"]
                ]

        # Ensure rune diffs / synergetic notes generated by the pure-English engine are friendly Turkish
        from app.services.locale_service import _localize_tr_rune_page  # local helper below

        base = out.get("old_meta_baseline")
        if isinstance(base, dict):
            _localize_tr_rune_page(base.get("rune_page"))

        for var in out.get("variations") or []:
            style = str(var.get("playstyle") or "")
            if style in PLAYSTYLE_LABEL_TR:
                var["playstyle_label"] = PLAYSTYLE_LABEL_TR[style]
            _localize_tr_rune_page(var.get("rune_page"))

        return out

    ver = version or out.get("to_version")
    loc = get_ddragon_localization(ver, riot_locale) or {}
    items_map = loc.get("items") or {}
    champs_map = loc.get("champions") or {}
    trees_map = loc.get("trees") or {}
    runes_map = loc.get("runes") or {}
    rune_ids_map = loc.get("rune_ids") or {}

    ckey = out.get("champion_key")
    if ckey and ckey in champs_map:
        out["champion_name"] = champs_map[ckey].get("name", out.get("champion_name"))

    prof = out.get("profile")
    if isinstance(prof, dict):
        ka = prof.get("kit_archetype_label")
        if ka in KIT_ARCHETYPE_EN:
            prof["kit_archetype_label"] = KIT_ARCHETYPE_EN[ka]
        ps = prof.get("patch_signals")
        if isinstance(ps, dict) and ps.get("adaptation_notes"):
            ps["adaptation_notes"] = [
                ADAPTATION_NOTE_EN.get(n, n) for n in ps["adaptation_notes"]
            ]

    def _loc_rune_entry(entry: Dict[str, Any]) -> None:
        rkey = str(entry.get("key") or "")
        rid = str(entry.get("rune_id") or "")
        if rkey in runes_map:
            entry["name"] = runes_map[rkey]
        elif rid in rune_ids_map:
            entry["name"] = rune_ids_map[rid]

    def _loc_rune_page(rp: Optional[Dict[str, Any]]) -> None:
        if not isinstance(rp, dict):
            return
        pt = rp.get("primary_tree")
        if isinstance(pt, dict):
            if pt.get("key") in trees_map:
                pt["name"] = trees_map[pt["key"]]
            if isinstance(pt.get("keystone"), dict):
                _loc_rune_entry(pt["keystone"])
            for r in pt.get("runes") or []:
                _loc_rune_entry(r)
        st = rp.get("secondary_tree")
        if isinstance(st, dict):
            if st.get("key") in trees_map:
                st["name"] = trees_map[st["key"]]
            for r in st.get("runes") or []:
                _loc_rune_entry(r)
        for sh in rp.get("stat_shards") or []:
            if sh.get("slot") in SHARD_SLOT_EN:
                sh["slot"] = SHARD_SLOT_EN[sh["slot"]]
            if sh.get("key") in SHARD_LABEL_EN:
                sh["label"] = SHARD_LABEL_EN[sh["key"]]

    base = out.get("old_meta_baseline")
    if isinstance(base, dict):
        for it in base.get("items") or []:
            iid = str(it.get("item_id") or "")
            if iid in items_map:
                it["name"] = items_map[iid]
        ks = base.get("keystone")
        if isinstance(ks, dict) and ks.get("key") in runes_map:
            ks["label"] = runes_map[ks["key"]]
        _loc_rune_page(base.get("rune_page"))

    for var in out.get("variations") or []:
        for it in var.get("items") or []:
            iid = str(it.get("item_id") or "")
            if iid in items_map:
                it["name"] = items_map[iid]
        ks = var.get("keystone")
        if isinstance(ks, dict):
            if ks.get("key") in runes_map:
                ks["label"] = runes_map[ks["key"]]
            pt_key = ((var.get("rune_page") or {}).get("primary_tree") or {}).get("key")
            if pt_key in trees_map:
                ks["tree"] = trees_map[pt_key]
        _loc_rune_page(var.get("rune_page"))

    return out


def _localize_tr_rune_page(rp: Optional[Dict[str, Any]]) -> None:
    """Translates English Stat Shard labels and synergy notes to Turkish for 'tr_TR' responses."""
    if not isinstance(rp, dict):
        return
    for sh in rp.get("stat_shards") or []:
        if sh.get("slot") in SHARD_SLOT_TR:
            sh["slot"] = SHARD_SLOT_TR[sh["slot"]]
        if sh.get("key") in SHARD_LABEL_TR:
            sh["label"] = SHARD_LABEL_TR[sh["key"]]
    notes = rp.get("synergy_notes")
    if isinstance(notes, list) and notes:
        localized_notes: List[str] = []
        for note in notes:
            if ":" in note:
                rname, rest = note.split(":", 1)
                tr_rest = SYNERGY_NOTE_TR_MAP.get(rest.strip(), rest.strip())
                localized_notes.append(f"{rname.strip()}: {tr_rest}")
            else:
                localized_notes.append(SYNERGY_NOTE_TR_MAP.get(note, note))
        rp["synergy_notes"] = localized_notes


ZERO_DAY_VERDICT_LABELS: Dict[str, Dict[str, str]] = {
    "tr": {
        "MODE_SPECIFIC_TRAP": "Farklı Mod Değişikliği (SR Etkisi Yok)",
        "TRAP_BUFF_NET_NERF": "Tuzak Buff (Ekosistemde Net Zayıflama)",
        "HIDDEN_NET_BUFF": "Gizli Net Güçlenme (Nerfe Rağmen Artı)",
        "PLACEBO_BUFF": "Plasebo Buff (< +%1 Gerçek Etki)",
        "PAPER_TIGER_NERF": "Kâğıt Üstü Nerf (< %1 Kombo Kaybı)",
        "CONFIRMED_POWER_SPIKE": "Doğrulanmış Güç Patlaması",
        "CONFIRMED_HEAVY_NERF": "Doğrulanmış Ağır Nerf",
        "VERIFIED_BUFF": "Doğrulanmış Net Buff",
        "VERIFIED_NERF": "Doğrulanmış Net Nerf",
        "NEUTRAL_ADJUSTMENT": "Dengeli / Nötr Düzenleme",
    },
    "en": {
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
    },
    "de": {
        "MODE_SPECIFIC_TRAP": "Modus-spezifische Änderung (Kein SR-Einfluss)",
        "TRAP_BUFF_NET_NERF": "Fallen-Buff (Netto-Ökosystem-Nerf)",
        "HIDDEN_NET_BUFF": "Versteckter Netto-Buff (Trotz Nerf)",
        "PLACEBO_BUFF": "Placebo-Buff (< +1% Kampfwirkung)",
        "PAPER_TIGER_NERF": "Papiertiger-Nerf (< 1% Kombo-Verlust)",
        "CONFIRMED_POWER_SPIKE": "Bestätigter Power-Spike",
        "CONFIRMED_HEAVY_NERF": "Bestätigter Starker Nerf",
        "VERIFIED_BUFF": "Bestätigter Netto-Buff",
        "VERIFIED_NERF": "Bestätigter Netto-Nerf",
        "NEUTRAL_ADJUSTMENT": "Neutrale Anpassung",
    },
    "es": {
        "MODE_SPECIFIC_TRAP": "Cambio Exclusivo de Otro Modo",
        "TRAP_BUFF_NET_NERF": "Buff Trampa (Nerf Neto de Ecosistema)",
        "HIDDEN_NET_BUFF": "Buff Neto Oculto (Pese al Nerf)",
        "PLACEBO_BUFF": "Buff Placebo (< +1% Impacto Real)",
        "PAPER_TIGER_NERF": "Nerf de Papel (< 1% Pérdida de Combo)",
        "CONFIRMED_POWER_SPIKE": "Pico de Poder Confirmado",
        "CONFIRMED_HEAVY_NERF": "Nerf Fuerte Confirmado",
        "VERIFIED_BUFF": "Buff Neto Verificado",
        "VERIFIED_NERF": "Nerf Neto Verificado",
        "NEUTRAL_ADJUSTMENT": "Ajuste Neutral",
    },
    "fr": {
        "MODE_SPECIFIC_TRAP": "Ajustement Spécifique à un Autre Mode",
        "TRAP_BUFF_NET_NERF": "Buff Piège (Nerf Net d'Écosystème)",
        "HIDDEN_NET_BUFF": "Buff Net Caché (Malgré le Nerf)",
        "PLACEBO_BUFF": "Buff Placebo (< +1% d'Impact Réel)",
        "PAPER_TIGER_NERF": "Nerf en Papier (< 1% Perte de Combo)",
        "CONFIRMED_POWER_SPIKE": "Pic de Puissance Confirmé",
        "CONFIRMED_HEAVY_NERF": "Gros Nerf Confirmé",
        "VERIFIED_BUFF": "Buff Net Vérifié",
        "VERIFIED_NERF": "Nerf Net Vérifié",
        "NEUTRAL_ADJUSTMENT": "Ajustement Neutre",
    },
    "it": {
        "MODE_SPECIFIC_TRAP": "Modifica Specifica per Altra Modalità",
        "TRAP_BUFF_NET_NERF": "Buff Trappola (Nerf Netto)",
        "HIDDEN_NET_BUFF": "Buff Netto Nascosto (Nonostante il Nerf)",
        "PLACEBO_BUFF": "Buff Placebo (< +1% Impatto Reale)",
        "PAPER_TIGER_NERF": "Nerf Apparente (< 1% Perdita Combo)",
        "CONFIRMED_POWER_SPIKE": "Picco di Potenza Confermato",
        "CONFIRMED_HEAVY_NERF": "Nerf Pesante Confermato",
        "VERIFIED_BUFF": "Buff Netto Verificato",
        "VERIFIED_NERF": "Nerf Netto Verificato",
        "NEUTRAL_ADJUSTMENT": "Aggiustamento Neutro",
    },
    "pt": {
        "MODE_SPECIFIC_TRAP": "Ajuste Exclusivo de Outro Modo",
        "TRAP_BUFF_NET_NERF": "Buff Armadilha (Nerf Líquido)",
        "HIDDEN_NET_BUFF": "Buff Líquido Oculto (Apesar do Nerf)",
        "PLACEBO_BUFF": "Buff Placebo (< +1% Impacto Real)",
        "PAPER_TIGER_NERF": "Nerf no Papel (< 1% Perda de Combo)",
        "CONFIRMED_POWER_SPIKE": "Pico de Poder Confirmado",
        "CONFIRMED_HEAVY_NERF": "Nerf Pesado Confirmado",
        "VERIFIED_BUFF": "Buff Líquido Verificado",
        "VERIFIED_NERF": "Nerf Líquido Verificado",
        "NEUTRAL_ADJUSTMENT": "Ajuste Neutro",
    },
    "pl": {
        "MODE_SPECIFIC_TRAP": "Zmiana Tylko dla Innego Trybu",
        "TRAP_BUFF_NET_NERF": "Buff-Pułapka (Netto Osłabienie)",
        "HIDDEN_NET_BUFF": "Ukryty Netto Buff (Mimo Nerfa)",
        "PLACEBO_BUFF": "Buff Placebo (< +1% Wpływu)",
        "PAPER_TIGER_NERF": "Papierowy Nerf (< 1% Straty Kombo)",
        "CONFIRMED_POWER_SPIKE": "Potwierdzony Skok Mocy",
        "CONFIRMED_HEAVY_NERF": "Potwierdzony Mocny Nerf",
        "VERIFIED_BUFF": "Potwierdzony Netto Buff",
        "VERIFIED_NERF": "Potwierdzony Netto Nerf",
        "NEUTRAL_ADJUSTMENT": "Neutralna Zmiana",
    },
    "ru": {
        "MODE_SPECIFIC_TRAP": "Правка только для другого режима",
        "TRAP_BUFF_NET_NERF": "Ловушка-бафф (итоговое ослабление)",
        "HIDDEN_NET_BUFF": "Скрытый бафф (вопреки нерфу)",
        "PLACEBO_BUFF": "Бафф-плацебо (< +1% в бою)",
        "PAPER_TIGER_NERF": "Бумажный нерф (< 1% потери комбо)",
        "CONFIRMED_POWER_SPIKE": "Подтверждённый скачок силы",
        "CONFIRMED_HEAVY_NERF": "Подтверждённый сильный нерф",
        "VERIFIED_BUFF": "Подтверждённый бафф",
        "VERIFIED_NERF": "Подтверждённый нерф",
        "NEUTRAL_ADJUSTMENT": "Нейтральная правка",
    },
    "cs": {
        "MODE_SPECIFIC_TRAP": "Úprava jen pro jiný herní režim",
        "TRAP_BUFF_NET_NERF": "Past-buff (čisté oslabení)",
        "HIDDEN_NET_BUFF": "Skrytý čistý buff (navzdory nerfu)",
        "PLACEBO_BUFF": "Placebo buff (< +1% dopad)",
        "PAPER_TIGER_NERF": "Papírový nerf (< 1% ztráta komba)",
        "CONFIRMED_POWER_SPIKE": "Potvrzený nárůst síly",
        "CONFIRMED_HEAVY_NERF": "Potvrzený silný nerf",
        "VERIFIED_BUFF": "Ověřený čistý buff",
        "VERIFIED_NERF": "Ověřený čistý nerf",
        "NEUTRAL_ADJUSTMENT": "Neutrální úprava",
    },
    "el": {
        "MODE_SPECIFIC_TRAP": "Αλλαγή μόνο για άλλη λειτουργία",
        "TRAP_BUFF_NET_NERF": "Παγίδα Buff (Καθαρή Αποδυνάμωση)",
        "HIDDEN_NET_BUFF": "Κρυφό Καθαρό Buff (Παρά το Nerf)",
        "PLACEBO_BUFF": "Εικονικό Buff (< +1% Επίδραση)",
        "PAPER_TIGER_NERF": "Χάρτινο Nerf (< 1% Απώλεια)",
        "CONFIRMED_POWER_SPIKE": "Επιβεβαιωμένο Power Spike",
        "CONFIRMED_HEAVY_NERF": "Επιβεβαιωμένο Βαρύ Nerf",
        "VERIFIED_BUFF": "Επιβεβαιωμένο Buff",
        "VERIFIED_NERF": "Επιβεβαιωμένο Nerf",
        "NEUTRAL_ADJUSTMENT": "Ουδέτερη Ρύθμιση",
    },
    "hu": {
        "MODE_SPECIFIC_TRAP": "Más játékmódra vonatkozó módosítás",
        "TRAP_BUFF_NET_NERF": "Csapda Buff (Nettó Gyengülés)",
        "HIDDEN_NET_BUFF": "Rejtett Nettó Buff (Nerf Ellenére)",
        "PLACEBO_BUFF": "Placebo Buff (< +1% Harci Hatás)",
        "PAPER_TIGER_NERF": "Papír Nerf (< 1% Kombó Veszteség)",
        "CONFIRMED_POWER_SPIKE": "Igazolt Erőlöket",
        "CONFIRMED_HEAVY_NERF": "Igazolt Erős Nerf",
        "VERIFIED_BUFF": "Igazolt Nettó Buff",
        "VERIFIED_NERF": "Igazolt Nettó Nerf",
        "NEUTRAL_ADJUSTMENT": "Semleges Módosítás",
    },
    "ro": {
        "MODE_SPECIFIC_TRAP": "Modificare exclusivă altui mod",
        "TRAP_BUFF_NET_NERF": "Buff Capcană (Nerf Net)",
        "HIDDEN_NET_BUFF": "Buff Net Ascuns (În Ciuda Nerfului)",
        "PLACEBO_BUFF": "Buff Placebo (< +1% Impact)",
        "PAPER_TIGER_NERF": "Nerf Pe Hârtie (< 1% Pierdere)",
        "CONFIRMED_POWER_SPIKE": "Creștere Confirmată de Putere",
        "CONFIRMED_HEAVY_NERF": "Nerf Puternic Confirmat",
        "VERIFIED_BUFF": "Buff Net Verificat",
        "VERIFIED_NERF": "Nerf Net Verificat",
        "NEUTRAL_ADJUSTMENT": "Ajustare Neutră",
    },
    "ar": {
        "MODE_SPECIFIC_TRAP": "تعديل خاص بنمط آخر",
        "TRAP_BUFF_NET_NERF": "تعزيز خادع (انخفاض فعلي)",
        "HIDDEN_NET_BUFF": "تعزيز خفي رغم الإضعاف",
        "PLACEBO_BUFF": "تعزيز شكلي (< +1% تأثير قتالي)",
        "PAPER_TIGER_NERF": "إضعاف ورقي (< 1% خسارة ضرر)",
        "CONFIRMED_POWER_SPIKE": "قفزة قوة مؤكدة",
        "CONFIRMED_HEAVY_NERF": "إضعاف قوي مؤكد",
        "VERIFIED_BUFF": "تعزيز فعلي مؤكد",
        "VERIFIED_NERF": "إضعاف فعلي مؤكد",
        "NEUTRAL_ADJUSTMENT": "تعديل متوازن",
    },
    "ja": {
        "MODE_SPECIFIC_TRAP": "他モード専用調整 (SR影響なし)",
        "TRAP_BUFF_NET_NERF": "罠バフ (環境トータル弱体化)",
        "HIDDEN_NET_BUFF": "隠れ実質バフ (ナーフ下でも強化)",
        "PLACEBO_BUFF": "プラセボバフ (+1%未満の影響)",
        "PAPER_TIGER_NERF": "見かけナーフ (1%未満の損失)",
        "CONFIRMED_POWER_SPIKE": "確実なパワースパイク",
        "CONFIRMED_HEAVY_NERF": "確実な大幅ナーフ",
        "VERIFIED_BUFF": "実質バフ確認済み",
        "VERIFIED_NERF": "実質ナーフ確認済み",
        "NEUTRAL_ADJUSTMENT": "中立的な調整",
    },
    "ko": {
        "MODE_SPECIFIC_TRAP": "타 모드 전용 변경 (소환사의 협곡 무영향)",
        "TRAP_BUFF_NET_NERF": "함정 버프 (아이템/룬 포함 실질 너프)",
        "HIDDEN_NET_BUFF": "숨은 실질 버프 (너프에도 순상승)",
        "PLACEBO_BUFF": "플라시보 버프 (실전 +1% 미만)",
        "PAPER_TIGER_NERF": "종이호랑이 너프 (1% 미만 손실)",
        "CONFIRMED_POWER_SPIKE": "검증된 파워 스파이크",
        "CONFIRMED_HEAVY_NERF": "검증된 대형 너프",
        "VERIFIED_BUFF": "검증된 순수 버프",
        "VERIFIED_NERF": "검증된 순수 너프",
        "NEUTRAL_ADJUSTMENT": "중립적 조정",
    },
    "zh-TW": {
        "MODE_SPECIFIC_TRAP": "其他模式專屬調整 (對峽谷無影響)",
        "TRAP_BUFF_NET_NERF": "陷阱強化 (生態系淨削弱)",
        "HIDDEN_NET_BUFF": "隱藏淨強化 (削弱後仍提升)",
        "PLACEBO_BUFF": "安慰劑強化 (< +1% 實戰影響)",
        "PAPER_TIGER_NERF": "紙老虎削弱 (< 1% 連招損失)",
        "CONFIRMED_POWER_SPIKE": "確認強勢期躍升",
        "CONFIRMED_HEAVY_NERF": "確認重度削弱",
        "VERIFIED_BUFF": "已驗證淨強化",
        "VERIFIED_NERF": "已驗證淨削弱",
        "NEUTRAL_ADJUSTMENT": "中性調整",
    },
    "th": {
        "MODE_SPECIFIC_TRAP": "ปรับเฉพาะโหมดอื่น (ไม่กระทบ SR)",
        "TRAP_BUFF_NET_NERF": "บัฟหลอก (สุทธิอ่อนแอลง)",
        "HIDDEN_NET_BUFF": "บัฟแฝงสุทธิ (แม้โดนเนิร์ฟ)",
        "PLACEBO_BUFF": "บัฟจางมาก (ผลลัพธ์ < +1%)",
        "PAPER_TIGER_NERF": "เนิร์ฟแค่บนกระดาษ (ลด < 1%)",
        "CONFIRMED_POWER_SPIKE": "ยืนยันพลังพุ่งสูงขึ้น",
        "CONFIRMED_HEAVY_NERF": "ยืนยันเนิร์ฟหนัก",
        "VERIFIED_BUFF": "ยืนยันบัฟจริง",
        "VERIFIED_NERF": "ยืนยันเนิร์ฟจริง",
        "NEUTRAL_ADJUSTMENT": "ปรับสมดุลกลาง",
    },
    "vi": {
        "MODE_SPECIFIC_TRAP": "Chỉnh sửa riêng cho chế độ khác",
        "TRAP_BUFF_NET_NERF": "Buff Bẫy (Giảm sức mạnh ròng)",
        "HIDDEN_NET_BUFF": "Buff Ngầm Thực Tế (Dù bị Nerf)",
        "PLACEBO_BUFF": "Buff Tượng Trưng (< +1% Thực Chiến)",
        "PAPER_TIGER_NERF": "Nerf Trên Giấy (< 1% Tổn Thất)",
        "CONFIRMED_POWER_SPIKE": "Xác Nhận Đột Biến Sức Mạnh",
        "CONFIRMED_HEAVY_NERF": "Xác Nhận Giảm Sức Mạnh Nặng",
        "VERIFIED_BUFF": "Xác Nhận Tăng Sức Mạnh",
        "VERIFIED_NERF": "Xác Nhận Giảm Sức Mạnh",
        "NEUTRAL_ADJUSTMENT": "Điều Chỉnh Cân Bằng",
    },
    "id": {
        "MODE_SPECIFIC_TRAP": "Khusus Mode Lain (Tanpa Efek SR)",
        "TRAP_BUFF_NET_NERF": "Buff Jebakan (Net Ekosistem Nerf)",
        "HIDDEN_NET_BUFF": "Buff Tersembunyi (Meski Kena Nerf)",
        "PLACEBO_BUFF": "Buff Plasebo (< +1% Dampak Nyata)",
        "PAPER_TIGER_NERF": "Nerf di Atas Kertas (< 1% Rugi)",
        "CONFIRMED_POWER_SPIKE": "Lonjakan Kekuatan Terkonfirmasi",
        "CONFIRMED_HEAVY_NERF": "Nerf Berat Terkonfirmasi",
        "VERIFIED_BUFF": "Buff Bersih Terverifikasi",
        "VERIFIED_NERF": "Nerf Bersih Terverifikasi",
        "NEUTRAL_ADJUSTMENT": "Penyesuaian Netral",
    },
}

ZERO_DAY_SHARE_I18N: Dict[str, Dict[str, str]] = {
    "tr": {
        "headline": "LoL {patch} — 0. Dakika Meta Kâhini & Yama Efsane Çürütücü",
        "subtitle": "Maç verisi oluşmadan {count} şampiyonun deterministik taraması ({from_patch} → {patch})",
    },
    "en": {
        "headline": "LoL {patch} — Zero-Day Meta Oracle & Patch Mythbuster",
        "subtitle": "Deterministic scan of {count} champions ({from_patch} → {patch}) before Day-1 match data",
    },
    "de": {
        "headline": "LoL {patch} — Zero-Day Meta-Orakel & Patch-Mythbuster",
        "subtitle": "Deterministischer Scan von {count} Champions ({from_patch} → {patch}) ab Minute Null",
    },
    "es": {
        "headline": "LoL {patch} — Oráculo Meta Día Cero y Cazador de Mitos",
        "subtitle": "Análisis determinista de {count} campeones ({from_patch} → {patch}) desde el minuto cero",
    },
    "fr": {
        "headline": "LoL {patch} — Oracle Méta Jour Zéro & Mythbuster",
        "subtitle": "Analyse déterministe de {count} champions ({from_patch} → {patch}) dès la sortie du patch",
    },
    "it": {
        "headline": "LoL {patch} — Oracolo Meta Giorno Zero & Mythbuster",
        "subtitle": "Scansione deterministica di {count} campioni ({from_patch} → {patch}) al minuto zero",
    },
    "pt": {
        "headline": "LoL {patch} — Oráculo Meta Dia Zero & Caça-Mitos",
        "subtitle": "Varredura determinística de {count} campeões ({from_patch} → {patch}) antes dos primeiros jogos",
    },
    "pl": {
        "headline": "LoL {patch} — Wyrocznia Meta Dnia Zero & Pogromca Mitów",
        "subtitle": "Deterministyczny skan {count} bohaterów ({from_patch} → {patch}) w zerowej minucie patcha",
    },
    "ru": {
        "headline": "LoL {patch} — Мета-оракул нулевого дня и разрушитель мифов",
        "subtitle": "Детерминированный расчёт {count} чемпионов ({from_patch} → {patch}) до выхода статистики матчей",
    },
    "cs": {
        "headline": "LoL {patch} — Meta Orákulum Dne Nula & Bořič Mýtů",
        "subtitle": "Deterministický sken {count} šampionů ({from_patch} → {patch}) před prvními daty ze zápasů",
    },
    "el": {
        "headline": "LoL {patch} — Μαντείο Meta Ημέρας Μηδέν & Mythbuster",
        "subtitle": "Μαθηματική σάρωση {count} ηρώων ({from_patch} → {patch}) πριν τα πρώτα στατιστικά",
    },
    "hu": {
        "headline": "LoL {patch} — Nulladik Napi Meta Jós & Mítoszromboló",
        "subtitle": "{count} hős determinisztikus elemzése ({from_patch} → {patch}) meccsadatok előtt",
    },
    "ro": {
        "headline": "LoL {patch} — Oracol Meta Ziua Zero & Mythbuster",
        "subtitle": "Scanare deterministă pentru {count} campioni ({from_patch} → {patch}) înainte de datele live",
    },
    "ar": {
        "headline": "LoL {patch} — عرّاف الميتا في الدقيقة الصفر وكاشف الأساطير",
        "subtitle": "فحص حسابي حتمي لـ {count} بطل ({from_patch} → {patch}) قبل صدور إحصائيات المباريات",
    },
    "ja": {
        "headline": "LoL {patch} — ゼロデイ・メタ予言者 & パッチ神話検証",
        "subtitle": "試合統計が出る前に全 {count} チャンピオン ({from_patch} → {patch}) を数理スキャン",
    },
    "ko": {
        "headline": "LoL {patch} — 0분 차 메타 예언자 & 패치 팩트체커",
        "subtitle": "전적 데이터 집계 전 챔피언 {count}명 ({from_patch} → {patch}) 수학적 전수 스캔",
    },
    "zh-TW": {
        "headline": "LoL {patch} — 零時差 Meta 先知 & 更新謠言終結者",
        "subtitle": "於對戰統計生成前完成 {count} 位英雄 ({from_patch} → {patch}) 的確定性數學掃描",
    },
    "th": {
        "headline": "LoL {patch} — พยากรณ์เมต้านาทีที่ศูนย์ & จับผิดแพตช์",
        "subtitle": "สแกนคณิตศาสตร์ {count} แชมเปี้ยน ({from_patch} → {patch}) ก่อนมีสถิติจริง",
    },
    "vi": {
        "headline": "LoL {patch} — Nhà Tiên Tri Meta Phút 0 & Giải Mã Bản Vá",
        "subtitle": "Quét toán học toàn bộ {count} tướng ({from_patch} → {patch}) trước khi có dữ liệu trận đấu",
    },
    "id": {
        "headline": "LoL {patch} — Peramal Meta Hari-0 & Pembongkar Mitos Patch",
        "subtitle": "Pemindaian deterministik {count} champion ({from_patch} → {patch}) sebelum data pertandingan tersedia",
    },
}

ZERO_DAY_SUMMARY_TR: Dict[str, str] = {
    "MODE_SPECIFIC_TRAP": "Resmi değişiklik yalnızca yan modda (ör. Arena); bu haritadaki net etki {score:+.2f}%.",
    "TRAP_BUFF_NET_NERF": "Tuzak Buff: Şampiyon güçlendirilmiş görünse de çekirdek eşya/rün kayıplarıyla net gücü {score:+.2f}% düştü.",
    "HIDDEN_NET_BUFF": "Gizli Net Güçlenme: Zayıflatılmış görünse de eşya/ekosistem artışıyla net gücü {score:+.2f}% oldu.",
    "PLACEBO_BUFF": "Plasebo Buff: Kâğıt üzerinde buff sayılıyor ancak tam dizilimde etkisi yalnızca {score:+.2f}%.",
    "PAPER_TIGER_NERF": "Kâğıt Üstü Nerf: Korkutucu görünse de tam kombo/DPS üzerindeki gerçek kaybı yalnızca {score:+.2f}%.",
    "CONFIRMED_POWER_SPIKE": "Doğrulanmış Güç Patlaması: Tam dizilim simülasyonunda {score:+.2f}% net güç artışı.",
    "CONFIRMED_HEAVY_NERF": "Doğrulanmış Ağır Nerf: Tam dizilim simülasyonunda {score:+.2f}% belirgin güç düşüşü.",
    "VERIFIED_BUFF": "Doğrulanmış Net Buff: Ölçülebilir {score:+.2f}% gerçek çatışma artışı.",
    "VERIFIED_NERF": "Doğrulanmış Net Nerf: Ölçülebilir {score:+.2f}% gerçek çatışma düşüşü.",
    "NEUTRAL_ADJUSTMENT": "Dengeli / Nötr Düzenleme: Gerçek çatışma değişimi {score:+.2f}%.",
}


def localize_zero_day_radar(
    radar: Dict[str, Any],
    lang: Optional[str],
    version: Optional[str] = None,
) -> Dict[str, Any]:
    """Translates Zero-Day Meta Oracle buckets, verdicts, items, runes, and share card across all 25 LoL locales."""
    riot_locale, bkey, _ = normalize_locale(lang)
    out = copy.deepcopy(radar)

    ver = version or out.get("to_version")
    loc = get_ddragon_localization(ver, riot_locale) or {}
    champs_map = loc.get("champions") or {}
    items_map = loc.get("items") or {}
    runes_map = loc.get("runes") or {}
    rune_ids_map = loc.get("rune_ids") or {}

    verdict_bundle = ZERO_DAY_VERDICT_LABELS.get(bkey, ZERO_DAY_VERDICT_LABELS["en"])
    role_bundle = ROLE_LABELS_I18N.get(bkey, ROLE_LABELS_I18N["en"])
    share_bundle = ZERO_DAY_SHARE_I18N.get(bkey, ZERO_DAY_SHARE_I18N["en"])

    def _loc_entry(entry: Optional[Dict[str, Any]]) -> None:
        if not isinstance(entry, dict):
            return
        ckey = entry.get("champion_key")
        if ckey and ckey in champs_map:
            entry["champion_name"] = champs_map[ckey].get("name", entry.get("champion_name"))

        rkey = str(entry.get("role") or "")
        if rkey in role_bundle:
            entry["role_label"] = role_bundle[rkey]

        ka = entry.get("kit_archetype_label")
        if isinstance(ka, str):
            if bkey == "tr":
                entry["kit_archetype_label"] = KIT_ARCHETYPE_TR.get(ka, ka)
            else:
                entry["kit_archetype_label"] = KIT_ARCHETYPE_EN.get(ka, ka)

        for it in entry.get("core_items") or []:
            iid = str(it.get("item_id") or "")
            if iid in items_map:
                it["name"] = items_map[iid]

        for cat in entry.get("catalysts") or []:
            ctype = cat.get("entity_type")
            ekey = str(cat.get("entity_key") or "")
            if ctype == "item" and ekey in items_map:
                cat["entity_name"] = items_map[ekey]
            elif ctype == "rune":
                if ekey in runes_map:
                    cat["entity_name"] = runes_map[ekey]
                elif ekey in rune_ids_map:
                    cat["entity_name"] = rune_ids_map[ekey]

        vcode = entry.get("verdict_code")
        if isinstance(vcode, str) and vcode in verdict_bundle:
            entry["verdict_label"] = verdict_bundle[vcode]
            score = float(entry.get("power_shift_score", 0.0))
            if bkey == "tr" and vcode in ZERO_DAY_SUMMARY_TR:
                entry["verdict_summary"] = ZERO_DAY_SUMMARY_TR[vcode].format(score=score)
            elif bkey != "en":
                entry["verdict_summary"] = f"{verdict_bundle[vcode]} ({score:+.2f}%)"

    for bucket_key in ("hidden_winners", "hidden_losers", "mythbusters", "top_winners", "top_losers"):
        for item in out.get(bucket_key) or []:
            _loc_entry(item)

    out["map_label"] = MAP_LABELS_I18N.get(bkey, MAP_LABELS_I18N["en"]).get(
        str(out.get("game_map") or "sr"), out.get("map_label")
    )
    out["target_label"] = localize_target_label(out.get("target_profile"), riot_locale)

    sc = out.get("share_card")
    if isinstance(sc, dict):
        to_disp = str(out.get("to_display_version") or out.get("to_version") or "")
        from_disp = str(out.get("from_display_version") or out.get("from_version") or "")
        count = int(out.get("champions_scanned") or 0)
        sc["headline"] = share_bundle["headline"].format(patch=to_disp)
        sc["subtitle"] = share_bundle["subtitle"].format(
            patch=to_disp, from_patch=from_disp, count=count
        )
        _loc_entry(sc.get("top_winner"))
        _loc_entry(sc.get("top_hidden_mover"))
        _loc_entry(sc.get("top_myth"))

    return out
