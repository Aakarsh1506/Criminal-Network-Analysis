import asyncio
from dataclasses import replace
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from PIL import Image, ImageDraw, ImageFont

from backend.errors import APIError
from backend.services import document_text, extraction, ingestion
from backend.services.extraction import Extraction, validate_extraction
from backend.services.ingestion_store import sync_graph

TEXT = "Alice (P001) witnessed case C100 in Mumbai. Bob contacted Alice."


def sample():
    return Extraction.model_validate(
        {
            "entities": [
                {
                    "ref": "alice",
                    "kind": "Person",
                    "name": "Alice",
                    "identifier": "P001",
                    "attributes": [],
                    "evidence": "Alice (P001)",
                },
                {
                    "ref": "case",
                    "kind": "Case",
                    "name": "C100",
                    "identifier": "C100",
                    "attributes": [],
                    "evidence": "case C100",
                },
            ],
            "relationships": [
                {
                    "subject": "alice",
                    "predicate": "WITNESS_IN",
                    "object": "case",
                    "evidence": "Alice (P001) witnessed case C100",
                }
            ],
        }
    )


@pytest.mark.parametrize(
    "suffix,content",
    [(".txt", "Alice"), (".csv", "name,role\nAlice,witness"), (".json", '{"name":"Alice"}')],
)
def test_digital_text(tmp_path, suffix, content):
    path = tmp_path / ("source" + suffix)
    path.write_text(content)
    assert document_text.extract_text(path) == content


def test_word_text(tmp_path):
    import zipfile

    path = tmp_path / "source.docx"
    with zipfile.ZipFile(path, "w") as doc:
        doc.writestr(
            "word/document.xml",
            """<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Alice witnessed C100.</w:t></w:r></w:p></w:body></w:document>""",
        )
    assert "Alice witnessed C100." in document_text.extract_text(path)


def test_image_and_scanned_pdf_ocr(tmp_path):
    import shutil

    if not shutil.which("tesseract"):
        pytest.skip("Tesseract is not installed")
    picture = Image.new("RGB", (1200, 200), "white")
    draw = ImageDraw.Draw(picture)
    draw.text(
        (30, 50), "Alice witnessed case C100.", font=ImageFont.load_default(size=45), fill="black"
    )
    for suffix in (".png", ".pdf"):
        path = tmp_path / ("scan" + suffix)
        picture.save(path)
        assert "Alice witnessed case C100" in document_text.extract_text(path)


def test_unreadable_and_oversized_text(tmp_path):
    path = tmp_path / "blank.txt"
    path.write_text(" ")
    with pytest.raises(APIError, match="No readable text"):
        document_text.extract_text(path)
    path.write_text("x" * (document_text.MAX_TEXT + 1))
    with pytest.raises(APIError, match="60,000"):
        document_text.extract_text(path)
    path = tmp_path / "invalid.pdf"
    path.write_bytes(b"not a PDF")
    with pytest.raises(APIError, match="Cannot read"):
        document_text.extract_text(path)


def test_missing_tesseract_has_actionable_error(monkeypatch):
    import pytesseract

    monkeypatch.setattr(
        pytesseract, "image_to_string", MagicMock(side_effect=pytesseract.TesseractNotFoundError())
    )
    with pytest.raises(APIError, match="Install Tesseract"):
        document_text.ocr_image(Image.new("RGB", (50, 50)), "eng")


def test_validation_requires_source_evidence_and_valid_directions():
    assert validate_extraction(sample(), TEXT).relationships[0].predicate == "WITNESS_IN"
    result = sample()
    result.relationships[0].predicate = "OWNS"
    with pytest.raises(APIError, match="invalid relationship"):
        validate_extraction(result, TEXT)
    result = sample()
    result.entities[0].evidence = "A fabricated quote"
    with pytest.raises(APIError, match="evidence"):
        validate_extraction(result, TEXT)
    result = sample()
    result.entities[0].identifier = "P099"
    with pytest.raises(APIError, match="identifier"):
        validate_extraction(result, TEXT)
    result = sample()
    result.relationships[0].subject = "missing"
    with pytest.raises(APIError, match="invalid relationship"):
        validate_extraction(result, TEXT)


async def test_groq_json_validation_and_chunk_deduplication(settings):
    client = AsyncMock()
    client.post.return_value = httpx.Response(
        200,
        json={
            "choices": [
                {"message": {"content": sample().model_dump_json()}, "finish_reason": "stop"}
            ]
        },
    )
    configured = replace(settings, groq_api_key="fake")
    result = await extraction.extract_entities((TEXT + " ") * 230, "fir", configured, client)
    assert len(result.entities) == 2 and len(result.relationships) == 1
    assert client.post.await_count > 1
    assert result.relationships[0].subject == result.entities[0].ref
    client.post.return_value = httpx.Response(
        200, json={"choices": [{"message": {"content": "{}"}, "finish_reason": "length"}]}
    )
    with pytest.raises(APIError, match="incomplete"):
        await extraction.extract_chunk(TEXT, "fir", configured, client)


@pytest.mark.parametrize("status", [401, 500])
async def test_provider_error_does_not_leak_body(settings, status):
    client = AsyncMock()
    client.post.return_value = httpx.Response(status, text="secret provider details")
    with pytest.raises(APIError) as caught:
        await extraction.extract_chunk(TEXT, "fir", replace(settings, groq_api_key="fake"), client)
    assert "secret" not in str(caught.value)


async def test_graph_sync_retry_does_not_repeat_ocr_ai_or_postgres(settings, monkeypatch):
    payload = {"nodes": [], "edges": [], "document_id": 1}
    doc = {"document_id": 1, "graph_payload": payload}
    state = SimpleNamespace(settings=settings, db=AsyncMock(), graph=AsyncMock())
    ocr = MagicMock()
    ai, persist, graph_write = (
        AsyncMock(),
        AsyncMock(),
        AsyncMock(side_effect=RuntimeError("secret")),
    )
    monkeypatch.setattr(ingestion, "extract_text", ocr)
    monkeypatch.setattr(ingestion, "extract_entities", ai)
    monkeypatch.setattr(ingestion, "persist_extraction", persist)
    monkeypatch.setattr(ingestion, "sync_graph", graph_write)
    await ingestion.process_document(state, doc)
    sql, params = state.db.query.call_args.args
    assert "sync_failed" in sql and "secret" not in params[0]
    graph_write.side_effect = None
    await ingestion.process_document(state, doc)
    assert "processing_status='complete'" in state.db.query.call_args.args[0]
    ocr.assert_not_called()
    ai.assert_not_called()
    persist.assert_not_called()


async def test_shutdown_requeues_job(settings, monkeypatch):
    state = SimpleNamespace(settings=settings, db=AsyncMock(), graph=AsyncMock())
    monkeypatch.setattr(ingestion, "sync_graph", AsyncMock(side_effect=asyncio.CancelledError()))
    with pytest.raises(asyncio.CancelledError):
        await ingestion.process_document(state, {"document_id": 1, "graph_payload": {}})
    assert "processing_status='queued'" in state.db.query.call_args.args[0]


async def test_graph_predicates_preserve_directions_and_are_idempotent():
    tx = AsyncMock()
    tx.run.return_value = AsyncMock()
    session = AsyncMock()

    async def execute_write(callback):
        await callback(tx)

    session.execute_write.side_effect = execute_write
    driver = MagicMock()
    driver.session.return_value.__aenter__.return_value = session
    payload = {
        "document_id": 3,
        "nodes": [
            {"kind": "Person", "id": "P001", "properties": {"name": "Alice"}},
            {"kind": "Case", "id": "C100", "properties": {}},
        ],
        "edges": [
            {
                "id": "r1",
                "subject": {"kind": "Person", "id": "P001"},
                "object": {"kind": "Case", "id": "C100"},
                "predicate": "WITNESS_IN",
                "evidence": "Alice witnessed C100",
            }
        ],
    }
    await sync_graph(SimpleNamespace(driver=driver), payload)
    query = tx.run.call_args.args[0]
    assert "MERGE (a)-[r:WITNESS_IN {extraction_id: $id}]->(b)" in query
    assert tx.run.call_args.kwargs["subject"] == "P001"
    assert tx.run.call_args.kwargs["object"] == "C100"
    assert "unverified" in query


@pytest.mark.parametrize("source_type", list(extraction.SOURCE_TYPES))
async def test_seven_source_categories_queue_on_upload(officer_client, db, source_type):
    db.query.return_value = [
        {
            "document_id": 1,
            "original_name": "report.csv",
            "mime_type": "text/csv",
            "size_bytes": 5,
            "uploaded_at": datetime.now(timezone.utc),
            "source_type": source_type,
            "processing_status": "queued",
        }
    ]
    response = await officer_client.post(
        "/api/documents",
        data={"sourceType": source_type},
        files={"file": ("report.csv", b"name\nAlice", "text/csv")},
    )
    assert response.status_code == 201
    assert response.json()["sourceType"] == source_type
    assert response.json()["status"] == "queued"
    assert db.query.call_args.args[1][-1] == source_type


async def test_document_details_and_retry_require_owner(officer_client, db):
    db.query.return_value = []
    assert (await officer_client.get("/api/documents/1")).status_code == 404
    assert db.query.call_args.args[1] == (1, 7)
    assert (await officer_client.post("/api/documents/1/process")).status_code == 409
    assert db.query.call_args.args[1] == (1, 7)
    assert "officer_id=%s" in db.query.call_args.args[0]


async def test_reject_unknown_category_before_saving(officer_client, db):
    response = await officer_client.post(
        "/api/documents",
        data={"sourceType": "invented"},
        files={"file": ("report.txt", b"Alice", "text/plain")},
    )
    assert response.status_code == 400
    db.query.assert_not_called()


def test_evidence_typography_is_matched_and_original_quote_is_preserved():
    source = "Alice (P001) witnessed case C100 — at “Acme”."
    result = sample()
    result.relationships[0].evidence = 'Alice (P001) witnessed case C100 - at "Acme".'
    validated = validate_extraction(result, source)
    assert validated.relationships[0].evidence == source
    assert extraction.source_quote("office", "ofﬁce") == "ofﬁce"
    assert extraction.source_quote("Alice (P001)", "Alice\u00a0(P001)") == "Alice\u00a0(P001)"
    assert extraction.source_quote('"Alice (P001)"', TEXT) == "Alice (P001)"


def test_evidence_matching_does_not_remove_negations_or_change_identifiers():
    assert extraction.source_quote("Alice contacted Bob", "Alice never contacted Bob") is None
    assert extraction.source_quote("P001", "P009") is None
    assert extraction.source_quote("Alice owns a car", "Alice rented a car") is None


async def test_unmatched_evidence_gets_one_corrective_attempt(settings):
    incorrect = sample()
    incorrect.entities[0].evidence = "Alice is a witness"
    client = AsyncMock()
    client.post.side_effect = [
        httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": result.model_dump_json()}, "finish_reason": "stop"}
                ]
            },
        )
        for result in (incorrect, sample())
    ]
    result = await extraction.extract_chunk(
        TEXT, "fir", replace(settings, groq_api_key="fake"), client
    )
    assert result.entities[0].evidence == "Alice (P001)"
    assert client.post.await_count == 2
    assert "previous_extraction" in client.post.call_args.kwargs["json"]["messages"][1]["content"]


async def test_evidence_correction_is_bounded(settings):
    incorrect = sample()
    incorrect.entities[0].evidence = "Made up evidence"
    client = AsyncMock()
    client.post.return_value = httpx.Response(
        200,
        json={
            "choices": [
                {"message": {"content": incorrect.model_dump_json()}, "finish_reason": "stop"}
            ]
        },
    )
    with pytest.raises(APIError, match="after a correction attempt"):
        await extraction.extract_chunk(TEXT, "fir", replace(settings, groq_api_key="fake"), client)
    assert client.post.await_count == 2


async def test_groq_json_generation_error_is_retried_without_blaming_key(settings):
    client = AsyncMock()
    client.post.side_effect = [
        httpx.Response(
            400,
            json={
                "error": {"code": "json_validate_failed", "failed_generation": "private records"}
            },
        ),
        httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": sample().model_dump_json()}, "finish_reason": "stop"}
                ]
            },
        ),
    ]
    result = await extraction.extract_chunk(
        TEXT, "fir", replace(settings, groq_api_key="fake"), client
    )
    assert result.entities[0].name == "Alice"
    assert client.post.await_count == 2
    assert "private records" not in client.post.call_args.kwargs["json"]["messages"][1]["content"]


@pytest.mark.parametrize(
    "status,code,message",
    [
        (401, "invalid_api_key", "rejected the API key"),
        (403, None, "denied access"),
        (404, "model_not_found", "model is unavailable"),
        (400, "model_decommissioned", "model is unavailable"),
        (400, "context_length_exceeded", "size limit"),
        (400, None, "HTTP 400"),
    ],
)
async def test_groq_failures_are_distinguished(settings, status, code, message):
    client = AsyncMock()
    client.post.return_value = httpx.Response(
        status, json={"error": {"code": code, "message": "private content"}}
    )
    with pytest.raises(APIError, match=message) as caught:
        await extraction.extract_chunk(TEXT, "fir", replace(settings, groq_api_key="fake"), client)
    assert "private content" not in str(caught.value)
    assert client.post.await_count == 1


async def test_rate_limit_honors_retry_after_and_recovers(settings, monkeypatch):
    sleep = AsyncMock()
    monkeypatch.setattr(extraction.asyncio, "sleep", sleep)
    client = AsyncMock()
    client.post.side_effect = [
        httpx.Response(429, headers={"retry-after": "25"}),
        httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": sample().model_dump_json()}, "finish_reason": "stop"}
                ]
            },
        ),
    ]
    result = await extraction.extract_chunk(
        TEXT, "fir", replace(settings, groq_api_key="fake"), client
    )
    assert result.entities[0].name == "Alice"
    sleep.assert_awaited_once_with(25)
    assert client.post.await_count == 2
    assert client.post.call_args.kwargs["json"]["max_completion_tokens"] == 4096


async def test_rate_limit_retries_are_bounded(settings, monkeypatch):
    sleep = AsyncMock()
    monkeypatch.setattr(extraction.asyncio, "sleep", sleep)
    client = AsyncMock()
    client.post.return_value = httpx.Response(429, headers={"retry-after": "2"})
    with pytest.raises(extraction.RateLimitError):
        await extraction.extract_chunk(TEXT, "fir", replace(settings, groq_api_key="fake"), client)
    assert client.post.await_count == 3
    assert [call.args[0] for call in sleep.await_args_list] == [15, 30]


async def test_long_quota_reset_is_not_retried_early(settings, monkeypatch):
    sleep = AsyncMock()
    monkeypatch.setattr(extraction.asyncio, "sleep", sleep)
    client = AsyncMock()
    client.post.return_value = httpx.Response(429, headers={"retry-after": "3600"})
    with pytest.raises(APIError, match="3600 seconds"):
        await extraction.extract_chunk(TEXT, "fir", replace(settings, groq_api_key="fake"), client)
    sleep.assert_not_awaited()
    assert client.post.await_count == 1


@pytest.mark.parametrize(
    "value,expected", [("NaN", 60), ("inf", 60), ("garbage", 60), ("-1", 1), ("2.5", 2.5)]
)
def test_retry_after_is_sanitized(value, expected):
    assert extraction.retry_delay({"retry-after": value}) == expected


def test_strict_output_schema_enforces_requested_predicates():
    output = extraction.response_format_for("openai/gpt-oss-20b")
    assert output["type"] == "json_schema"
    assert output["json_schema"]["strict"] is True
    schema = output["json_schema"]["schema"]
    predicates = schema["$defs"]["SourceRelationship"]["properties"]["predicate"]["enum"]
    assert set(predicates) == set(extraction.RELATION_RULES)
    for definition in [schema, *schema["$defs"].values()]:
        assert definition["additionalProperties"] is False
        assert set(definition["required"]) == set(definition["properties"])
    assert "maxItems" not in schema["properties"]["entities"]


async def test_groq_request_uses_strict_schema_for_configured_model(settings):
    client = AsyncMock()
    client.post.return_value = httpx.Response(
        200,
        json={
            "choices": [
                {"message": {"content": sample().model_dump_json()}, "finish_reason": "stop"}
            ]
        },
    )
    await extraction.extract_chunk(TEXT, "fir", replace(settings, groq_api_key="fake"), client)
    request = client.post.call_args.kwargs["json"]
    assert request["response_format"]["json_schema"]["strict"] is True
    assert "JSON schema:" not in request["messages"][0]["content"]


def test_other_models_keep_json_mode_with_local_validation():
    assert extraction.response_format_for("another-model") == {"type": "json_object"}


async def test_extraction_waits_for_review_without_canonical_or_graph_writes(settings, monkeypatch):
    state = SimpleNamespace(settings=settings, db=AsyncMock(), graph=AsyncMock())
    persist, graph_write = AsyncMock(), AsyncMock()
    monkeypatch.setattr(ingestion, "persist_extraction", persist)
    monkeypatch.setattr(ingestion, "sync_graph", graph_write)
    await ingestion.process_document(
        state,
        {
            "document_id": 3,
            "extracted_text": TEXT,
            "extraction": sample().model_dump(),
            "confirmed_at": None,
        },
    )
    assert "awaiting_review" in state.db.query.call_args.args[0]
    persist.assert_not_awaited()
    graph_write.assert_not_awaited()


async def test_confirmation_requires_auth(client, db):
    response = await client.post(
        "/api/documents/3/confirm", json={"extraction": sample().model_dump()}
    )
    assert response.status_code == 401
    db.query.assert_not_called()


async def test_confirmation_scopes_owner_and_exact_snapshot(officer_client, db):
    db.query.return_value = []
    response = await officer_client.post(
        "/api/documents/3/confirm", json={"extraction": sample().model_dump()}
    )
    assert response.status_code == 409
    sql, params = db.query.call_args.args
    assert "officer_id=%s" in sql and "extraction=%s" in sql
    assert "processing_status='awaiting_review'" in sql
    assert params[:3] == (7, 3, 7)
    assert params[3].obj == sample().model_dump()


def test_relationship_resolves_only_unique_exact_names_or_identifiers():
    result = sample()
    result.relationships[0].subject = "Alice"
    result.relationships[0].object = "C100"
    validated = validate_extraction(result, TEXT)
    assert validated.relationships[0].subject == "alice"
    assert validated.relationships[0].object == "case"


def test_relationship_ambiguous_names_are_not_guessed():
    result = sample()
    duplicate = result.entities[0].model_copy(update={"ref": "another-alice"})
    result.entities.append(duplicate)
    result.relationships[0].subject = "Alice"
    with pytest.raises(extraction.RelationshipError, match="missing entity"):
        validate_extraction(result, TEXT)


async def test_wrong_relationship_kind_gets_targeted_correction(settings):
    incorrect = sample()
    incorrect.relationships[0].predicate = "OWNS"
    client = AsyncMock()
    client.post.side_effect = [
        httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": value.model_dump_json()}, "finish_reason": "stop"}
                ]
            },
        )
        for value in (incorrect, sample())
    ]
    result = await extraction.extract_chunk(
        TEXT, "fir", replace(settings, groq_api_key="fake"), client
    )
    assert result.relationships[0].predicate == "WITNESS_IN"
    correction = client.post.call_args.kwargs["json"]["messages"][1]["content"]
    assert "OWNS" in correction and "Vehicle" in correction
    assert client.post.await_count == 2


async def test_invalid_relationship_is_excluded_after_correction(settings):
    incorrect = sample()
    incorrect.relationships[0].predicate = "OWNS"
    client = AsyncMock()
    client.post.return_value = httpx.Response(
        200,
        json={
            "choices": [
                {"message": {"content": incorrect.model_dump_json()}, "finish_reason": "stop"}
            ]
        },
    )
    result = await extraction.extract_chunk(TEXT, "fir", replace(settings, groq_api_key="fake"), client)
    assert result.entities == sample().entities
    assert result.relationships == []
    assert result.excluded_relationships[0].predicate == "OWNS"
    assert "Vehicle" in result.excluded_relationships[0].reason
    assert client.post.await_count == 2


def test_line_references_copy_original_source_instead_of_generated_quotes():
    text = "Alice (P001)\nWitnessed case C100.\n"
    payload = sample().model_dump()
    payload["entities"][0]["evidence"] = {"start_line": 1, "end_line": 1}
    payload["entities"][1]["evidence"] = {"start_line": 2, "end_line": 2}
    payload["relationships"][0]["evidence"] = {"start_line": 1, "end_line": 2}
    result = extraction.resolve_evidence_spans(payload, text)
    validate_extraction(result, text)
    assert result.entities[0].evidence == "Alice (P001)"
    assert result.relationships[0].evidence == text.strip()


@pytest.mark.parametrize("start,end", [(0, 1), (1, 9), (2, 1)])
def test_invalid_line_ranges_cannot_create_evidence(start, end):
    payload = sample().model_dump()
    payload["entities"][0]["evidence"] = {"start_line": start, "end_line": end}
    with pytest.raises(extraction.GenerationError, match="line references"):
        extraction.resolve_evidence_spans(payload, "one line")


def test_long_source_line_splitting_preserves_all_source_characters():
    text = ("Alice (P001)\t witnessed a case. " * 80) + "\nNext paragraph."
    lines = extraction.source_lines(text)
    assert "".join(lines) == text
    assert max(map(len, lines)) <= 700


async def test_groq_line_spans_are_resolved_before_grounding_validation(settings):
    text = "Alice (P001) witnessed case C100."
    payload = sample().model_dump()
    for item in payload["entities"] + payload["relationships"]:
        item["evidence"] = {"start_line": 1, "end_line": 1}
    client = AsyncMock()
    import json

    client.post.return_value = httpx.Response(
        200,
        json={"choices": [{"message": {"content": json.dumps(payload)}, "finish_reason": "stop"}]},
    )
    result = await extraction.extract_chunk(
        text, "fir", replace(settings, groq_api_key="fake"), client
    )
    assert result.entities[0].evidence == text
    request = client.post.call_args.kwargs["json"]
    source = json.loads(request["messages"][1]["content"])
    assert source["source_lines"] == [{"line": 1, "text": text}]


async def test_provider_rejected_predicate_gets_specific_correction(settings):
    import json

    invalid = sample().model_dump()
    for item in invalid["entities"] + invalid["relationships"]:
        item["evidence"] = {"start_line": 1, "end_line": 1}
    invalid["relationships"][0]["predicate"] = "INVENTED_LINK"
    client = AsyncMock()
    client.post.side_effect = [
        httpx.Response(
            400,
            json={
                "error": {"code": "json_validate_failed", "failed_generation": json.dumps(invalid)}
            },
        ),
        httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": sample().model_dump_json()}, "finish_reason": "stop"}
                ]
            },
        ),
    ]
    await extraction.extract_chunk(TEXT, "fir", replace(settings, groq_api_key="fake"), client)
    correction = json.loads(client.post.call_args.kwargs["json"]["messages"][1]["content"])[
        "correction"
    ]
    assert correction["invalid_fields"][0]["unsupported_predicate"] == "INVENTED_LINK"
    assert "Keep the entities" in correction["invalid_fields"][0]["instruction"]


def test_groq_debug_output_is_disabled_by_default(settings, capsys):
    extraction.debug_response(httpx.Response(200, json={"private": "document data"}), settings)
    assert capsys.readouterr().err == ""


@pytest.mark.parametrize("status,key", [(200, "content"), (400, "failed_generation")])
def test_groq_debug_prints_raw_and_generated_json(settings, capsys, status, key):
    generated = '{\n  "entities": [], "relationships": []\n}'
    body = (
        {"choices": [{"message": {"content": generated}}]}
        if key == "content"
        else {"error": {"code": "json_validate_failed", "failed_generation": generated}}
    )
    response = httpx.Response(status, json=body)
    extraction.debug_response(response, replace(settings, groq_debug_responses=True))
    output = capsys.readouterr().err
    assert response.text in output
    assert generated in output
    assert f"HTTP {status}" in output


def test_groq_debug_redacts_api_key_and_handles_non_json(settings, capsys):
    extraction.debug_response(
        httpx.Response(502, text="Oops fake-secret-key"),
        replace(settings, groq_api_key="fake-secret-key", groq_debug_responses=True),
    )
    output = capsys.readouterr().err
    assert "fake-secret-key" not in output
    assert "[REDACTED API KEY]" in output


async def test_groq_debug_runs_before_provider_error_handling(settings, capsys):
    client = AsyncMock()
    client.post.return_value = httpx.Response(401, json={"error": {"message": "Invalid API key"}})
    with pytest.raises(APIError):
        await extraction.extract_chunk(
            TEXT, "fir", replace(settings, groq_api_key="fake", groq_debug_responses=True), client
        )
    assert "GROQ DEBUG RESPONSE" in capsys.readouterr().err


def test_exclusion_preserves_valid_links_and_rejects_ungrounded_evidence():
    result = sample()
    bad = result.relationships[0].model_copy(update={"predicate": "OCCURRED_AT"})
    result.relationships.insert(0, bad)
    validated = validate_extraction(result, TEXT, exclude_invalid=True)
    assert [r.predicate for r in validated.relationships] == ["WITNESS_IN"]
    assert len(validated.excluded_relationships) == 1
    assert "Person → Case" in validated.excluded_relationships[0].reason
    validated.entities[0].evidence = "Invented evidence"
    with pytest.raises(extraction.EvidenceError):
        validate_extraction(validated, TEXT, exclude_invalid=True)


def test_empty_exclusions_preserve_legacy_confirmation_snapshot():
    payload = sample().model_dump()
    assert "excluded_relationships" not in payload
    assert extraction.Extraction.model_validate(payload).model_dump() == payload


async def test_excluded_refs_survive_chunk_merge(settings, monkeypatch):
    result = sample()
    result.relationships.append(result.relationships[0].model_copy(update={"object": "missing"}))
    result = validate_extraction(result, TEXT, exclude_invalid=True)
    monkeypatch.setattr(extraction, "extract_chunk", AsyncMock(return_value=result))
    merged = await extraction.extract_entities(TEXT, "fir", settings, AsyncMock())
    assert merged.excluded_relationships[0].subject == merged.entities[0].ref
    assert merged.excluded_relationships[0].object == "chunk-0:missing"
    assert len(merged.relationships) == 1
    assert extraction.Extraction.model_validate(merged.model_dump()) == merged


async def test_failed_section_is_split_once_without_losing_source(settings, monkeypatch):
    calls = []

    async def extract(section, *_args):
        calls.append(section)
        if len(calls) == 1:
            raise extraction.ExtractionFailure("bad JSON", 502)
        return extraction.Extraction(entities=[], relationships=[])

    monkeypatch.setattr(extraction, "extract_chunk", extract)
    source = "first paragraph\n" * 180
    result = await extraction.extract_entities(source, "fir", settings, AsyncMock())
    assert len(calls) == 3
    assert calls[1] + calls[2][400:] == source
    assert result.entities == []


async def test_subdivision_stops_and_reports_source_range(settings, monkeypatch):
    extract = AsyncMock(side_effect=extraction.ExtractionFailure("entities.0.name: missing", 502))
    monkeypatch.setattr(extraction, "extract_chunk", extract)
    with pytest.raises(extraction.ExtractionFailure, match="Source characters 1–.*entities.0.name"):
        await extraction.extract_entities("x" * 3000, "fir", settings, AsyncMock())
    assert extract.await_count == 2


async def test_rate_limits_do_not_trigger_subdivision(settings, monkeypatch):
    extract = AsyncMock(side_effect=extraction.RateLimitError(3600))
    monkeypatch.setattr(extraction, "extract_chunk", extract)
    with pytest.raises(extraction.RateLimitError):
        await extraction.extract_entities("x" * 3000, "fir", settings, AsyncMock())
    assert extract.await_count == 1


async def test_markdown_json_wrapper_is_accepted_without_changing_evidence(settings):
    client = AsyncMock()
    client.post.return_value = httpx.Response(200, json={"choices": [{
        "message": {"content": "```json\n" + sample().model_dump_json() + "\n```"},
        "finish_reason": "stop",
    }]})
    result = await extraction.extract_chunk(TEXT, "fir", replace(settings, groq_api_key="fake"), client)
    assert result == sample()
    assert client.post.await_count == 1


async def test_provider_schema_retry_uses_json_mode_with_local_validation(settings):
    import json

    invalid = sample().model_dump()
    invalid["entities"][0]["kind"] = "UnknownKind"
    client = AsyncMock()
    client.post.side_effect = [
        httpx.Response(400, json={"error": {
            "code": "json_validate_failed", "failed_generation": json.dumps(invalid),
        }}),
        httpx.Response(200, json={"choices": [{
            "message": {"content": sample().model_dump_json()}, "finish_reason": "stop",
        }]}),
    ]
    result = await extraction.extract_chunk(TEXT, "fir", replace(settings, groq_api_key="fake"), client)
    assert result == sample()
    request = client.post.call_args.kwargs["json"]
    assert request["response_format"] == {"type": "json_object"}
    assert "JSON schema:" in request["messages"][0]["content"]
    assert "entities.0.kind" in request["messages"][1]["content"]


@pytest.mark.parametrize("grounded", [True, False])
async def test_provider_rejected_json_requires_local_evidence(settings, grounded):
    import json

    payload = sample().model_dump()
    for item in payload["entities"] + payload["relationships"]:
        item["evidence"] = {"start_line": 1, "end_line": 1}
    if not grounded:
        payload["entities"][0]["name"] = "Invented Person"
    client = AsyncMock()
    client.post.return_value = httpx.Response(400, json={"error": {
        "code": "json_validate_failed", "failed_generation": json.dumps(payload),
    }})
    if grounded:
        result = await extraction.extract_chunk(TEXT, "fir", replace(settings, groq_api_key="fake"), client)
        assert result.entities[0].name == "Alice"
        assert client.post.await_count == 1
    else:
        with pytest.raises(extraction.ExtractionFailure, match=r"entities\[0\].name"):
            await extraction.extract_chunk(TEXT, "fir", replace(settings, groq_api_key="fake"), client)
        assert client.post.await_count == 2
