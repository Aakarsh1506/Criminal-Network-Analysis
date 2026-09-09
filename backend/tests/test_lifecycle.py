from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from backend import app as app_module
from backend.app import create_app
from backend.config import Settings
from backend.security import token_lifetime


async def test_owns_and_closes_resources(settings, monkeypatch):
    database = AsyncMock()
    graph = AsyncMock()
    provider = AsyncMock()
    provider.__aenter__.return_value = provider
    monkeypatch.setattr(app_module, "Database", MagicMock(return_value=database))
    monkeypatch.setattr(app_module, "GraphDatabase", MagicMock(return_value=graph))
    monkeypatch.setattr(app_module.httpx, "AsyncClient", MagicMock(return_value=provider))
    application = create_app(settings)
    async with application.router.lifespan_context(application):
        database.open.assert_awaited_once()
        database.ensure_schema.assert_awaited_once()
        assert application.state.graph is graph
        assert application.state.http_client is provider
    database.close.assert_awaited_once()
    graph.close.assert_awaited_once()
    provider.__aexit__.assert_awaited_once()


async def test_schema_failure_retains_liveness(settings, db, graph):
    db.ensure_schema.side_effect = RuntimeError("database unavailable")
    application = create_app(settings, database=db, graph=graph, http_client=AsyncMock())
    async with application.router.lifespan_context(application):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=application), base_url="http://test"
        ) as client:
            assert (await client.get("/api/health")).json() == {"ok": True}


def test_configuration_precedence_and_missing_secret(tmp_path, monkeypatch):
    from backend import config

    monkeypatch.setattr(config, "BASE_DIR", tmp_path)
    monkeypatch.delenv("JWT_SECRET", raising=False)
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        Settings.from_env()
    (tmp_path / ".env").write_text("JWT_SECRET=file-secret\nPORT=6000\nPGDATABASE=from-file\n")
    monkeypatch.setenv("PORT", "7000")
    monkeypatch.delenv("PGDATABASE", raising=False)
    settings = Settings.from_env()
    assert settings.jwt_secret == "file-secret"
    assert settings.port == 7000
    assert settings.pg_database == "from-file"


@pytest.mark.parametrize(
    "duration,seconds",
    [("12h", 43200), ("7d", 604800), ("120", 0.12), ("2 hours", 7200), ("1.5h", 5400)],
)
def test_jwt_duration_compatibility(duration, seconds):
    assert token_lifetime(duration).total_seconds() == seconds


def test_invalid_expiry_fails_at_startup(settings):
    from dataclasses import replace

    with pytest.raises(ValueError, match="JWT_EXPIRES_IN"):
        create_app(replace(settings, jwt_expires_in="invalid"))


def test_server_entrypoint_uses_configured_port(monkeypatch):
    import runpy

    import uvicorn

    run = MagicMock()
    monkeypatch.setenv("JWT_SECRET", "test-secret-that-is-at-least-32-characters")
    monkeypatch.setenv("JWT_EXPIRES_IN", "12h")
    monkeypatch.setenv("PORT", "6080")
    monkeypatch.setattr(uvicorn, "run", run)
    namespace = runpy.run_module("backend.server", run_name="__main__")
    run.assert_called_once_with(namespace["app"], host="0.0.0.0", port=6080)
