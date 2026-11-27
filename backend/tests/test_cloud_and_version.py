import json
import re
from pathlib import Path
from fastapi.testclient import TestClient

from app.core.config import parse_cors_origins, settings
from app.core.database import normalize_database_url
from app.main import app


def test_normalize_database_url_for_psycopg3():
    assert (
        normalize_database_url("postgres://user:pass@ep-cool.neon.tech/neondb?sslmode=require")
        == "postgresql+psycopg://user:pass@ep-cool.neon.tech/neondb?sslmode=require"
    )
    assert (
        normalize_database_url("postgresql://user:pass@localhost:5432/patchdiff")
        == "postgresql+psycopg://user:pass@localhost:5432/patchdiff"
    )
    assert (
        normalize_database_url("postgresql+psycopg://user:pass@localhost:5432/patchdiff")
        == "postgresql+psycopg://user:pass@localhost:5432/patchdiff"
    )
    assert normalize_database_url("sqlite:///:memory:") == "sqlite:///:memory:"


def test_parse_cors_origins():
    parsed = parse_cors_origins("https://patchdiff.pages.dev/, http://localhost:5173 , ")
    assert parsed == ["https://patchdiff.pages.dev", "http://localhost:5173"]
    assert parse_cors_origins("*") == ["*"]
    assert parse_cors_origins("") == ["http://localhost:5173"]


def test_release_version_parity_across_backend_frontend_and_changelog(monkeypatch):
    monkeypatch.setattr(settings, "AUTO_SYNC_ENABLED", False)
    repo_root = Path(__file__).resolve().parents[2]
    pkg_version = json.loads((repo_root / "frontend" / "package.json").read_text(encoding="utf-8"))["version"]
    lock_version = json.loads((repo_root / "frontend" / "package-lock.json").read_text(encoding="utf-8"))["version"]
    changelog_text = (repo_root / "CHANGELOG.md").read_text(encoding="utf-8")

    pattern = re.compile(
        rf"^## \[{re.escape(pkg_version)}\][^\n]*\n(.*?)(?=^## \[|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(changelog_text)
    assert match is not None and match.group(1).strip()

    assert pkg_version == "2.0.1"
    assert lock_version == "2.0.1"
    assert app.version == pkg_version

    with TestClient(app) as client:
        res = client.get("/")
    assert res.status_code == 200
    assert res.json()["version"] == "2.0.1"
