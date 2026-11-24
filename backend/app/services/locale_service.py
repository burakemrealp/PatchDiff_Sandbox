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
