from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app


def _make_test_client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app), engine


def test_submit_and_summarize_recommendation_feedback():
    client, _ = _make_test_client()
    try:
        # 1. Invalid rating (6) must be rejected
        bad_resp = client.post(
            "/api/v1/feedback",
            json={
                "patch_version": "16.23.1",
                "champion_key": "Syndra",
                "playstyle": "burst",
                "rating": 6,
                "is_helpful": True,
            },
        )
        assert bad_resp.status_code == 422

        # 2. Submit two valid feedback entries
        r1 = client.post(
            "/api/v1/feedback",
            json={
                "patch_version": "16.23.1",
                "champion_key": "Syndra",
                "role": "mid",
                "game_map": "sr",
                "target_profile": "squishy",
                "playstyle": "burst",
                "items": [{"item_id": "6655", "name": "Luden's Companion", "buy_order": 1}],
                "rating": 5,
                "is_helpful": True,
                "comment": "Great that Lich Bane is excluded here!",
            },
        )
        assert r1.status_code == 200
        assert r1.json()["status"] == "saved"
        assert r1.json()["rating"] == 5

        r2 = client.post(
            "/api/v1/feedback",
            json={
                "patch_version": "16.23.1",
                "champion_key": "Syndra",
                "role": "mid",
                "game_map": "sr",
                "target_profile": "squishy",
                "playstyle": "balanced",
                "items": [],
                "rating": 3,
                "is_helpful": False,
                "comment": "Zhonya could come slightly earlier.",
            },
        )
        assert r2.status_code == 200

        # 3. Verify aggregated feedback summary
        summary = client.get("/api/v1/feedback/summary?champion_key=Syndra").json()
        assert summary["total_count"] == 2
        assert summary["avg_rating"] == 4.0
        assert summary["helpful_rate_pct"] == 50.0
        assert summary["by_playstyle"]["burst"]["avg_rating"] == 5.0
        assert len(summary["recent_comments"]) == 2
    finally:
        app.dependency_overrides.clear()
