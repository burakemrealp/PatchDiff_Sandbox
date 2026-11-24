from app.core.config import settings
from app.schemas.patch_contracts import (
    AbilityDelta,
    AbilitySlot,
    ChampionPatchDiff,
    ChangeDirection,
    DamageType,
    PatchPayload,
    ScalingDelta,
    ScalingStat,
    StatDelta,
    StatName,
)
from app.services.llm_extractor import PatchExtractorService
from app.services.normalizer import PatchNormalizer
from app.services.sanity_checker import PatchSanityChecker

# Sample Turkish HTML patch note fixture testing HTML tag, arrow, and decimal comma normalization
MESSY_PATCH_INPUT = """
<div class="patch-notes">
  <h2>Yama 14.23 Şampiyon Değişiklikleri</h2>
  <h3>Ahri - Dokuz Kuyruklu Tilki</h3>
  <p>Ahri erken koridor aşamasında fazla güvenliydi, zırhını düşürüp geç oyun hasarını artırıyoruz.</p>
  <ul>
    <li><strong>Taban Zırh:</strong> 21 ⇒ 18</li>
    <li><strong>Q - Aldatıcı Küre:</strong> Taban Hasar: 80/130/180/230/280 ➔ 90/145/200/255/310</li>
    <li><strong>Q - Aldatıcı Küre:</strong> Yetenek Gücü (AP) Oranı: %90 ==> %105 (0,90 ⇒ 1,05)</li>
    <li><strong>Q - Bekleme Süresi:</strong> 7 saniye -> 6,5 saniye</li>
  </ul>

  <h3>Zed</h3>
  <ul>
    <li>Taban Saldırı Gücü: 63 ⇒ 60</li>
    <li>Q - Keskin Shuriken İlave SG Oranı: %110 ➔ %125</li>
  </ul>
</div>
"""


def test_stat_delta_auto_direction_and_percent():
    nerf = StatDelta(stat_name=StatName.BASE_ARMOR, old_value=21.0, new_value=18.0)
    buff = StatDelta(stat_name=StatName.BASE_AD, old_value=60.0, new_value=66.0)
    same = StatDelta(stat_name=StatName.MOVE_SPEED, old_value=330.0, new_value=330.0)

    assert nerf.direction == ChangeDirection.NERF
    assert nerf.delta_percent == -14.29
    assert buff.direction == ChangeDirection.BUFF
    assert buff.delta_percent == 10.0
    assert same.direction == ChangeDirection.ADJUSTMENT


def test_ability_delta_cooldown_reduction_is_buff():
    ab = AbilityDelta(
        slot=AbilitySlot.Q,
        damage_type=DamageType.MAGIC,
        old_cooldown=[7.0] * 5,
        new_cooldown=[6.0] * 5,
    )
    assert ab.direction == ChangeDirection.BUFF


def test_normalizer_cleans_html_arrows_commas_and_splits_champions():
    chunks = PatchNormalizer.split_by_champion(MESSY_PATCH_INPUT)

    assert set(chunks.keys()) == {"Ahri", "Zed"}
    assert "<strong>" not in chunks["Ahri"]
    assert "21 -> 18" in chunks["Ahri"]
    assert "6.5 saniye" in chunks["Ahri"]
    assert "63 -> 60" in chunks["Zed"]


def test_extractor_offline_deterministic_returns_tuple(monkeypatch):
    monkeypatch.setattr(settings, "LLM_PROVIDER", "offline")
    payload, engine_used, latency_ms = PatchExtractorService.extract_patch_payload(
        MESSY_PATCH_INPUT, patch_version="14.23"
    )

    assert engine_used == "deterministic-offline"
    assert latency_ms >= 0.0
    assert payload.patch_version == "14.23"

    ahri = next(c for c in payload.champions if c.champion_key == "Ahri")
    assert ahri.stat_deltas[0].stat_name == StatName.BASE_ARMOR
    assert ahri.stat_deltas[0].new_value == 18.0
    assert len(ahri.ability_deltas) == 1
    assert ahri.ability_deltas[0].slot == AbilitySlot.Q
    assert ahri.ability_deltas[0].new_base_damage == [90.0, 145.0, 200.0, 255.0, 310.0]
    assert ahri.ability_deltas[0].scaling_changes[0].new_ratio == 1.05


def test_sanity_checker_fixes_ratio_units_rank_lengths_and_invalid_stats():
    buggy = PatchPayload(
        patch_version="14.23",
        champions=[
            ChampionPatchDiff(
                champion_key="Ahri",
                stat_deltas=[
                    StatDelta(stat_name=StatName.BASE_ARMOR, old_value=21.0, new_value=-5.0),
                ],
                ability_deltas=[
                    AbilityDelta(
                        slot=AbilitySlot.Q,
                        old_cooldown=[7.0],
                        new_cooldown=[6.5],
                        scaling_changes=[
                            ScalingDelta(
                                scaling_stat=ScalingStat.AP,
                                old_ratio=90.0,
                                new_ratio=105.0,
                            )
                        ],
                    )
                ],
            )
        ],
    )

    clean, warnings = PatchSanityChecker.validate_and_sanitize(buggy)

    assert len(warnings) >= 4
    champ = clean.champions[0]
    assert champ.stat_deltas == []
    ab = champ.ability_deltas[0]
    assert ab.old_cooldown == [7.0] * 5
    assert ab.new_cooldown == [6.5] * 5
    assert ab.scaling_changes[0].old_ratio == 0.90
    assert ab.scaling_changes[0].new_ratio == 1.05
    assert ab.direction == ChangeDirection.BUFF


def test_normalizer_supports_dynamic_champion_dictionary():
    raw = """
    ### Lee Sin
    Taban Saldırı Gücü: 66 -> 69
    ### Aurelion Sol
    Taban Can: 620 -> 600
    """
    dynamic_map = {
        "leesin": "LeeSin",
        "lee sin": "LeeSin",
        "aurelionsol": "AurelionSol",
        "aurelion sol": "AurelionSol",
    }
    chunks = PatchNormalizer.split_by_champion(raw, known_champions=dynamic_map)

    assert set(chunks.keys()) == {"LeeSin", "AurelionSol"}
    assert "66 -> 69" in chunks["LeeSin"]
    assert "620 -> 600" in chunks["AurelionSol"]


def test_global_exception_handler_hides_detail_when_debug_false(monkeypatch):
    import asyncio
    import json
    from starlette.requests import Request
    from app.main import global_exception_handler

    req = Request({"type": "http", "method": "GET", "path": "/boom", "headers": []})

    monkeypatch.setattr(settings, "DEBUG", False)
    resp_prod = asyncio.run(global_exception_handler(req, RuntimeError("secret db password")))
    body_prod = json.loads(resp_prod.body)
    assert resp_prod.status_code == 500
    assert "detail" not in body_prod

    monkeypatch.setattr(settings, "DEBUG", True)
    resp_dev = asyncio.run(global_exception_handler(req, RuntimeError("secret db password")))
    body_dev = json.loads(resp_dev.body)
    assert body_dev["detail"] == "secret db password"
