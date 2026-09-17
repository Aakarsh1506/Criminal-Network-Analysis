"""Statistical NER noise is trimmed or discarded before entity review."""

from types import SimpleNamespace

import pytest

from backend.services import local_entities
from backend.services.entity_spans import clean_span

FIR = (
    "Police Station Bandra Police Station, Mumbai\n"
    "FIR No. FIR/2026/0589\n"
    "Date of Registration 09 September 2026\n"
    "Investigating Officer Inspector Neha Kulkarni\n"
    "Name: Anita Desai\n"
    "Age: 39 years\n"
    "2. Persons Referred to in the Complaint\n"
    "• Sameer Khan, approximately 33 years old, reportedly residing in Thane, Maharashtra.\n"
    "On 04 September 2026, INR 3,20,000 was transferred at 14:15 hrs.\n"
    # PDF text keeps a trailing space where a long name wraps onto the next line.
    "Arjun Malhotra has links with Meridian Freight \n"
    "Solutions Pvt. Ltd., operating from Mumbai.\n"
    "Police Station: Bandra Police Station\n"
)


def fake_ner(predictions):
    """Return spaCy-like entities for (source text, label) pairs, in source order."""
    def nlp(text):
        ents, cursor = [], 0
        for value, label in predictions:
            start = text.index(value, cursor if value in text[cursor:] else 0)
            cursor = start + len(value)
            ents.append(SimpleNamespace(label_=label, start_char=start, end_char=cursor))
        return SimpleNamespace(ents=sorted(ents, key=lambda e: e.start_char))
    return nlp


def names(result, kind=None):
    return sorted(e.name for e in result.entities if kind is None or e.kind == kind)


@pytest.mark.parametrize("span,kind", [
    ("09 September 2026", "PERSON"), ("Age", "GPE"), ("14:15", "LOC"), ("INR 3,20,000", "PERSON"),
    ("Persons Referred", "ORG"), ("Page 1", "ORG"), ("• Available", "ORG"), ("Ltd.", "GPE"),
    ("-", "GPE"), ("2026", "GPE"), ("Approximately", "GPE"),
])
def test_form_labels_dates_amounts_and_bullets_are_not_names(span, kind):
    text = f"Header\n{span} was recorded.\n"
    start = text.index(span)
    mapped = local_entities.NER_KINDS.get(kind)
    assert clean_span(text, start, start + len(span), mapped) == []


def test_realistic_fir_noise_leaves_only_names(monkeypatch):
    monkeypatch.setattr(local_entities, "load_pipeline", lambda _: fake_ner([
        ("Bandra", "GPE"), ("09 September 2026", "PERSON"), ("Registration", "GPE"),
        ("Neha Kulkarni", "PERSON"), ("Age", "GPE"), ("Persons Referred", "ORG"),
        ("• Sameer Khan", "PERSON"), ("Thane", "ORG"), ("Maharashtra", "GPE"),
        ("04 September 2026", "PERSON"), ("INR 3,20,000", "PERSON"), ("14:15", "LOC"),
        ("Arjun Malhotra", "PERSON"), ("Meridian Freight \nSolutions Pvt", "ORG"),
        ("Ltd.", "GPE"), ("Mumbai.\nPolice", "LOC"),
    ]))
    result = local_entities.extract_local(FIR, "test")
    assert names(result, "Person") == ["Anita Desai", "Arjun Malhotra", "Neha Kulkarni", "Sameer Khan"]
    assert names(result, "Organization") == [
        "Bandra Police Station", "Meridian Freight Solutions Pvt. Ltd."]
    assert names(result, "Location") == ["Maharashtra", "Mumbai", "Thane"]
    for entity in result.entities:
        assert entity.evidence in FIR or " ".join(entity.evidence.split()) in " ".join(FIR.split())


def test_month_names_are_only_dates_beside_numbers():
    text = "April Fernandes prepared invoices on 3 April 2026."
    assert clean_span(text, 0, len("April Fernandes"), "Person") == [(0, 15, "Person")]
    start = text.index("3 April")
    assert clean_span(text, start, start + len("3 April 2026"), "Person") == []


def test_soft_wrapped_name_is_kept_but_field_on_next_line_is_split():
    text = "Firm: Meridian Freight \nSolutions\nAnita Desai\nAge: 39"
    start = text.index("Meridian")
    assert [text[s:e] for s, e, _ in clean_span(text, start, text.index("\nAnita"), "Organization")] == [
        "Meridian Freight \nSolutions"]
    start = text.index("Anita")
    assert [text[s:e] for s, e, _ in clean_span(text, start, text.index(":", start), "Person")] == [
        "Anita Desai"]


def test_known_place_does_not_split_longer_organization(monkeypatch):
    text = "Invoices named Goa Marine Exports. The goods reached Goa."
    monkeypatch.setattr(local_entities, "load_pipeline", lambda _: fake_ner([
        ("Goa Marine Exports", "PERSON"), ("Goa.", "ORG")]))
    result = local_entities.extract_local(text, "test")
    assert [(e.name, e.kind) for e in result.entities] == [
        ("Goa Marine Exports", "Organization"), ("Goa", "Location")]


def test_one_kind_per_name_across_mentions(monkeypatch):
    text = "Powai is busy. The car was seen in Powai. Later, Powai again."
    monkeypatch.setattr(local_entities, "load_pipeline", lambda _: fake_ner([
        ("Powai", "ORG"), ("Powai.", "GPE"), ("Powai", "GPE")]))
    result = local_entities.extract_local(text, "test")
    assert [(e.name, e.kind) for e in result.entities] == [("Powai", "Location")]


def test_lowercase_single_word_place_is_not_a_candidate(monkeypatch):
    monkeypatch.setattr(local_entities, "load_pipeline", lambda _: fake_ner([]))
    result = local_entities.extract_local("Send the pune file.", "test")
    assert result.entities == []


def test_windows_line_endings_extract_like_unix_text(monkeypatch):
    # PDFium returns "\r\n"; the custom NER model then tags "Suburban\r\n" alone.
    crlf = FIR.replace("\n", "\r\n")
    start = crlf.index("Meridian")
    monkeypatch.setattr(local_entities, "load_pipeline", lambda _: fake_ner([
        ("Meridian Freight", "ORG"), ("Mumbai", "GPE")]))
    result = local_entities.extract_local(crlf, "test")
    organization = next(e for e in result.entities if e.name.startswith("Meridian"))
    assert organization.name == "Meridian Freight Solutions Pvt. Ltd."
    assert organization.evidence == crlf[start:crlf.index("Ltd.") + 4]  # Exact stored source.
    assert not any("\r" in e.name for e in result.entities)


def test_extracted_text_uses_one_newline_form(tmp_path):
    from backend.services.document_text import extract_text

    path = tmp_path / "fir.txt"
    path.write_bytes(b"FIR/2026/1\r\nName: Alice\rAge: 30\r\n")
    assert extract_text(path) == "FIR/2026/1\nName: Alice\nAge: 30"


@pytest.mark.parametrize("span,kind", [
    ("BNS", "PERSON"), ("B.N.S.S", "GPE"), ("Acts & Sections", "ORG"), ("Bharatiya Nyaya Sanhita", "PERSON"),
    ("Information Technology Act", "ORG"), ("State Sessions Court", "ORG"), ("Court of Sessions", "ORG"),
    ("State of Maharashtra", "ORG"), ("Judicial Magistrate", "ORG"), ("Nationality", "GPE"),
    ("Tuesday", "GPE"), ("P.S", "GPE"), ("Copy", "PERSON"), ("Indian", "NORP"), ("Sections", "ORG"),
])
def test_legal_references_courts_and_form_labels_are_not_entities(span, kind):
    text = f"Header\n{span} was recorded.\n"
    start = text.index(span)
    assert clean_span(text, start, start + len(span), local_entities.NER_KINDS.get(kind, "Organization")) == []


def test_names_beside_legal_words_and_generic_starts_survive():
    text = "PI Sandeep Pawar Rank: Police Inspector. Indian Railways and Station Road. CAM-ME-06."
    def spans(value, kind):
        start = text.index(value)
        return [text[s:e] for s, e, _ in clean_span(text, start, start + len(value), kind)]
    assert spans("PI Sandeep Pawar Rank: Police", "Person") == ["Sandeep Pawar"]
    assert spans("Indian Railways", "Organization") == ["Indian Railways"]
    assert spans("Station Road", "Organization") == ["Station Road"]
    assert spans("ME-06", "Location") == []


def test_acronyms_address_suffixes_and_fir_label(monkeypatch):
    text = "For AI / testing only\nFIR No.\n\nFIR-SYN-2026-0142\nArjun Deshmukh, resident of 18 Lotus Enclave, Nandipur"
    monkeypatch.setattr(local_entities, "load_pipeline", lambda _: fake_ner([
        ("AI", "GPE"), ("Arjun Deshmukh", "PERSON"), ("Enclave", "GPE"), ("Nandipur", "GPE")]))
    result = local_entities.extract_local(text, "test")
    assert [(e.kind, e.name) for e in result.entities] == [
        ("Case", "FIR-SYN-2026-0142"), ("Person", "Arjun Deshmukh"), ("Location", "Lotus Enclave"),
        ("Location", "Nandipur")]


def test_location_evidence_stays_in_its_form_paragraph():
    text = "District\n\nNandipur District, Maharashtra\n\nComplainant\n\nArjun, resident of Nandipur"
    start = text.rindex("Nandipur")
    assert local_entities.location_context(text, start, start + 8, [(0, len(text))]) == "Arjun, resident of Nandipur"
