from types import SimpleNamespace

import pytest

from backend.services.crime_terms import is_explicit_crime_field
from backend.services.local_entities import extract_local
from backend.services.relationship_sentences import relationship_batches


@pytest.fixture
def local_only(monkeypatch):
    # Crime candidates must not depend on generic NER recognizing an offence.
    monkeypatch.setattr("backend.services.local_entities.load_pipeline",
                        lambda _: lambda text: SimpleNamespace(ents=[]))


def test_unlabelled_complaint_extracts_crime_and_preserves_allegation():
    text = "FIR/2026/0589\n\nNature of Complaint\n\nSuspected financial fraud and coordinated movement of funds."
    result = extract_local(text, "en_core_web_sm")
    crimes = [e for e in result.entities if e.kind == "CrimeType"]
    assert [e.name for e in crimes] == ["financial fraud"]
    assert "Suspected financial fraud" in crimes[0].evidence
    assert crimes[0].evidence in text
    assert result.relationships == []  # AI still decides which case this describes.


@pytest.mark.parametrize("phrase,expected", [
    ("financial\n\nfraud", "financial fraud"),
    ("attempted murder", "attempted murder"),
    ("identity theft", "identity theft"),
    ("money laundering", "money laundering"),
])
def test_crime_phrases_preserve_specific_type_without_duplicate_generic_tag(local_only, phrase, expected):
    result = extract_local(f"The complaint alleges {phrase}.", "test")
    assert [e.name for e in result.entities if e.kind == "CrimeType"] == [expected]


def test_fund_movement_alone_is_not_renamed_as_money_laundering(local_only):
    result = extract_local("Coordinated movement of funds was observed.", "test")
    assert not any(e.kind == "CrimeType" for e in result.entities)


def test_crime_vocabulary_does_not_suppress_organization_candidates(monkeypatch):
    name = "Fraud Prevention Unit"
    monkeypatch.setattr("backend.services.local_entities.load_pipeline", lambda _: lambda text:
        SimpleNamespace(ents=[SimpleNamespace(label_="ORG", start_char=0, end_char=len(name))]))
    result = extract_local(f"{name} reviewed the file.", "test")
    assert any(e.kind == "Organization" and e.name == name for e in result.entities)


def test_crime_sentence_reaches_ai_without_other_relationship_keywords(local_only):
    text = "FIR/2026/0589. The allegations concern financial fraud."
    result = extract_local(text, "test")
    batches = list(relationship_batches(text, result.entities, 1024))
    assert any("The allegations concern financial fraud." in passage for passage, _ in batches)
    assert any(any(e.kind == "CrimeType" for e in catalog) for _, catalog in batches)


@pytest.mark.parametrize("evidence,name,expected", [
    ("Crime type: Fraud", "Fraud", True),
    ("Offence: Financial fraud", "Financial fraud", True),
    ("No crime of fraud was established.", "fraud", False),
    ("Crime: Theft\nFraud was ruled out.", "Fraud", False),
    ("Nature of Complaint\nSuspected financial fraud", "financial fraud", False),
])
def test_single_case_fallback_requires_a_matching_labelled_field(evidence, name, expected):
    assert is_explicit_crime_field(evidence, name) is expected
