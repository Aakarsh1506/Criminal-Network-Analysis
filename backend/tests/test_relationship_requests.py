"""Local relationship requests must stay small without weakening source checks."""

import json
from dataclasses import replace
from unittest.mock import AsyncMock

import httpx
import pytest

from backend.services import extraction, local_entities


def entity(ref, kind, name):
    return extraction.Entity(ref=ref, kind=kind, name=name, identifier=None,
                             attributes=[], evidence=name)


def response(relationships, reason="stop"):
    return httpx.Response(200, json={"done": True, "done_reason": reason,
        "message": {"content": json.dumps({"relationships": relationships})}})


def link(**overrides):
    return dict(subject="a", predicate="CONTACTED", object="b", start_line=1,
                end_line=1) | overrides


def test_native_schema_prevents_empty_overlong_reversed_and_omitted_evidence_ranges():
    text = "\nAlice contacted Bob.\n" + ("x" * 680 + "\n") * 4 + "\n[OMITTED SOURCE]\nBob called Alice.\n"
    lines = extraction.source_lines(text)
    catalog = [entity("a", "Person", "Alice"), entity("b", "Person", "Bob")]
    schema = extraction.compact_relationship_schema(catalog, text)
    allowed = set()
    for variant in schema["properties"]["relationships"]["items"]["anyOf"]:
        fields = variant["properties"]
        for start in fields["start_line"]["enum"]:
            for end in fields["end_line"]["enum"]:
                quote = "".join(lines[start - 1:end]).strip()
                assert 1 <= start <= end <= len(lines)
                assert 0 < len(quote) <= 2000
                assert "[OMITTED SOURCE]" not in quote
                allowed.add((start, end))
    assert (1, 1) not in allowed
    assert (2, 6) not in allowed
    assert (2, 2) in allowed
    assert (3, 4) in allowed  # Legitimate multi-line evidence stays available.
    assert (len(lines), len(lines)) in allowed


async def test_overlong_evidence_correction_keeps_exact_source_quote(settings):
    text = "Alice contacted Bob.\n" + ("x" * 680 + "\n") * 3
    catalog = [entity("a", "Person", "Alice"), entity("b", "Person", "Bob")]
    client = AsyncMock()
    client.post.side_effect = [response([link(end_line=4)]), response([link()])]
    result = await extraction.extract_chunk(text, "fir",
        replace(settings, extraction_provider="ollama"), client, catalog=catalog)
    assert result.relationships[0].evidence == "Alice contacted Bob."
    correction = json.loads(client.post.call_args.kwargs["json"]["messages"][1]["content"])["correction"]
    assert "Evidence lines 1-4" in correction["validation_error"]


async def test_compact_output_restores_exact_evidence_and_constrains_endpoint_types(settings):
    catalog = [entity("a", "Person", "Alice"), entity("b", "Person", "Bob"),
               entity("c", "Case", "FIR/2026/1")]
    text = "Alice contacted Bob.\nFIR/2026/1"
    client = AsyncMock()
    client.post.return_value = response([link()])
    result = await extraction.extract_chunk(text, "fir", replace(settings, extraction_provider="ollama"),
                                            client, catalog=catalog)
    assert result.relationships[0].evidence == "Alice contacted Bob."
    assert len(result.entities) == 3
    request = client.post.call_args.kwargs["json"]
    variants = request["format"]["properties"]["relationships"]["items"]["anyOf"]
    for variant in variants:
        fields = variant["properties"]
        predicate = fields["predicate"]["enum"][0]
        subjects, objects = extraction.RELATION_RULES[predicate]
        assert fields["subject"]["enum"] == [e.ref for e in catalog if e.kind in subjects]
        assert fields["object"]["enum"] == [e.ref for e in catalog if e.kind in objects]
        assert fields["end_line"]["maximum"] == 2
    assert "JSON schema:" not in request["messages"][0]["content"]


@pytest.mark.parametrize("invalid", [
    link(start_line=0), link(end_line=3), link(start_line=2, end_line=1),
    link(subject="invented"), link(predicate="OWNS"),
    link(extra="unexpected"), link(start_line=True),
])
async def test_compact_output_still_requires_validation_and_one_correction(settings, invalid):
    catalog = [entity("a", "Person", "Alice"), entity("b", "Person", "Bob")]
    client = AsyncMock()
    client.post.side_effect = [response([invalid]), response([link()])]
    result = await extraction.extract_chunk("Alice contacted Bob.\nFooter", "fir",
        replace(settings, extraction_provider="ollama"), client, catalog=catalog)
    assert client.post.await_count == 2
    assert [(r.subject, r.predicate, r.object) for r in result.relationships] == [("a", "CONTACTED", "b")]


async def test_compact_output_cannot_attach_another_persons_quote(settings):
    catalog = [entity("a", "Person", "Alice"), entity("b", "Person", "Bob"),
               entity("c", "Person", "Carol")]
    client = AsyncMock()
    client.post.return_value = response([link(object="c")])
    result = await extraction.extract_chunk("Alice contacted Bob.\nCarol was elsewhere.", "fir",
        replace(settings, extraction_provider="ollama"), client, catalog=catalog)
    assert result.relationships == []
    assert len(result.excluded_relationships) == 1


async def test_compact_truncated_output_is_not_accepted_as_complete(settings):
    catalog = [entity("a", "Person", "Alice"), entity("b", "Person", "Bob")]
    client = AsyncMock()
    client.post.return_value = response([link()], reason="length")
    with pytest.raises(extraction.ExtractionFailure, match="token limit"):
        await extraction.extract_chunk("Alice contacted Bob.", "fir",
            replace(settings, extraction_provider="ollama", ollama_max_tokens=1024),
            client, catalog=catalog)
    assert [call.kwargs["json"]["options"]["num_predict"]
            for call in client.post.call_args_list] == [1024, 2048]


@pytest.mark.parametrize("fixed", [False, True])
async def test_correction_preserves_valid_edges_and_reviews_unfixed_ones(settings, fixed):
    text = "Alice contacted Bob.\nAlice contacted Carol."
    catalog = [entity("a", "Person", "Alice"), entity("b", "Person", "Bob"),
               entity("c", "Person", "Carol")]
    client = AsyncMock()
    client.post.side_effect = [
        response([link(), link(object="c")]),
        response([link(object="c", start_line=2, end_line=2)] if fixed else []),
    ]
    result = await extraction.extract_chunk(text, "fir",
        replace(settings, extraction_provider="ollama"), client, catalog=catalog)
    assert result.relationships[0].evidence == "Alice contacted Bob."
    assert len(result.relationships) == (2 if fixed else 1)
    assert len(result.excluded_relationships) == (0 if fixed else 1)
    correction = json.loads(client.post.call_args.kwargs["json"]["messages"][1]["content"])["correction"]
    assert "does not identify" in correction["validation_error"]
    assert correction["previous_extraction"] is None


def test_low_budget_splits_dense_rows_without_losing_source_or_single_case_context():
    rows = [f"Alice contacted Bob at 12:{i:02d}.\n" for i in range(40)]
    text = "FIR/2026/1\n" + "".join(rows)
    catalog = [entity("a", "Person", "Alice"), entity("b", "Person", "Bob"),
               entity("c", "Case", "FIR/2026/1")]
    small = list(local_entities.relevant_batches(text, catalog, 1024))
    large = list(local_entities.relevant_batches(text, catalog, 4096))
    assert len(small) > len(large)
    assert all(any(row.strip() in passage for passage, _ in small) for row in rows)
    assert all({e.ref for e in entities} == {"a", "b", "c"} for _, entities in small)
    assert all(len(extraction.source_lines(passage)) <= 18 for passage, _ in small)


def test_multicase_batch_does_not_inject_unrelated_case_header():
    text = "FIR/2026/1\n" + "Alice contacted Bob.\n" * 30 + "FIR/2026/2\n"
    catalog = [entity("a", "Person", "Alice"), entity("b", "Person", "Bob"),
               entity("c", "Case", "FIR/2026/1"), entity("d", "Case", "FIR/2026/2")]
    batches = list(local_entities.relevant_batches(text, catalog, 512))
    assert all("FIR/2026/1" not in passage for passage, _ in batches[1:])
    assert all("FIR/2026/2" not in passage for passage, _ in batches[:-1])


def test_dense_people_split_before_small_model_confuses_identities():
    people = [f"Person {i:02d}" for i in range(12)]
    rows = [f"{name} witnessed FIR/2026/1.\n{name} resides in Mumbai.\n" for name in people]
    text = "FIR/2026/1\n" + "".join(rows)
    catalog = [entity("case", "Case", "FIR/2026/1"), entity("city", "Location", "Mumbai")]
    catalog += [entity(f"p{i}", "Person", name) for i, name in enumerate(people)]
    batches = list(local_entities.relevant_batches(text, catalog, 1024))
    assert len(batches) >= 3
    assert all(len(entities) <= 6 for _, entities in batches)
    assert all(any(sentence.strip() in passage for passage, _ in batches)
               for row in rows for sentence in row.splitlines())


def test_short_output_budget_preserves_long_lines_and_negation():
    text = ("Alice did not contact Bob. " * 100) + "\nAlice contacted Bob yesterday."
    catalog = [entity("a", "Person", "Alice"), entity("b", "Person", "Bob")]
    passages = [p for p, _ in local_entities.relevant_batches(text, catalog, 256)]
    assert all(len(p) <= 1400 for p in passages)
    assert any("Alice did not contact Bob." in p for p in passages)
    assert "Alice contacted Bob yesterday." in passages[-1]
