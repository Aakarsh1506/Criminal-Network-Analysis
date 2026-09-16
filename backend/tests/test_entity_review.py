import json
from dataclasses import replace
from unittest.mock import AsyncMock

import httpx
import pytest

from backend.errors import APIError
from backend.services import entity_review, extraction, local_entities
from backend.services.relationship_sentences import relationship_batches, sentence_spans


def entity(ref, name, kind="Person"):
    return extraction.Entity(ref=ref, name=name, kind=kind, identifier=None, attributes=[], evidence=name)


def reply(payload, local=True, finish="stop"):
    choice = {"message": {"content": json.dumps(payload)}, "finish_reason": finish}
    return httpx.Response(200, json={"done": True, "done_reason": finish, "message": choice["message"]}
                          if local else {"choices": [choice]})


@pytest.mark.parametrize("provider", ["ollama", "groq"])
async def test_every_candidate_is_checked_including_entities_without_relationships(settings, provider):
    entities = [entity("a", "Alice"), entity("b", "London", "Person"), entity("c", "9876543210", "PhoneNumber")]
    source = "Alice resides in London.\nPhone: 9876543210."
    client = AsyncMock()
    client.post.return_value = reply({"checks": [
        {"ref": "a", "kind": "Person", "valid": True},
        {"ref": "b", "kind": "Location", "valid": True},
        {"ref": "c", "kind": "PhoneNumber", "valid": True},
    ]}, local=provider == "ollama")
    result = await entity_review.verify_entities(source, extraction.Extraction(entities=entities, relationships=[]),
        replace(settings, extraction_provider=provider, groq_api_key="fake"), client)
    assert [(e.ref, e.name, e.kind) for e in result.entities] == [
        ("a", "Alice", "Person"), ("b", "London", "Location"), ("c", "9876543210", "PhoneNumber"),
    ]
    sent = json.loads(client.post.call_args.kwargs["json"]["messages"][1]["content"])["entities"]
    assert {e["ref"] for e in sent} == {"a", "b", "c"}
    assert all({"name", "kind", "context"} <= e.keys() for e in sent)
    assert sent[0]["context"] == "Alice resides in London."


@pytest.mark.parametrize("checks", [[], [{"ref": "invented", "kind": "Person", "valid": True}],
    [{"ref": "a", "kind": "Person", "valid": True}] * 2])
async def test_missing_duplicate_or_invented_checks_fail_without_silently_losing_entities(settings, checks):
    client = AsyncMock()
    client.post.return_value = reply({"checks": checks})
    with pytest.raises(APIError, match="entity checking was incomplete"):
        await entity_review.verify_entities("Alice met Bob.", extraction.Extraction(
            entities=[entity("a", "Alice"), entity("b", "Bob")], relationships=[]),
            replace(settings, extraction_provider="ollama"), client)
    assert client.post.await_count == 2


async def test_flagged_candidates_are_preserved_for_officer_review(settings):
    client = AsyncMock()
    client.post.return_value = reply({"checks": [{"ref": "a", "kind": "Person", "valid": False}]})
    result = await entity_review.verify_entities("Unknown phrase", extraction.Extraction(
        entities=[entity("a", "Unknown phrase")], relationships=[]),
        replace(settings, extraction_provider="ollama"), client)
    assert result.entities == []
    assert result.excluded_entities[0].name == "Unknown phrase"


async def test_entity_checking_covers_every_batch_without_limiting_total_candidates(settings):
    entities = [entity(f"e{i}", f"Candidate {i}") for i in range(19)]
    seen = []
    async def post(*args, **kwargs):
        candidates = json.loads(kwargs["json"]["messages"][1]["content"])["entities"]
        seen.extend(e["ref"] for e in candidates)
        return reply({"checks": [{"ref": e["ref"], "kind": e["kind"], "valid": True} for e in candidates]})
    client = AsyncMock()
    client.post.side_effect = post
    result = await entity_review.verify_entities("; ".join(e.name for e in entities),
        extraction.Extraction(entities=entities, relationships=[]),
        replace(settings, extraction_provider="ollama", ollama_max_tokens=1024), client)
    assert seen == [e.ref for e in entities]
    assert len(result.entities) == 19
    assert client.post.await_count == 3


async def test_entity_checking_retains_groq_rate_limit_backoff(settings, monkeypatch):
    client = AsyncMock()
    client.post.side_effect = [httpx.Response(429, headers={"retry-after": "20"}),
        reply({"checks": [{"ref": "a", "kind": "Person", "valid": True}]}, local=False)]
    sleep = AsyncMock()
    monkeypatch.setattr(entity_review.asyncio, "sleep", sleep)
    result = await entity_review.verify_entities("Alice", extraction.Extraction(
        entities=[entity("a", "Alice")], relationships=[]), replace(settings, groq_api_key="fake"), client)
    assert result.entities[0].name == "Alice"
    sleep.assert_awaited_once_with(20)


async def test_hybrid_checks_entities_then_sends_full_cue_sentences(settings, monkeypatch):
    text = "Alice contacted Bob after the meeting. Carol arrived independently."
    local = extraction.Extraction(entities=[entity("a", "Alice"), entity("b", "Bob"), entity("c", "Carol")], relationships=[])
    monkeypatch.setattr(local_entities, "extract_local", lambda *args: local)
    client = AsyncMock()
    client.post.side_effect = [
        reply({"checks": [{"ref": e.ref, "kind": e.kind, "valid": True} for e in local.entities]}),
        reply({"relationships": [{"subject": "a", "predicate": "CONTACTED", "object": "b", "start_line": 1, "end_line": 1}]}),
    ]
    result = await local_entities.extract_hybrid(text, "fir", replace(settings, extraction_provider="ollama"), client)
    requests = [json.loads(c.kwargs["json"]["messages"][1]["content"]) for c in client.post.call_args_list]
    assert "source_lines" not in requests[0]
    assert requests[1]["source_lines"][0]["text"] == "Alice contacted Bob after the meeting."
    assert {e.ref for e in result.entities} == {"a", "b", "c"}
    assert result.relationships[0].evidence == "Alice contacted Bob after the meeting."


def test_pronouns_and_negation_keep_complete_antecedent_sentence():
    text = "Alice arrived in London. She did not contact Bob despite repeated requests."
    batches = list(relationship_batches(text, [entity("a", "Alice"), entity("b", "Bob")], 1024))
    assert len(batches) == 1
    assert text in batches[0][0]


def test_long_sentence_is_never_cut_at_a_character_or_line_limit():
    text = "Alice contacted Bob " + "after reviewing the earlier records " * 100 + "yesterday."
    batches = list(relationship_batches(text, [entity("a", "Alice"), entity("b", "Bob")], 256))
    assert len(batches) == 1
    assert batches[0][0] == text


def test_keyword_does_not_create_relationship_or_drop_unrelated_entities():
    assert list(relationship_batches("Alice enjoys chess. Bob prefers tennis.",
                                    [entity("a", "Alice"), entity("b", "Bob")])) == []


def test_wrapped_pdf_sentence_is_kept_intact():
    text = "Alice contacted\n\nBob regarding the warehouse\n\nmeeting."
    assert len(sentence_spans(text)) == 1
    assert list(relationship_batches(text, [entity("a", "Alice"), entity("b", "Bob")]))[0][0] == text


async def test_failed_group_retries_complete_sentences_once_without_rechecking_entities(settings, monkeypatch):
    text = "Alice contacted Bob. Alice resides in London."
    local = extraction.Extraction(entities=[entity("a", "Alice"), entity("b", "Bob"),
                                 entity("l", "London", "Location")], relationships=[])
    monkeypatch.setattr(local_entities, "extract_local", lambda *args: local)
    review = AsyncMock(return_value=local)
    monkeypatch.setattr(local_entities, "verify_entities", review)
    async def extract(passage, *args, catalog):
        if passage == text:
            raise extraction.ExtractionFailure("Response token limit reached.", 502)
        assert passage.strip() in ["Alice contacted Bob.", "Alice resides in London."]
        return extraction.Extraction(entities=catalog, relationships=[extraction.Relationship(
            subject="a", predicate="CONTACTED" if "contacted" in passage else "RESIDES_IN",
            object="b" if "contacted" in passage else "l", evidence=passage.strip())])
    extract_mock = AsyncMock(side_effect=extract)
    monkeypatch.setattr(local_entities, "extract_chunk", extract_mock)
    result = await local_entities.extract_hybrid(text, "fir", settings, AsyncMock())
    assert {r.predicate for r in result.relationships} == {"CONTACTED", "RESIDES_IN"}
    assert extract_mock.await_count == 3
    review.assert_awaited_once()


async def test_sentence_retry_failure_is_not_recursively_retried_or_silently_accepted(settings, monkeypatch):
    text = "Alice contacted Bob. Alice contacted Bob yesterday."
    local = extraction.Extraction(entities=[entity("a", "Alice"), entity("b", "Bob")], relationships=[])
    monkeypatch.setattr(local_entities, "extract_local", lambda *args: local)
    monkeypatch.setattr(local_entities, "verify_entities", AsyncMock(return_value=local))
    extract = AsyncMock(side_effect=extraction.ExtractionFailure("Truncated", 502))
    monkeypatch.setattr(local_entities, "extract_chunk", extract)
    with pytest.raises(extraction.ExtractionFailure):
        await local_entities.extract_hybrid(text, "fir", settings, AsyncMock())
    assert extract.await_count == 2
