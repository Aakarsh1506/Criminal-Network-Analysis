from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from backend.errors import APIError
from backend.services import extraction, ingestion, local_entities


@pytest.mark.parametrize("fails", [False, True])
async def test_worker_persists_monotonic_progress_and_stops_on_failure(settings, monkeypatch, fails):
    async def extract(*args, progress):
        await progress(30, "Starting batch 1 of 2")
        await progress(60, "Completed batch 1 of 2")
        await progress(50, "Retrying a smaller section")
        if fails:
            raise APIError("Output was truncated", 502)
        await progress(90, "Completed batch 2 of 2")
        return extraction.Extraction(entities=[], relationships=[])

    monkeypatch.setattr(ingestion, "extract_entities", extract)
    state = SimpleNamespace(settings=settings, db=AsyncMock(), http_client=AsyncMock())
    await ingestion.process_document(state, {
        "document_id": 1, "extracted_text": "Example", "source_type": "fir",
    })
    updates = [
        call.args[1][0].obj for call in state.db.query.call_args_list
        if "SET processing_progress=%s" in call.args[0]
    ]
    percents = [update["percent"] for update in updates]
    assert percents == sorted(percents)
    assert updates[4]["percent"] == 60
    final_sql = state.db.query.call_args.args[0]
    if fails:
        assert "'failed'" in final_sql
        assert max(percents) < 100
        assert '"percent":100' not in final_sql
    else:
        assert "'awaiting_review'" in final_sql
        assert '"percent":100' in final_sql


async def test_hybrid_progress_counts_completed_batches(settings, monkeypatch):
    result = extraction.Extraction(entities=[], relationships=[])
    monkeypatch.setattr(local_entities, "extract_local", lambda *args: result)
    monkeypatch.setattr(local_entities, "relevant_batches", lambda *args: [("a", []), ("b", [])])
    extract = AsyncMock(return_value=result)
    monkeypatch.setattr(local_entities, "extract_chunk", extract)
    progress = AsyncMock()
    await local_entities.extract_hybrid("ab", "fir", settings, AsyncMock(), progress=progress)
    assert extract.await_count == 2
    assert [call.args[0] for call in progress.call_args_list] == [20, 30, 60, 60, 90]
    assert progress.call_args.args == (90, "Extracted relationships: 2 of 2 batches")


async def test_full_extraction_progress_counts_sections(settings, monkeypatch):
    monkeypatch.setattr(extraction, "extract_chunk", AsyncMock(
        return_value=extraction.Extraction(entities=[], relationships=[]),
    ))
    progress = AsyncMock()
    await extraction.extract_entities("a" * 7000, "fir", settings, AsyncMock(), progress=progress)
    assert [call.args[0] for call in progress.call_args_list] == [20, 55, 55, 90]
    assert progress.call_args.args == (90, "Extracted 2 of 2 sections")


async def test_document_api_exposes_persisted_progress(officer_client, db):
    progress = {"percent": 60, "label": "Extracted relationships: 1 of 2 batches"}
    db.query.return_value = [{
        "document_id": 1, "original_name": "test.txt", "mime_type": "text/plain",
        "size_bytes": 10, "uploaded_at": "2026-09-10", "processing_status": "processing",
        "processing_progress": progress,
    }]
    for path in ("/api/documents", "/api/documents/1"):
        response = await officer_client.get(path)
        assert response.status_code == 200
        body = response.json()
        assert (body[0] if isinstance(body, list) else body)["progress"] == progress
