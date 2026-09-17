"""FIR layout and fixed phrasing yield grounded relationships without a model."""

import pytest

from backend.services.extraction import Entity
from backend.services.structural_relations import structural_relationships

FIR = (
    "Police Station: Harbour View Police Station\n"
    "FIR No. FIR-SYN-2026-0142\n"
    "Place of occurrence: Meridian Electronics, Station Road, Nandipur\n"
    "Complainant\n"
    "Name: Arjun Deshmukh\n"
    "Age: 45\n"
    "Address: Harbour Lane, Nandipur\n"
    "Details of known / suspected accused\n"
    "1. Rohan Mehta, age 29, resident of 42 Cedar Park, Nandipur; Sameer Qureshi, age 31, "
    "resident of 7 Lake Road, Nandipur\n"
    "Witnesses / persons acquainted with facts\n"
    "1. Kavita Rao, shop employee, 27, Station Road, Nandipur.\n"
    "1. Brief facts of the information\n"
    "Kavita Rao saw Rohan Mehta near the shop. Sameer Qureshi was not seen at Station Road.\n"
    "Rohan Mehta called Sameer\nQureshi at 23:05 hrs. Arjun Deshmukh did not call Kavita Rao.\n"
    "Imran Sheikh, an employee of Meridian Electronics, was seen at Station Road.\n"
    "A motorcycle MH12AB4521 was used.\n"
)
ENTITIES = [
    ("station", "Organization", "Harbour View Police Station"), ("case", "Case", "FIR No. FIR-SYN-2026-0142"),
    ("shop", "Organization", "Meridian Electronics"), ("road", "Location", "Station Road"),
    ("town", "Location", "Nandipur"), ("arjun", "Person", "Arjun Deshmukh"),
    ("lane", "Location", "Harbour Lane, Nandipur"), ("rohan", "Person", "Rohan Mehta"),
    ("cedar", "Location", "Cedar Park"), ("sameer", "Person", "Sameer Qureshi"),
    ("lake", "Location", "Lake Road"), ("kavita", "Person", "Kavita Rao"),
    ("imran", "Person", "Imran Sheikh"), ("bike", "Vehicle", "MH12AB4521"),
]


def entities(text=FIR, rows=ENTITIES):
    return [Entity(ref=ref, kind=kind, name=name, identifier=name if kind in {"Case", "Vehicle"} else None,
                   attributes=[], evidence=name) for ref, kind, name in rows if name in text]


def edges(text=FIR, rows=ENTITIES):
    return {(r.subject, r.predicate, r.object): r.evidence
            for r in structural_relationships(text, entities(text, rows))}


def test_fir_layout_and_phrases_give_grounded_edges():
    found = edges()
    expected = {
        ("rohan", "SUSPECT_IN", "case"), ("sameer", "SUSPECT_IN", "case"), ("kavita", "WITNESS_IN", "case"),
        ("arjun", "RESIDES_IN", "lane"), ("rohan", "RESIDES_IN", "cedar"), ("sameer", "RESIDES_IN", "lake"),
        ("rohan", "CONTACTED", "sameer"), ("imran", "SEEN_AT", "road"), ("imran", "EMPLOYED_BY", "shop"),
        ("case", "OCCURRED_AT", "road"), ("case", "OCCURRED_AT", "town"),
        ("station", "MENTIONED_IN", "case"), ("bike", "MENTIONED_IN", "case"), ("kavita", "MENTIONED_IN", "case"),
    }
    assert expected <= found.keys()
    for evidence in found.values():
        assert evidence in FIR
    assert found[("rohan", "CONTACTED", "sameer")] == "Rohan Mehta called Sameer\nQureshi at 23:05 hrs."
    # A clause cites only its own person's address.
    assert "Lake Road" not in found[("rohan", "RESIDES_IN", "cedar")]


@pytest.mark.parametrize("edge", [
    ("rohan", "WITNESS_IN", "case"),        # Named in a witness's sentence, but not listed as one.
    ("kavita", "SUSPECT_IN", "case"),
    ("rohan", "RESIDES_IN", "lake"),        # Another person's address on the same line.
    ("sameer", "SEEN_AT", "road"),          # "was not seen"
    ("arjun", "CONTACTED", "kavita"),       # "did not call"
    ("kavita", "CONTACTED", "rohan"),       # "saw" is not contact
    ("rohan", "SEEN_AT", "road"),           # Another person's sighting sentence.
    ("imran", "WITNESS_IN", "case"),        # Listed after the witness section ended.
])
def test_negations_other_records_and_later_sections_do_not_create_edges(edge):
    assert edge not in edges()


def test_case_edges_need_exactly_one_case():
    rows = ENTITIES + [("other", "Case", "FIR No. FIR-SYN-2026-0999")]
    text = FIR + "Linked: FIR No. FIR-SYN-2026-0999\n"
    found = edges(text, rows)
    assert not any(predicate in {"MENTIONED_IN", "SUSPECT_IN", "WITNESS_IN", "OCCURRED_AT"}
                   for _, predicate, _ in found)
    assert ("rohan", "CONTACTED", "sameer") in found


def test_labelled_role_fields_and_windows_line_endings():
    text = "FIR No. FIR-SYN-2026-7\r\nAccused: Rohan Mehta\r\nWitness name: Kavita Rao\r\n"
    found = edges(text, ENTITIES + [("case", "Case", "FIR No. FIR-SYN-2026-7")])
    assert ("rohan", "SUSPECT_IN", "case") in found and ("kavita", "WITNESS_IN", "case") in found


def test_calls_between_seen_together_visits_and_nature_of_complaint():
    text = (
        "FIR No. FIR/2026/0589\n"
        "Nature of Complaint Suspected financial fraud and coordinated movement\n"
        "Arjun Malhotra was reportedly seen entering a commercial office complex near Bandra Kurla Complex.\n"
        "Arjun Malhotra and Sameer Khan had previously been seen together at a café in Powai.\n"
        "The same records indicate 6 calls between Arjun Malhotra and Karan Mehta.\n"
        "Sameer Khan visited a warehouse area in Bhiwandi. Karan Mehta was not seen in Powai.\n"
    )
    rows = [("case", "Case", "FIR No. FIR/2026/0589"), ("fraud", "CrimeType", "financial fraud"),
            ("arjun", "Person", "Arjun Malhotra"), ("sameer", "Person", "Sameer Khan"),
            ("karan", "Person", "Karan Mehta"), ("bkc", "Location", "Bandra Kurla Complex"),
            ("powai", "Location", "Powai"), ("bhiwandi", "Location", "Bhiwandi")]
    found = edges(text, rows)
    assert {("case", "OF_TYPE", "fraud"), ("arjun", "SEEN_AT", "bkc"), ("arjun", "SEEN_AT", "powai"),
            ("sameer", "SEEN_AT", "powai"), ("arjun", "CONTACTED", "karan"),
            ("sameer", "SEEN_AT", "bhiwandi")} <= found.keys()
    assert ("karan", "SEEN_AT", "powai") not in found
    assert found[("sameer", "SEEN_AT", "bhiwandi")] == "Sameer Khan visited a warehouse area in Bhiwandi."


TABLE_FIR = (
    "For AI / criminal-network-analysis testing only\n\nFIR No.\n\nFIR-SYN-2026-0142\n\n"
    "Police Station\n\nHarbour View Police Station\n\n"
    "Complainant\n\nArjun Deshmukh, age 34, resident of 18 Lotus Enclave, Nandipur\n\n"
    "Accused\n\nRohan Mehta, age 29, resident of 42 Cedar Park, Nandipur; Sameer Qureshi, age 31\n\n"
    "Victim / affected party\n\nArjun Deshmukh\n\n"
    "Place of occurrence\n\nParking area behind Meridian Electronics, Station Road, Nandipur\n\n"
    "2. Witnesses\n\n1. Kavita Rao, shop employee, Station Road.\n\n"
    "4. Linked records\n\nThis record shares Rohan Mehta with FIR-SYN-2026-0198 and FIR-SYN-2026-0271.\n\n"
    "Investigating Officer\n\nSI Neha Kulkarni, Harbour View Police Station\n"
)
TABLE_ENTITIES = ENTITIES + [
    ("case", "Case", "FIR-SYN-2026-0142"), ("other1", "Case", "FIR-SYN-2026-0198"),
    ("other2", "Case", "FIR-SYN-2026-0271"), ("neha", "Person", "Neha Kulkarni"),
]


def test_table_layout_with_referenced_firs_attaches_edges_to_the_documents_own_fir():
    found = edges(TABLE_FIR, [row for row in TABLE_ENTITIES if row[2] != "FIR No. FIR-SYN-2026-0142"])
    assert {("rohan", "SUSPECT_IN", "case"), ("sameer", "SUSPECT_IN", "case"), ("kavita", "WITNESS_IN", "case"),
            ("case", "OCCURRED_AT", "road"), ("case", "OCCURRED_AT", "town"), ("neha", "MENTIONED_IN", "case"),
            ("neha", "EMPLOYED_BY", "station"), ("station", "MENTIONED_IN", "case")} <= found.keys()
    assert not any(target in {"other1", "other2"} for _, _, target in found)
    assert ("arjun", "SUSPECT_IN", "case") not in found and ("arjun", "WITNESS_IN", "case") not in found


def test_long_line_with_suspected_is_not_a_role_heading():
    text = ("FIR No. FIR/2026/0589\nNature of Complaint Suspected financial fraud and coordinated movement\n"
            "Rohan Mehta signed the complaint.\n")
    assert ("rohan", "SUSPECT_IN", "case") not in edges(text, ENTITIES + [("case", "Case", "FIR No. FIR/2026/0589")])


def test_two_labelled_firs_have_no_primary_case():
    text = "FIR No. FIR/2026/1\nAccused: Rohan Mehta\nFIR No. FIR/2026/2\n"
    rows = ENTITIES + [("c1", "Case", "FIR/2026/1"), ("c2", "Case", "FIR/2026/2")]
    assert not any(p == "SUSPECT_IN" for _, p, _ in edges(text, rows))
