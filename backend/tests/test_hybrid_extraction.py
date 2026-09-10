import json
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from backend.errors import APIError
from backend.services import extraction, local_entities


@pytest.fixture
def local_pipeline(monkeypatch):
    monkeypatch.setattr(
        local_entities, "load_pipeline", lambda _: lambda text: SimpleNamespace(ents=[])
    )


def response(payload, status=200, headers=None):
    body = {"choices": [{"message": {"content": json.dumps(payload)}, "finish_reason": "stop"}]}
    return httpx.Response(status, json=body if status == 200 else payload, headers=headers)


def test_regex_and_explicit_fields_keep_source_evidence(local_pipeline):
    text = "FIR/2026/0417\nName: Rahul Sharma\nAge: 34\nPhone: 9876543210\n\nVehicle: MH02AB1234\nCrime type: Fraud"
    result = local_entities.extract_local(text, "test")
    by_name = {e.name: e for e in result.entities}
    assert by_name["FIR/2026/0417"].kind == "Case"
    assert by_name["9876543210"].kind == "PhoneNumber"
    assert by_name["MH02AB1234"].kind == "Vehicle"
    assert by_name["Fraud"].kind == "CrimeType"
    assert {a.key: a.value for a in by_name["Rahul Sharma"].attributes} == {
        "age": "34",
        "phone": "9876543210",
    }
    assert by_name["Rahul Sharma"].evidence in text
    assert result.relationships == []


def test_ner_maps_people_organizations_and_places(monkeypatch):
    text = "Alice met Acme in London."
    spans = [
        SimpleNamespace(
            text=name,
            start_char=text.index(name),
            end_char=text.index(name) + len(name),
            label_=label,
        )
        for name, label in [("Alice", "PERSON"), ("Acme", "ORG"), ("London", "GPE")]
    ]
    monkeypatch.setattr(
        local_entities, "load_pipeline", lambda _: lambda text: SimpleNamespace(ents=spans)
    )
    result = local_entities.extract_local(text, "test")
    assert [(e.name, e.kind) for e in result.entities] == [
        ("Alice", "Person"),
        ("Acme", "Organization"),
        ("London", "Location"),
    ]


def test_passages_omit_unrelated_text_and_keep_negation(local_pipeline):
    text = (
        "irrelevant boilerplate\n" * 100
        + "Name: Alice\nName: Bob\nAlice did not contact Bob.\n"
        + "footer\n" * 100
    )
    entities = local_entities.extract_local(text, "test").entities
    batches = list(local_entities.relevant_batches(text, entities))
    assert len(batches) == 1
    assert "Alice did not contact Bob." in batches[0][0]
    assert len(batches[0][0]) < len(text) / 4


@pytest.mark.asyncio
async def test_hybrid_sends_only_relationship_schema_and_preserves_entities(
    settings, local_pipeline
):
    text = "Name: Alice\nName: Bob\nAlice contacted Bob."
    local = local_entities.extract_local(text, "test")
    alice, bob = local.entities
    relationship = {
        "subject": alice.ref,
        "predicate": "CONTACTED",
        "object": bob.ref,
        "evidence": {"start_line": 3, "end_line": 3},
    }
    client = SimpleNamespace(
        post=AsyncMock(return_value=response({"relationships": [relationship]}))
    )
    result = await extraction.extract_entities(
        text, "fir", replace(settings, extraction_mode="hybrid", groq_api_key="fake"), client
    )
    assert result.entities == local.entities
    assert result.relationships[0].evidence == "Alice contacted Bob."
    request = client.post.call_args.kwargs["json"]
    assert set(request["response_format"]["json_schema"]["schema"]["properties"]) == {
        "relationships"
    }
    assert request["max_completion_tokens"] == 2048
    assert {e["ref"] for e in json.loads(request["messages"][1]["content"])["entities"]} == {
        alice.ref,
        bob.ref,
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "invalid",
    [
        {"relationships": [], "entities": []},
        {
            "relationships": [
                {
                    "subject": "invented",
                    "predicate": "CONTACTED",
                    "object": "unknown",
                    "evidence": {"start_line": 1, "end_line": 1},
                }
            ]
        },
        {
            "relationships": [
                {
                    "subject": "a",
                    "predicate": "USES_PHONE",
                    "object": "b",
                    "evidence": {"start_line": 1, "end_line": 1},
                }
            ]
        },
    ],
)
async def test_hybrid_rejects_invented_entities_refs_and_predicates(
    settings, local_pipeline, invalid
):
    text = "Name: Alice\nName: Bob\nAlice contacted Bob."
    client = SimpleNamespace(post=AsyncMock(return_value=response(invalid)))
    with pytest.raises(extraction.ExtractionFailure):
        await extraction.extract_entities(
            text, "fir", replace(settings, extraction_mode="hybrid", groq_api_key="fake"), client
        )
    assert client.post.await_count == 2


@pytest.mark.asyncio
async def test_hybrid_no_candidates_uses_no_api(settings, local_pipeline):
    client = SimpleNamespace(post=AsyncMock())
    result = await extraction.extract_entities(
        "Nothing here.", "fir", replace(settings, extraction_mode="hybrid"), client
    )
    assert result.entities == result.relationships == []
    client.post.assert_not_awaited()


@pytest.mark.asyncio
async def test_hybrid_retains_rate_limit_backoff(settings, local_pipeline, monkeypatch):
    sleep = AsyncMock()
    monkeypatch.setattr(extraction.asyncio, "sleep", sleep)
    client = SimpleNamespace(
        post=AsyncMock(
            side_effect=[response({}, 429, {"retry-after": "25"}), response({"relationships": []})]
        )
    )
    await extraction.extract_entities(
        "Name: Alice\nName: Bob",
        "fir",
        replace(settings, extraction_mode="hybrid", groq_api_key="fake"),
        client,
    )
    sleep.assert_awaited_once_with(25)


def test_missing_spacy_model_is_actionable():
    with pytest.raises(APIError, match="Hybrid extraction needs spaCy"):
        local_entities.load_pipeline("missing_cna_test_model")


def test_installed_spacy_model_smoke():
    result = local_entities.extract_local("Barack Obama visited London.", "en_core_web_sm")
    assert any(e.name == "Barack Obama" and e.kind == "Person" for e in result.entities)
    assert any(e.name == "London" and e.kind == "Location" for e in result.entities)


@pytest.mark.asyncio
async def test_hybrid_provider_schema_error_retries_relationships_only(settings, local_pipeline):
    invalid = {
        "relationships": [
            {
                "subject": "e1",
                "predicate": "VISITED",
                "object": "e2",
                "evidence": {"start_line": 1, "end_line": 1},
            }
        ]
    }
    client = SimpleNamespace(
        post=AsyncMock(
            side_effect=[
                response(
                    {
                        "error": {
                            "code": "json_validate_failed",
                            "failed_generation": json.dumps(invalid),
                        }
                    },
                    400,
                ),
                response({"relationships": []}),
            ]
        )
    )
    await extraction.extract_entities(
        "Name: Alice\nName: Bob",
        "fir",
        replace(settings, extraction_mode="hybrid", groq_api_key="fake"),
        client,
    )
    request = client.post.call_args.kwargs["json"]
    assert request["response_format"] == {"type": "json_object"}
    correction = json.loads(request["messages"][1]["content"])["correction"]
    assert correction["invalid_fields"][0]["unsupported_predicate"] == "VISITED"


@pytest.mark.asyncio
async def test_hybrid_rejects_evidence_crossing_omitted_text(settings, local_pipeline):
    text = "Name: Alice\n" + "unrelated\n" * 20 + "Name: Bob\n"

    async def post(*args, **kwargs):
        request = json.loads(kwargs["json"]["messages"][1]["content"])
        lines = request["source_lines"]
        assert any("[OMITTED SOURCE]" in line["text"] for line in lines)
        return response(
            {
                "relationships": [
                    {
                        "subject": "e1",
                        "predicate": "CONTACTED",
                        "object": "e2",
                        "evidence": {"start_line": 1, "end_line": len(lines)},
                    }
                ]
            }
        )

    client = SimpleNamespace(post=AsyncMock(side_effect=post))
    with pytest.raises(extraction.EvidenceError):
        await extraction.extract_entities(
            text, "fir", replace(settings, extraction_mode="hybrid", groq_api_key="fake"), client
        )


def test_batches_remain_bounded_and_preserve_late_mentions(local_pipeline):
    text = (
        "Name: Alice\nName: Bob\n"
        + ("Alice did not contact Bob. " * 200)
        + "\nAlice contacted Bob yesterday."
    )
    entities = local_entities.extract_local(text, "test").entities
    batches = list(local_entities.relevant_batches(text, entities))
    assert len(batches) > 1
    assert all(len(passage) <= 3500 for passage, _ in batches)
    assert "Alice contacted Bob yesterday." in batches[-1][0]


def test_location_saves_complete_sentence_with_real_model():
    text = "The report was filed yesterday. Barack Obama lives in London. A separate inquiry continues."
    result = local_entities.extract_local(text, "en_core_web_sm")
    location = next(e for e in result.entities if e.name == "London")
    assert location.evidence == "Barack Obama lives in London."
    assert location.evidence in text
    assert result.relationships == []


@pytest.mark.asyncio
async def test_location_context_reaches_groq_and_review(settings):
    text = "Barack Obama lives in London."

    async def post(*args, **kwargs):
        request = json.loads(kwargs["json"]["messages"][1]["content"])
        location = next(e for e in request["entities"] if e["kind"] == "Location")
        person = next(e for e in request["entities"] if e["kind"] == "Person")
        assert location["context"] == text
        return response(
            {
                "relationships": [
                    {
                        "subject": person["ref"],
                        "predicate": "RESIDES_IN",
                        "object": location["ref"],
                        "evidence": {"start_line": 1, "end_line": 1},
                    }
                ]
            }
        )

    result = await extraction.extract_entities(
        text,
        "fir",
        replace(settings, extraction_mode="hybrid", groq_api_key="fake"),
        SimpleNamespace(post=AsyncMock(side_effect=post)),
    )
    assert next(e for e in result.entities if e.kind == "Location").evidence == text
    assert result.relationships[0].predicate == "RESIDES_IN"
    assert result.relationships[0].evidence == text
    assert extraction.Extraction.model_validate_json(result.model_dump_json()) == result


def test_location_sentence_is_not_lost_at_batch_boundary():
    sentence = "Alice " + "was reportedly " * 60 + "seen in London."
    text = "Alice reported Bob. " * 145 + sentence
    person = extraction.Entity(
        ref="a", kind="Person", name="Alice", identifier=None, attributes=[], evidence="Alice"
    )
    place = extraction.Entity(
        ref="l", kind="Location", name="London", identifier=None, attributes=[], evidence=sentence
    )
    batches = list(local_entities.relevant_batches(text, [person, place]))
    assert any(
        sentence in passage and next(e for e in catalog if e.ref == "l").evidence == sentence
        for passage, catalog in batches
        if any(e.ref == "l" for e in catalog)
    )


@pytest.mark.parametrize("predicate", ["RESIDES_IN", "SEEN_AT"])
def test_person_location_direction_is_validated(predicate):
    text = "Alice lives in London."
    person = extraction.Entity(
        ref="a", kind="Person", name="Alice", identifier=None, attributes=[], evidence="Alice"
    )
    place = extraction.Entity(
        ref="l", kind="Location", name="London", identifier=None, attributes=[], evidence=text
    )
    relationship = extraction.Relationship(
        subject="a", predicate=predicate, object="l", evidence=text
    )
    result = extraction.Extraction(entities=[person, place], relationships=[relationship])
    extraction.validate_extraction(result, text)
    relationship.subject, relationship.object = "l", "a"
    with pytest.raises(extraction.RelationshipError):
        extraction.validate_extraction(result, text)


def test_oversized_location_context_retains_negation_and_exact_quote():
    text = "prefix " * 400 + "Alice does not live in London" + " suffix" * 400
    start = text.index("London")
    quote = local_entities.location_context(text, start, start + len("London"), [(0, len(text))])
    assert len(quote) <= 2000
    assert quote in text
    assert "Alice does not live in London" in quote


@pytest.mark.parametrize(
    "place", ["Bandra Kurla Complex", "Bandra-Kurla Complex", "Khar West", "khar west"]
)
def test_named_local_places_are_locations_not_people(place):
    result = local_entities.extract_local(f"A person was seen at {place}.", "en_core_web_sm")
    matching = [e for e in result.entities if e.name.casefold() == place.casefold()]
    assert len(matching) == 1
    assert matching[0].kind == "Location"
    assert matching[0].evidence == f"A person was seen at {place}."
    assert not any(
        e.kind == "Person" and e.name.casefold() in place.casefold() for e in result.entities
    )


def test_address_fields_override_statistical_person_predictions(monkeypatch):
    text = "Name: Alice\nAddress: Example Gardens\nLocation: Unknown District"

    def nlp(text):
        return SimpleNamespace(
            ents=[
                SimpleNamespace(
                    label_="PERSON",
                    start_char=text.index(name),
                    end_char=text.index(name) + len(name),
                )
                for name in ["Example Gardens", "Unknown District"]
            ]
        )

    monkeypatch.setattr(local_entities, "load_pipeline", lambda _: nlp)
    result = local_entities.extract_local(text, "test")
    assert [(e.name, e.kind) for e in result.entities] == [
        ("Alice", "Person"),
        ("Example Gardens", "Location"),
        ("Unknown District", "Location"),
    ]
