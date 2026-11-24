import re
from typing import Any, Dict, List, Optional, Tuple

# Turkish (`tr_TR`) stat labels used as default human-readable diff labels paired with locale_service.py
STAT_LABELS_TR: Dict[str, str] = {
    "base_hp": "Taban Can",
    "hp_growth": "Seviye Başı Can",
    "base_mp": "Taban Mana",
    "mp_growth": "Seviye Başı Mana",
    "base_ad": "Taban Saldırı Gücü (AD)",
    "ad_growth": "Seviye Başı Saldırı Gücü",
    "base_armor": "Taban Zırh",
    "armor_growth": "Seviye Başı Zırh",
    "base_mr": "Taban Büyü Direnci (MR)",
    "mr_growth": "Seviye Başı Büyü Direnci",
    "base_attack_speed": "Taban Saldırı Hızı",
    "attack_speed_growth": "Seviye Başı Saldırı Hızı",
    "attack_range": "Saldırı Menzili",
    "move_speed": "Hareket Hızı",
    "base_hp_regen": "Taban Can Yenileme",
    "hp_regen_growth": "Seviye Başı Can Yenileme",
    "base_mp_regen": "Taban Mana Yenileme",
    "mp_regen_growth": "Seviye Başı Mana Yenileme",
}

# Player-friendly Turkish (`tr_TR`) labels for common Riot CDragon DataValues / calculation field names
KNOWN_FIELD_LABELS_TR: Dict[str, str] = {
    "basedamage": "Taban Hasar",
    "basedamageinitial": "İlk Vuruş Taban Hasarı",
    "basedamagesubsequent": "Sonraki Vuruş Taban Hasarı",
    "totaldamage": "Toplam Hasar",
    "damage": "Hasar",
    "calculateddamage": "Hesaplanan Hasar",
    "rcalculateddamage": "Ulti Toplam Hasarı",
    "minitotaldamage": "Mini Form Toplam Hasarı",
    "megatotaldamage": "Mega Form Toplam Hasarı",
    "auradamage": "Alan (Aura) Hasarı",
    "tibberstotalhp": "Tibbers Toplam Canı",
    "tibbershp": "Tibbers Canı",
    "tibbersattackdamage": "Tibbers Saldırı Gücü",
    "shieldpercent": "Kalkan Oranı",
    "shieldratio": "Kalkan Oranı",
    "baseshield": "Taban Kalkan",
    "shieldamount": "Kalkan Miktarı",
    "apratio": "Yetenek Gücü (AP) Oranı",
    "apratiosubsequent": "Sonraki Vuruş AP Oranı",
    "apratiosubsuquent": "Sonraki Vuruş AP Oranı",
    "rapratio": "Ulti AP Oranı",
    "rapcoefficient": "Ulti AP Oranı",
    "adratio": "Saldırı Gücü (AD) Oranı",
    "attackdamageratio": "Saldırı Gücü (AD) Oranı",
    "bonusadratio": "İlave Saldırı Gücü Oranı",
    "totaladratio": "Toplam Saldırı Gücü Oranı",
    "armorratio": "Zırh Oranı",
    "mrratio": "Büyü Direnci Oranı",
    "soldierratio": "Asker Saldırı Oranı",
    "onhitmultiplier": "İsabet Etkisi (On-Hit) Çarpanı",
    "rdamageincreasemax": "Ulti Maksimum Hasar Artışı",
    "percentcurrenthpmelee": "Yakın Dövüş Mevcut Can Hasarı",
    "percentcurrenthpranged": "Menzilli Mevcut Can Hasarı",
    "damagebase": "Taban Hasar",
    "damagemax": "Maksimum Hasar",
    "cooldown": "Bekleme Süresi",
    "cooldownmin": "En Düşük Bekleme Süresi",
}

# Fallback word-by-word Turkish dictionary for splitting unknown future CamelCase Riot parameters
WORD_TRANSLATIONS: Dict[str, str] = {
    "Base": "Taban",
    "Total": "Toplam",
    "Bonus": "İlave",
    "Damage": "Hasar",
    "Aura": "Alan (Aura)",
    "Shield": "Kalkan",
    "Heal": "İyileştirme",
    "Health": "Can",
    "HP": "Can",
    "Mana": "Mana",
    "Cost": "Maliyeti",
    "Cooldown": "Bekleme Süresi",
    "Duration": "Süresi",
    "Slow": "Yavaşlatma",
    "Stun": "Sersemletme",
    "Ratio": "Oranı",
    "Percent": "Yüzdesi",
    "Range": "Menzili",
    "Speed": "Hızı",
    "Attack": "Saldırı",
    "Melee": "Yakın Dövüş",
    "Ranged": "Menzilli",
    "Current": "Mevcut",
    "Max": "Maksimum",
    "Min": "Minimum",
    "Mini": "Mini Form",
    "Mega": "Mega Form",
    "Passive": "Pasif",
    "Armor": "Zırh",
    "Magic": "Büyü",
    "Resist": "Direnci",
    "Mod": "Çarpanı",
    "Mult": "Çarpanı",
    "Multiplier": "Çarpanı",
    "Per": "Başına",
    "Level": "Seviye",
    "Rank": "Kademe",
    "Cap": "Sınırı",
    "Threshold": "Eşiği",
    "Crit": "Kritik",
    "Initial": "İlk Vuruş",
    "Subsequent": "Sonraki Vuruş",
    "Subsuquent": "Sonraki Vuruş",
    "Increase": "Artışı",
    "Decrease": "Azalması",
    "Reduction": "Azaltması",
    "Ghoul": "Hortlak",
    "Cherry": "Arena Modu",
    "On": "İsabet",
    "Hit": "Etkisi",
}


def format_stat_label(stat_key: str) -> str:
    """Returns the Turkish default readable stat label for database diff snapshots."""
    return STAT_LABELS_TR.get(stat_key, split_camel_case(stat_key))


def split_camel_case(raw: str) -> str:
    """Splits CamelCase/snake_case tokens cleanly: 'AuraDamage' -> 'Aura Damage'."""
    if not raw:
        return ""
    text = raw.replace("_", " ").strip()
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", text)
    return re.sub(r"\s+", " ", text).strip()


def format_field_label(field_name: str) -> str:
    """Formats raw Riot CDragon parameter keys into player-friendly Turkish diff labels."""
    if not field_name:
        return ""
    norm = re.sub(r"[^a-z0-9]", "", field_name.lower())
    if norm in KNOWN_FIELD_LABELS_TR:
        return KNOWN_FIELD_LABELS_TR[norm]

    words = split_camel_case(field_name).split()
    # Strip leading single-letter Riot Hungarian prefixes such as 'm'
    if len(words) > 1 and words[0] in ("m", "M"):
        words = words[1:]

    translated = [WORD_TRANSLATIONS.get(w, w) for w in words]
    return " ".join(translated)


def format_spell_label(
    champion_name: str,
    spell_name: str,
    abilities: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Formats internal Riot spell identifiers into clean headings:
    'AnnieR' -> 'Annie R — Summon: Tibbers'
    'GnarBigQ' -> 'Gnar Mega Q — Boulder Toss'
    'YorickPassive' -> 'Yorick Pasif'
    'AlphaStrike' -> 'Master Yi Q — Alpha Strike'
    """
    abilities = abilities or {}
    sl = spell_name.lower()

    # 1. Passive check (match explicit 'passive' token or uppercase trailing 'P' only)
    if "passive" in sl or re.search(r"[a-z]P$", spell_name):
        return f"{champion_name} Pasif"

    # 2. Match against Q/W/E/R ability names in champion ability dictionary
    matched_slot: Optional[str] = None
    matched_ab_name: Optional[str] = None

    for slot in ("Q", "W", "E", "R"):
        ab = abilities.get(slot)
        if not isinstance(ab, dict):
            continue
        ab_name = str(ab.get("name") or "")
        ab_clean = re.sub(r"[^a-z0-9]", "", ab_name.lower())
        sp_clean = re.sub(r"[^a-z0-9]", "", sl)
        if ab_clean and (ab_clean == sp_clean or sp_clean.endswith(ab_clean)):
            matched_slot = slot
            matched_ab_name = ab_name
            break

    # 3. Trailing slot + optional alternate form prefix check (e.g., AnnieR, GalioW, GnarBigQ)
    form_prefix = ""
    if not matched_slot:
        m = re.search(r"(big|mega|mini|cougar|spider|hammer|cannon|allout)?([qwer])$", sl)
        if m:
            raw_form = m.group(1) or ""
            matched_slot = m.group(2).upper()
            if raw_form in ("big", "mega"):
                form_prefix = "Mega "
            elif raw_form == "mini":
                form_prefix = "Mini "
            elif raw_form == "allout":
                form_prefix = "All Out "
            elif raw_form:
                form_prefix = f"{raw_form.capitalize()} "

            ab = abilities.get(matched_slot)
            if isinstance(ab, dict) and ab.get("name"):
                matched_ab_name = str(ab["name"])

    if matched_slot:
        # Avoid redundant internal names like 'Annie R — AnnieR'
        if matched_ab_name and matched_ab_name.lower() != sl and not re.match(
            r"^[a-z]+[qwer]$", matched_ab_name.lower()
        ):
            return f"{champion_name} {form_prefix}{matched_slot} — {matched_ab_name}"
        return f"{champion_name} {form_prefix}{matched_slot}"

    # 4. Fallback to clean CamelCase splitting
    readable = split_camel_case(spell_name)
    if readable.lower().startswith(champion_name.lower()):
        return readable
    return f"{champion_name} — {readable}"


def format_readable_value_series(
    field_name: str, old_vals: List[float], new_vals: List[float]
) -> Tuple[str, str]:
    """
    Formats numeric series into compact human-readable strings:
    - Ratio/percent decimals (0.5 -> 0.67) display as '%50' -> '%67' (localized downstream for non-TR).
    - Fields already stored as percentage values (e.g., 9.0 -> 8.0) display as '%9' -> '%8'.
    - Integers drop unnecessary '.0' suffixes.
    """
    fl = field_name.lower()
    is_ratio = any(tok in fl for tok in ("ratio", "coeff", "mod", "mult", "increase", "reduction"))
    is_percent = "percent" in fl or "pct" in fl
    max_val = max([abs(x) for x in (old_vals + new_vals)] or [0.0])
    scale_to_pct = (is_ratio or is_percent) and 0.0 < max_val <= 3.0
    already_pct = is_percent and max_val > 3.0

    def _fmt_num(val: float) -> str:
        rv = round(val, 2)
        return str(int(rv) if rv == int(rv) else rv)

    def _fmt_list(vals: List[float]) -> str:
        if not vals:
            return "-"
        compact = [vals[0]] if len(set(vals)) == 1 else vals
        parts: List[str] = []
        for v in compact:
            if scale_to_pct:
                pct = round(v * 100.0, 1)
                parts.append(f"%{int(pct) if pct == int(pct) else pct}")
            elif already_pct:
                parts.append(f"%{_fmt_num(v)}")
            else:
                parts.append(_fmt_num(v))
        return "/".join(parts)

    return _fmt_list(old_vals), _fmt_list(new_vals)
