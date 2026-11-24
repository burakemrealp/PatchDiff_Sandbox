import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.database import Base, get_db
from app.main import app
from app.models.entities import ChampionSnapshot, ItemSnapshot, PatchVersion
from app.seed_data import CHAMPION_SEED_DATA


@pytest.fixture()
def rec_client(monkeypatch):
    monkeypatch.setattr(settings, "AUTO_SYNC_ENABLED", False)
    monkeypatch.setattr(settings, "LLM_PROVIDER", "offline")

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine)

    db = TestingSession()
    ahri = CHAMPION_SEED_DATA["Ahri"]
    db.add_all(
        [
            PatchVersion(version="16.22.1", is_latest=False, sync_status="synced"),
            PatchVersion(
                version="16.23.1", previous_version="16.22.1", is_latest=True, sync_status="synced"
            ),
            ChampionSnapshot(
                patch_version="16.22.1",
                champion_key="Ahri",
                name="Ahri",
                tags=["Mage", "Assassin"],
                partype="Mana",
                base_stats=ahri["base_stats"],
                abilities=ahri["abilities"],
            ),
            ChampionSnapshot(
                patch_version="16.23.1",
                champion_key="Ahri",
                name="Ahri",
                tags=["Mage", "Assassin"],
                partype="Mana",
                base_stats=ahri["base_stats"],
                abilities=ahri["abilities"],
            ),
        ]
    )

    items_seed = [
        ("3089", "Rabadon'un Şapkası", 3500, {"ap": 130.0, "ap_multiplier": 0.30}, []),
        ("4645", "Gölgealev", 3200, {"ap": 110.0, "magic_pen_flat": 15.0}, []),
        ("3135", "Hiçlik Değneği", 3000, {"ap": 95.0, "magic_pen_percent": 0.40}, ["MagicPenPercent"]),
        ("6655", "Luden'in Feryadı", 2750, {"ap": 100.0, "mana": 600.0, "ability_haste": 10.0}, []),
        ("3157", "Zhonya'nın Kumsaati", 3250, {"ap": 105.0, "armor": 50.0}, []),
    ]
    for ver in ("16.22.1", "16.23.1"):
        for iid, name, gold, stats, ugroups in items_seed:
            db.add(
                ItemSnapshot(
                    patch_version=ver,
                    item_id=iid,
                    name=name,
                    gold_total=gold,
                    is_completed=True,
                    stats=stats,
                    tags=["SpellDamage"],
                    unique_groups=ugroups,
                )
            )
    db.commit()
    db.close()

    def _override_db():
        s = TestingSession()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = _override_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
    engine.dispose()


def test_recommend_builds_endpoint_and_redis_cache_roundtrip(rec_client, monkeypatch):
    fake_cache = {}
    monkeypatch.setattr("app.api.routes.redis_client.get", lambda k: fake_cache.get(k))
    monkeypatch.setattr("app.api.routes.redis_client.setex", lambda k, ttl, v: fake_cache.__setitem__(k, v))

    # 1. First call: live calculation + AI advisor review
    r1 = rec_client.post(
        "/api/v1/recommend-builds",
        json={"champion_key": "Ahri", "target_profile": "squishy", "use_ai": True},
    )
    assert r1.status_code == 200
    b1 = r1.json()
    assert b1["cached"] is False
    assert b1["engine_used"] == "deterministic-advisor"
    assert len(b1["report"]["variations"]) == 3
    assert b1["report"]["variations"][0]["ai_review"]["practicality_score"] >= 1

    # 2. Second call: Redis cache HIT
    r2 = rec_client.post(
        "/api/v1/recommend-builds",
        json={"champion_key": "Ahri", "target_profile": "squishy", "use_ai": True},
    )
    assert r2.status_code == 200
    assert r2.json()["cached"] is True

    # 3. Unknown champion: HTTP 404
    r404 = rec_client.post(
        "/api/v1/recommend-builds",
        json={"champion_key": "UnknownChamp", "target_profile": "squishy"},
    )
    assert r404.status_code == 404
