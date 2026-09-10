import pytest

from backend.services.extraction import Attribute, Entity
from backend.services.ingestion_store import properties_for


def person(age):
    return Entity(
        ref="p",
        kind="Person",
        name="Alice",
        identifier=None,
        attributes=[Attribute(key="age", value=age)],
        evidence=f"Alice, age {age}",
    )


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("34", 34),
        ("34 years", 34),
        ("34 years old", 34),
        ("34 yrs", 34),
        ("34 yr.", 34),
        ("34 y/o", 34),
        ("0 years", 0),
        ("130", 130),
        ("034", 34),
    ],
)
def test_exact_age_formats(raw, expected):
    entity = person(raw)
    before = entity.model_dump()
    props = properties_for(entity)
    assert props["age"] == expected
    if raw != str(expected):
        assert props["age_text"] == raw
    assert entity.model_dump() == before  # The reviewed snapshot remains unchanged.


@pytest.mark.parametrize(
    "raw",
    [
        "30–35",
        "30-35 years",
        "about 34",
        "34 months",
        "unknown",
        "N/A",
        "-1",
        "131",
        "3.5",
        "34 or 35",
        "34; phone: 9876543210",
        "uncertain " * 20,
    ],
)
def test_uncertain_or_invalid_ages_preserve_text_without_an_integer(raw):
    entity = person(raw)
    props = properties_for(entity)
    assert "age" not in props
    assert props["age_text"] == raw.strip()
    assert entity.attributes[0].value == raw.strip()
