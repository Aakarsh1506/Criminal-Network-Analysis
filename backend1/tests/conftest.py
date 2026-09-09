from dataclasses import replace
from unittest.mock import AsyncMock

import httpx
import pytest

from backend1.app import create_app
from backend1.config import Settings
from backend1.security import sign_officer_token

PROFILE = {
    "officerId": 7,
    "username": "officer",
    "name": "Test Officer",
    "orgName": "Test Police",
    "role": "officer",
}


@pytest.fixture
def settings(tmp_path):
    return Settings(
        jwt_secret="test-secret-that-is-at-least-32-characters", upload_dir=tmp_path / "uploads"
    )


@pytest.fixture
def db():
    return AsyncMock(query=AsyncMock(return_value=[]))


@pytest.fixture
def graph():
    return AsyncMock(run=AsyncMock(return_value=[]))


@pytest.fixture
def provider():
    return AsyncMock(
        post=AsyncMock(
            return_value=httpx.Response(
                200,
                json={
                    "choices": [{"message": {"content": "Summary"}, "finish_reason": "stop"}],
                },
            )
        )
    )


@pytest.fixture
def app(settings, db, graph, provider):
    return create_app(
        settings, database=db, graph=graph, http_client=provider, initialize_schema=False
    )


@pytest.fixture
async def client(app):
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            yield client


@pytest.fixture
async def officer_client(client, settings):
    client.cookies.set(settings.cookie_name, sign_officer_token(PROFILE, settings))
    return client


@pytest.fixture
async def admin_client(client, settings):
    client.cookies.set(
        settings.cookie_name, sign_officer_token({**PROFILE, "role": "admin"}, settings)
    )
    return client


@pytest.fixture
def ai_settings(settings):
    return replace(settings, groq_api_key="test-api-key")
