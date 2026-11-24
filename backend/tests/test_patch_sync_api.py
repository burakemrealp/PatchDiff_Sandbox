import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.database import Base, get_db
from app.main import app
from app.models.entities import (
    AutoPatchDiff,
    ChampionSnapshot,
    PatchVersion,
)


@pytest.fixture()
def api_client(monkeypatch):
    monkeypatch.setattr(settings, "AUTO_SYNC_ENABLED", False)

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine)

    db = TestingSession()
    db.add_all(
        [
            PatchVersion(
                version="16.22.1",
                is_latest=False,
                sync_status="synced",
                champions_count=173,
                items_count=251,
                runes_count=62,
            ),
            PatchVersion(
                version="16.23.1",
                previous_version="16.22.1",
                is_latest=True,
                sync_status="synced",
                champions_count=173,
                items_count=251,
                runes_count=62,
            ),
            ChampionSnapshot(
                patch_version="16.22.1",
                champion_key="Ahri",
                name="Ahri",
                base_stats={
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
                abilities={
                    "Q": {
                        "name": "AhriQ",
                        "damage_type": "magic",
                        "base_damage": [80.0, 130.0, 180.0, 230.0, 280.0],
                        "cooldown": [7.0, 7.0, 7.0, 7.0, 7.0],
                        "scaling": {"ap": 0.9},
                    }
                },
            ),
            AutoPatchDiff(
                from_version="16.22.1",
                to_version="16.23.1",
                entity_type="champion",
                entity_key="Ahri",
                entity_name="Ahri",
                direction="BUFF",
                diff_payload={
                    "champion_key": "Ahri",
                    "summary": "Q buff",
                    "stat_deltas": [],
                    "ability_deltas": [
                        {
                            "slot": "Q",
                            "ability_name": "AhriQ",
                            "damage_type": "magic",
                            "old_base_damage": [80.0, 130.0, 180.0, 230.0, 280.0],
                            "new_base_damage": [95.0, 145.0, 195.0, 245.0, 295.0],
                            "old_cooldown": None,
                            "new_cooldown": None,
                            "scaling_changes": [],
                            "direction": "BUFF",
                        }
                    ],
                },
            ),
        ]
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


def test_latest_patch_and_diffs_endpoints(api_client):
    latest = api_client.get("/api/v1/patches/latest")
    assert latest.status_code == 200
    body = latest.json()
    assert body["synced"] is True
    assert body["patch"]["version"] == "16.23.1"
    assert body["patch"]["champions_changed"] == 1

    diffs = api_client.get("/api/v1/patches/16.23.1/diffs")
    assert diffs.status_code == 200
    d_body = diffs.json()
    assert d_body["from_version"] == "16.22.1"
    assert d_body["champions_count"] == 1
    assert d_body["champions"][0]["entity_key"] == "Ahri"


def test_simulate_uses_from_version_snapshot(api_client, monkeypatch):
    # Bypass Redis cache to verify live calculation path
    monkeypatch.setattr("app.api.routes.redis_client.get", lambda *a, **kw: None)
    monkeypatch.setattr("app.api.routes.redis_client.setex", lambda *a, **kw: None)

    diffs = api_client.get("/api/v1/patches/16.23.1/diffs").json()
    ahri_diff = diffs["champions"][0]["diff"]

    resp = api_client.post(
        "/api/v1/simulate",
        json={
            "champion_key": "Ahri",
            "item_ids": [],
            "target_profile": "squishy",
            "patch_diff": ahri_diff,
            "from_version": "16.22.1",
        },
    )
    assert resp.status_code == 200
    sim = resp.json()["result"]
    assert sim["champion_key"] == "Ahri"
    assert sim["summary"]["avg_burst_delta_pct"] > 0.0
