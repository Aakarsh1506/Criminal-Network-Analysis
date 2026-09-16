from unittest.mock import AsyncMock

import pytest

from backend.services.extraction import (
    Entity, Extraction, Relationship, RelationshipError,
    evidence_names_entity, validate_extraction,
)
from backend.services.profile_activity import load_activity

SOURCE = 'FIR/2026/0589\nName: Anita Desai\nAge: 39 years\nArjun Malhotra reportedly resides in Powai, Mumbai.'


def example(quote):
    return Extraction(entities=[
        Entity(ref='anita', kind='Person', name='Anita Desai', identifier=None,
               attributes=[], evidence='Name: Anita Desai\nAge: 39 years'),
        Entity(ref='case', kind='Case', name='FIR/2026/0589', identifier='FIR/2026/0589',
               attributes=[], evidence='FIR/2026/0589'),
    ], relationships=[Relationship(subject='anita', predicate='MENTIONED_IN',
                                  object='case', evidence=quote)])


def test_quote_from_another_person_is_rejected_even_when_verbatim():
    result = example('Arjun Malhotra reportedly resides in Powai, Mumbai.')
    with pytest.raises(RelationshipError, match='does not identify'):
        validate_extraction(result, SOURCE)


def test_uncorrected_mismatch_is_preserved_as_excluded_not_saved_as_a_link():
    result = validate_extraction(example('Arjun Malhotra reportedly resides in Powai, Mumbai.'),
                                 SOURCE, exclude_invalid=True)
    assert result.relationships == []
    assert len(result.excluded_relationships) == 1
    assert 'anita' in result.excluded_relationships[0].reason


def test_person_mention_can_use_single_fir_header_as_case_context():
    result = validate_extraction(example('Name: Anita Desai\nAge: 39 years'), SOURCE)
    assert len(result.relationships) == 1


@pytest.mark.parametrize('quote,name,expected', [
    ('Bobby contacted Alice.', 'Bob', False),
    ('Anita Desai was present.', 'Anita Desai', True),
    ('Anita\nDesai was present.', 'Anita Desai', True),
    ('Arjun Malhotra was present.', 'Anita Desai', False),
])
def test_entity_matching_respects_full_names_and_pdf_whitespace(quote, name, expected):
    assert evidence_names_entity(quote, name) is expected


def test_contact_evidence_must_identify_both_people():
    text = 'Alice\nBob\nAlice called a friend.'
    result = Extraction(entities=[
        Entity(ref=name, kind='Person', name=name, identifier=None, attributes=[], evidence=name)
        for name in ['Alice', 'Bob']
    ], relationships=[Relationship(subject='Alice', object='Bob', predicate='CONTACTED',
                                  evidence='Alice called a friend.')])
    with pytest.raises(RelationshipError, match='Bob'):
        validate_extraction(result, text)


async def test_old_bad_evidence_is_flagged_in_activity_without_modifying_records():
    row = dict(id='r1',kind='MENTIONED_IN',subject='Anita Desai',object='FIR/2026/0589',
               subject_kind='Person', object_kind='Case', subject_identifier=None,
               object_identifier=None,evidence='Arjun Malhotra reportedly resides in Powai, Mumbai.',
               recorded_at='2026-09-16',document_id=1,original_name='fir.pdf',officer_id=7)
    db = AsyncMock()
    db.query.side_effect = [[row], []]
    result = await load_activity('P1', db, 7)
    assert result['entries'][0]['needsReview'] is True
    assert all(call.args[0].lstrip().startswith(('SELECT', 'WITH')) for call in db.query.call_args_list)
