import asyncio
import json
from unittest.mock import AsyncMock

import httpx
import pytest

from backend1.routes import criminals
from backend1.services.groq import AIError, explain_network

PROFILE = {
    "criminal": {
        "id": "P1",
        "name": "Example",
        "photo": "private-photo",
        "dob": "private-dob",
        "cases": [{"caseId": "C1", "status": "Pending"}],
    },
    "relations": [
        {
            "criminal": {"id": "P2", "name": "Other", "photo": "private-photo"},
            "type": "Shared Location: Delhi",
        }
    ],
}


async def test_context_excludes_demographics_and_uses_server_records(provider):
    result = await explain_network(PROFILE, api_key="test-key", client=provider)
    assert result == "Summary"
    args, kwargs = provider.post.call_args
    assert args == ("https://api.groq.com/openai/v1/chat/completions",)
    assert kwargs["headers"]["Authorization"] == "Bearer test-key"
    context = kwargs["json"]["messages"][1]["content"]
    assert "C1" in context and "private-photo" not in context and "private-dob" not in context
    assert kwargs["timeout"] == 30
    assert "not confirmed personal relationships" in json.loads(context)["limitations"]


async def test_missing_key_and_oversized_context_do_not_call_provider(provider):
    with pytest.raises(AIError) as exc:
        await explain_network(PROFILE, api_key="", client=provider)
    assert exc.value.status == 503
    with pytest.raises(AIError) as exc:
        await explain_network(
            {**PROFILE, "criminal": {**PROFILE["criminal"], "name": "x" * 40001}},
            api_key="test",
            client=provider,
        )
    assert exc.value.status == 413
    provider.post.assert_not_called()


@pytest.mark.parametrize(
    "upstream,expected", [(401, 503), (403, 503), (429, 429), (500, 502), (404, 503)]
)
async def test_provider_errors_are_sanitized(provider, upstream, expected):
    provider.post.return_value = httpx.Response(
        upstream, json={"error": {"message": "private provider details"}}
    )
    with pytest.raises(AIError) as exc:
        await explain_network(PROFILE, api_key="test", client=provider)
    assert exc.value.status == expected
    assert "private provider details" not in str(exc.value)


@pytest.mark.parametrize(
    "error,status",
    [
        (httpx.ReadTimeout("private"), 504),
        (TimeoutError("private"), 504),
        (httpx.ConnectError("private"), 502),
    ],
)
async def test_timeout_and_network_failures(provider, error, status):
    provider.post.side_effect = error
    with pytest.raises(AIError) as exc:
        await explain_network(PROFILE, api_key="test", client=provider)
    assert exc.value.status == status and "private" not in str(exc.value)


@pytest.mark.parametrize("content,reason", [("", "stop"), (None, "stop"), ("partial", "length")])
async def test_unusable_answers(provider, content, reason):
    provider.post.return_value = httpx.Response(
        200, json={"choices": [{"message": {"content": content}, "finish_reason": reason}]}
    )
    with pytest.raises(AIError) as exc:
        await explain_network(PROFILE, api_key="test", client=provider)
    assert exc.value.status == 502


async def test_explanation_statuses_release_capacity(officer_client, app, ai_settings, monkeypatch):
    assert (await officer_client.post("/api/criminals/P1/explain")).status_code == 503
    app.state.settings = ai_settings
    monkeypatch.setattr(criminals, "load_profile", AsyncMock(return_value=None))
    assert (await officer_client.post("/api/criminals/P1/explain")).status_code == 404
    assert app.state.active_explanations == 0
    criminals.load_profile.return_value = PROFILE
    response = await officer_client.post("/api/criminals/P1/explain")
    assert response.json() == {"explanation": "Summary"}
    assert app.state.active_explanations == 0
    criminals.load_profile.side_effect = RuntimeError("private")
    assert (await officer_client.post("/api/criminals/P1/explain")).status_code == 500
    assert app.state.active_explanations == 0


async def test_explanation_limits_concurrent_requests(
    officer_client, app, ai_settings, monkeypatch
):
    app.state.settings = ai_settings
    release = asyncio.Event()
    all_started = asyncio.Event()
    started = 0

    async def load(*args):
        nonlocal started
        started += 1
        if started == 3:
            all_started.set()
        await release.wait()
        return PROFILE

    monkeypatch.setattr(criminals, "load_profile", load)
    tasks = [
        asyncio.create_task(officer_client.post("/api/criminals/P1/explain")) for _ in range(3)
    ]
    try:
        await asyncio.wait_for(all_started.wait(), timeout=5)
        assert (await officer_client.post("/api/criminals/P1/explain")).status_code == 429
    finally:
        release.set()
        responses = await asyncio.gather(*tasks)
    assert all(response.status_code == 200 for response in responses)
    assert app.state.active_explanations == 0
