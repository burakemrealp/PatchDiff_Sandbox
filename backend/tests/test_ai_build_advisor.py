from app.core.config import settings
from app.services.ai_build_advisor import AIBuildAdvisorService


def _sample_report() -> dict:
    return {
        "champion_key": "Velkoz",
        "champion_name": "Vel'Koz",
        "from_version": "16.22.1",
        "to_version": "16.23.1",
        "target_profile": "tank",
        "profile": {"tags": ["Mage", "Support"], "uses_mana": True},
        "champion_changed_in_patch": True,
        "champion_patch_diff": {"summary": "R hasarı güçlendirildi"},
        "old_meta_baseline": {
            "items": [{"item_id": "3135", "name": "Hiçlik Değneği"}],
            "keystone": {"key": "Electrocute", "label": "Elektrik Ver"},
            "total_gold": 9700,
        },
        "variations": [
            {
                "playstyle": "dps",
                "playstyle_label": "Sürekli Hasar (Sustained DPS)",
                "score": 1500.0,
                "total_gold": 9200,
                "items": [
                    {"item_id": "3115", "name": "Nashor'un Dişi", "gold_total": 3000, "stats": {"ap": 90.0}},
                    {"item_id": "3100", "name": "Lich Boğan", "gold_total": 2900, "stats": {"ap": 100.0}},
                    {"item_id": "3089", "name": "Rabadon'un Şapkası", "gold_total": 3300, "stats": {"ap": 130.0}},
                ],
                "keystone": {"key": "Electrocute", "label": "Elektrik Ver", "tree": "Domination"},
                "metrics": {
                    "lvl11_burst": 900.0,
                    "lvl18_burst": 1350.0,
                    "lvl11_dps": 150.0,
                    "lvl18_dps": 210.0,
                    "lvl11_ttk_sec": 12.0,
                    "lvl18_ttk_sec": 18.0,
                    "phys_ehp_lvl11": 2400.0,
                    "magic_ehp_lvl11": 2100.0,
                    "ability_haste": 15.0,
                    "gold_efficiency_index": 200.0,
                },
                "patch_shift": {"status": "STABLE", "lvl18_burst_delta_pct": 0.4, "lvl18_dps_delta_pct": 0.0},
                "vs_old_meta": {"gold_diff": -500, "dps_diff_pct": 12.0, "is_new_meta_discovery": True},
            },
            {
                "playstyle": "balanced",
                "playstyle_label": "Dengeli & Hayatta Kalma (EHP + Tempo)",
                "score": 1400.0,
                "total_gold": 8800,
                "items": [
                    {"item_id": "2503", "name": "Siyahateş Meşalesi", "gold_total": 2800, "stats": {"ap": 80.0, "mana": 600.0, "ability_haste": 20.0}},
                    {"item_id": "3137", "name": "Makber Çiçeği", "gold_total": 2850, "stats": {"ap": 75.0, "ability_haste": 20.0}},
                    {"item_id": "4629", "name": "Kozmik Hızlandırıcı", "gold_total": 3150, "stats": {"ap": 70.0, "hp": 350.0, "ability_haste": 25.0}},
                ],
                "keystone": {"key": "ArcaneComet", "label": "Sihirli Yıldız", "tree": "Sorcery"},
                "metrics": {
                    "lvl11_burst": 820.0,
                    "lvl18_burst": 1150.0,
                    "lvl11_dps": 135.0,
                    "lvl18_dps": 180.0,
                    "lvl11_ttk_sec": 13.0,
                    "lvl18_ttk_sec": 20.0,
                    "phys_ehp_lvl11": 3000.0,
                    "magic_ehp_lvl11": 2600.0,
                    "ability_haste": 65.0,
                    "gold_efficiency_index": 195.0,
                },
                "patch_shift": {"status": "GAINED", "lvl18_burst_delta_pct": 1.1, "lvl18_dps_delta_pct": 0.6},
                "vs_old_meta": {"gold_diff": -900, "dps_diff_pct": 6.1, "is_new_meta_discovery": True},
            },
        ],
    }


def test_deterministic_advisor_penalizes_impractical_mage_aa_build_and_reranks(monkeypatch):
    monkeypatch.setattr(settings, "LLM_PROVIDER", "offline")

    enriched, engine, latency_ms = AIBuildAdvisorService.evaluate_report(_sample_report())

    assert engine == "deterministic-advisor"
    assert latency_ms >= 0.0
    assert enriched["ai_summary"]

    # Balanced mana+haste build should be ranked #1 above risky Nashor+Lich Bane build on Vel'Koz!
    top = enriched["variations"][0]
    second = enriched["variations"][1]

    assert top["playstyle"] == "balanced"
    assert top["rank"] == 1
    assert top["ai_review"]["verdict"] == "RECOMMENDED"
    assert top["ai_review"]["rune_item_synergy"]
    assert "26.23" in enriched["ai_summary"]
    assert top["ai_review"]["practicality_score"] > second["ai_review"]["practicality_score"]
    assert second["playstyle"] == "dps"
    assert second["ai_review"]["verdict"] in {"SITUATIONAL", "RISKY"}
    assert any("Nashor" in w for w in second["ai_review"]["watchouts"])
