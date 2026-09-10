import json
from dataclasses import replace
from unittest.mock import AsyncMock

import httpx
import pytest

from backend.config import Settings
from backend.errors import APIError
from backend.services import extraction

TEXT = "Alice contacted Bob."


def payload():
    return {
        "entities": [
            {"ref": name.lower(), "kind": "Person", "name": name, "identifier": None,
             "attributes": [], "evidence": {"start_line": 1, "end_line": 1}}
            for name in ("Alice", "Bob")
        ],
        "relationships": [{"subject": "alice", "predicate": "CONTACTED", "object": "bob",
                           "evidence": {"start_line": 1, "end_line": 1}}],
    }


def response(data, reason="stop"):
    return httpx.Response(200, json={
        "done": True, "done_reason": reason,
        "message": {"content": json.dumps(data)},
    })


@pytest.mark.parametrize("hybrid", [False, True])
async def test_ollama_extraction_uses_local_schema_and_evidence_without_key(settings, hybrid):
    configured = replace(settings, extraction_provider="ollama", groq_api_key="")
    data = payload()
    catalog = extraction.resolve_evidence_spans(payload(), TEXT).entities if hybrid else None
    if hybrid:
        data.pop("entities")
    client = AsyncMock()
    client.post.return_value = response(data)
    result = await extraction.extract_chunk(TEXT, "fir", configured, client, catalog=catalog)
    assert result.relationships[0].evidence == TEXT
    assert len(result.entities) == 2
    args, kwargs = client.post.call_args
    assert args == ("http://localhost:11434/api/chat",)
    assert "headers" not in kwargs
    request = kwargs["json"]
    assert request["model"] == "qwen3:4b"
    assert request["think"] is False and request["stream"] is False
    assert set(request["format"]["properties"]) == (
        {"relationships"} if hybrid else {"entities", "relationships"}
    )
    assert "JSON schema:" in request["messages"][0]["content"]


async def test_ollama_corrects_invalid_evidence(settings):
    invalid = payload()
    invalid["entities"][0]["name"] = "Invented person"
    client = AsyncMock()
    client.post.side_effect = [response(invalid), response(payload())]
    result = await extraction.extract_chunk(
        TEXT, "fir", replace(settings, extraction_provider="ollama"), client,
    )
    assert result.entities[0].name == "Alice"
    assert client.post.await_count == 2
    correction = json.loads(client.post.call_args.kwargs["json"]["messages"][1]["content"])
    assert "correction" in correction
    assert correction["correction"]["previous_extraction"] is None
    assert "source_lines" in correction
    assert "entities[0].name" in correction["correction"]["validation_error"]
    assert [call.kwargs["json"]["options"]["num_predict"]
            for call in client.post.call_args_list] == [4096, 4096]


@pytest.mark.parametrize("hybrid", [False, True])
@pytest.mark.parametrize("budget,expected", [(4096, 8192), (6000, 8192)])
async def test_truncated_ollama_output_retries_with_larger_budget(settings, hybrid, budget, expected):
    data = payload()
    catalog = extraction.resolve_evidence_spans(payload(), TEXT).entities if hybrid else None
    if hybrid:
        data.pop("entities")
    client = AsyncMock()
    client.post.side_effect = [response(data, "length"), response(data)]
    result = await extraction.extract_chunk(
        TEXT, "fir", replace(settings, extraction_provider="ollama", ollama_max_tokens=budget),
        client, catalog=catalog,
    )
    assert result.relationships[0].evidence == TEXT
    assert [call.kwargs["json"]["options"]["num_predict"]
            for call in client.post.call_args_list] == [budget, expected]
    correction = json.loads(client.post.call_args.kwargs["json"]["messages"][1]["content"])
    assert correction["correction"]["output_truncated"] is True


@pytest.mark.parametrize("budget", [-1, 0, 10000])
async def test_invalid_ollama_budget_fails_before_provider_call(settings, budget):
    client = AsyncMock()
    with pytest.raises(APIError, match="OLLAMA_MAX_TOKENS"):
        await extraction.extract_chunk(
            TEXT, "fir", replace(settings, extraction_provider="ollama", ollama_max_tokens=budget),
            client,
        )
    client.post.assert_not_called()


@pytest.mark.parametrize("kind", ["json", "length", "schema"])
async def test_ollama_invalid_output_is_bounded(settings, kind):
    client = AsyncMock()
    client.post.return_value = (
        httpx.Response(200, json={"done": True, "done_reason": "stop",
                                 "message": {"content": "not json"}})
        if kind == "json" else response({} if kind == "schema" else payload(),
                                       "length" if kind == "length" else "stop")
    )
    with pytest.raises(extraction.ExtractionFailure, match="Ollama could not produce"):
        await extraction.extract_chunk(
            TEXT, "fir", replace(settings, extraction_provider="ollama"), client,
        )
    assert client.post.await_count == 2


@pytest.mark.parametrize("status,message", [(404, "ollama pull"), (400, "rejected"), (500, "failed")])
async def test_ollama_errors_are_actionable_and_never_fall_back(settings, status, message):
    client = AsyncMock()
    client.post.return_value = httpx.Response(status, json={"error": "private source text"})
    with pytest.raises(APIError, match=message) as error:
        await extraction.extract_chunk(
            TEXT, "fir", replace(settings, extraction_provider="ollama"), client,
        )
    assert "private source" not in str(error.value)
    assert client.post.await_count == 1


@pytest.mark.parametrize("error,message", [
    (httpx.ConnectError("offline"), "Unable to reach Ollama"),
    (httpx.ReadTimeout("slow"), "Ollama extraction timed out"),
])
async def test_ollama_connection_errors(settings, error, message):
    client = AsyncMock()
    client.post.side_effect = error
    with pytest.raises(APIError, match=message):
        await extraction.extract_chunk(
            TEXT, "fir", replace(settings, extraction_provider="ollama"), client,
        )
    assert client.post.await_count == 1


def test_ollama_settings_from_environment(monkeypatch):
    for key, value in {"JWT_SECRET": "test", "EXTRACTION_PROVIDER": "ollama",
                       "OLLAMA_BASE_URL": "http://localhost:11434/", "OLLAMA_MODEL": "qwen3:4b",
                       "OLLAMA_TIMEOUT": "90"}.items():
        monkeypatch.setenv(key, value)
    settings = Settings.from_env()
    assert settings.extraction_provider == "ollama"
    assert settings.ollama_base_url == "http://localhost:11434"
    assert settings.ollama_timeout == 90
