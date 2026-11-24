from app.services.readable_formatter import (
    format_field_label,
    format_readable_value_series,
    format_spell_label,
    format_stat_label,
    split_camel_case,
)


def test_format_stat_label_known_and_fallback():
    assert format_stat_label("attack_range") == "Saldırı Menzili"
    assert format_stat_label("base_hp") == "Taban Can"
    assert format_stat_label("base_ad") == "Taban Saldırı Gücü (AD)"
    assert format_stat_label("custom_stat_value") == "custom stat value"


def test_split_camel_case_and_field_label():
    assert split_camel_case("AuraDamage") == "Aura Damage"
    assert split_camel_case("TibbersTotalHP") == "Tibbers Total HP"
    assert format_field_label("AuraDamage") == "Alan (Aura) Hasarı"
    assert format_field_label("OnHitMultiplier") == "İsabet Etkisi (On-Hit) Çarpanı"
    assert format_field_label("PercentCurrentHPMelee") == "Yakın Dövüş Mevcut Can Hasarı"
    assert format_field_label("APRatioSubsuquent") == "Sonraki Vuruş AP Oranı"
    # Generic CamelCase + word translation fallback for unknown future patch fields
    assert format_field_label("BonusShieldDuration") == "İlave Kalkan Süresi"


def test_format_spell_label():
    abilities = {
        "Q": {"name": "Cosmic Binding"},
        "W": {"name": "Arise!"},
        "R": {"name": "Summon: Tibbers"},
    }
    assert format_spell_label("Annie", "AnnieR", abilities) == "Annie R — Summon: Tibbers"
    assert format_spell_label("Azir", "AzirW", abilities) == "Azir W — Arise!"
    assert format_spell_label("Gnar", "GnarBigQ", {"Q": {"name": "Boomerang Throw / Boulder Toss"}}) == (
        "Gnar Mega Q — Boomerang Throw / Boulder Toss"
    )
    assert format_spell_label("Yorick", "YorickPassive", {}) == "Yorick Pasif"
    # Regular ability names ending with lowercase 'p' must not be misclassified as Passive
    assert format_spell_label("Tristana", "RocketJump", {}) != "Tristana Pasif"


def test_format_readable_value_series():
    assert format_readable_value_series("OnHitMultiplier", [0.5], [0.67]) == ("%50", "%67")
    assert format_readable_value_series("PercentCurrentHPMelee", [9.0], [8.0]) == ("%9", "%8")
    assert format_readable_value_series("AuraDamage", [8.0, 12.0, 16.0], [10.0, 15.0, 20.0]) == (
        "8/12/16",
        "10/15/20",
    )
    assert format_readable_value_series("RDamageIncreaseMax", [0.8], [0.75]) == ("%80", "%75")
