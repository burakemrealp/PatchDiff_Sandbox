from app.services.locale_service import (
    SUPPORTED_LOCALES,
    localize_diff_payload,
    localize_game_context,
    localize_target_label,
    normalize_locale,
)


def test_supported_locales_match_all_25_official_lol_web_locales():
    assert len(SUPPORTED_LOCALES) == 25
    for code in ("tr_TR", "en_US", "en_GB", "de_DE", "es_MX", "fr_FR", "ja_JP", "ko_KR", "ar_AE", "zh_TW"):
        assert code in SUPPORTED_LOCALES


def test_normalize_locale_handles_web_and_riot_formats():
    assert normalize_locale("en-us") == ("en_US", "en", "English")
    assert normalize_locale("ja_JP") == ("ja_JP", "ja", "Japanese")
    assert normalize_locale("ar-ae") == ("ar_AE", "ar", "Arabic")
    assert normalize_locale("unknown_XX") == ("tr_TR", "tr", "Turkish")


def test_localize_game_context_and_target_labels():
    gc_tr = {
        "role": "mid",
        "role_label": "Orta Koridor (Mid)",
        "game_map": "sr",
        "map_label": "Sihirdar Vadisi (5v5)",
        "role_quests_enabled": True,
        "quest_reward": "Ücretsiz 3. Aşama Ayakkabı",
    }
    gc_de = localize_game_context(gc_tr, "de_DE")
    assert gc_de["role_label"] == "Mid-Lane"
    assert gc_de["map_label"] == "Kluft der Beschwörer (5v5)"
    assert "Tier 3 Boots" in gc_de["quest_reward"]

    gc_en = {"role": "mid", "role_label": "Mid Lane", "game_map": "sr", "map_label": "Summoner's Rift (5v5)", "role_quests_enabled": True}
    gc_back_tr = localize_game_context(gc_en, "tr_TR")
    assert gc_back_tr["role_label"] == "Orta Koridor (Mid)"
    assert gc_back_tr["map_label"] == "Sihirdar Vadisi (5v5)"

    assert localize_target_label("tank", "ko_KR") == "하드 탱커"
    assert localize_target_label("squishy", "ja_JP") == "柔らかい敵"
    assert localize_target_label("bruiser", "ar_AE") == "مقاتل"


def test_localize_diff_payload_for_non_turkish():
    champ_diff = {
        "stat_deltas": [{"stat_name": "attack_range", "stat_label": "Saldırı Menzili"}],
        "mechanic_deltas": [
            {
                "spell_name": "YorickPassive",
                "spell_label": "Yorick Pasif",
                "field_name": "OnHitMultiplier",
                "field_label": "İsabet Etkisi Çarpanı",
                "display_old": "%50",
                "display_new": "%67",
            }
        ],
    }
    en_diff = localize_diff_payload("champion", champ_diff, "en_US")
    assert en_diff["stat_deltas"][0]["stat_label"] == "Attack Range"
    assert en_diff["mechanic_deltas"][0]["spell_label"] == "Yorick Passive"
    assert en_diff["mechanic_deltas"][0]["field_label"] == "On Hit Multiplier"
    assert en_diff["mechanic_deltas"][0]["display_old"] == "50%"
    assert en_diff["mechanic_deltas"][0]["display_new"] == "67%"
