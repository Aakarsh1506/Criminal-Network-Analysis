from unittest.mock import AsyncMock

import pytest

from backend.errors import APIError
from backend.routes import documents
from backend.services import entity_resolution as resolution
from backend.services.extraction import Entity, Extraction, Relationship
from backend.services.ingestion_store import canonical_entity


def entity(ref, kind, name, identifier=None):
    return Entity(ref=ref, kind=kind, name=name, identifier=identifier, attributes=[], evidence=name)


def draft():
    return Extraction(entities=[entity('p', 'Person', ' Alice ')] + [
        entity(f'l{i}', 'Location', f'City {i}') for i in range(3)
    ], relationships=[Relationship(subject='p', predicate='SEEN_AT', object=f'l{i}', evidence=f'Alice in City {i}') for i in range(3)])


async def test_phone_reuses_formatted_indian_number_without_claiming_ownership():
    db = AsyncMock()
    db.query.return_value = [{'canonical_id': 'existing', 'name': '9876543210', 'properties': {}}]
    identifier, row = await canonical_entity(db, entity('p', 'PhoneNumber', '+91 98765-43210'), 'new', {})
    assert identifier == 'existing'
    assert set(db.query.call_args.args[1][0]) == {'9876543210', '919876543210', '00919876543210'}
    assert not any('INSERT' in call.args[0] for call in db.query.call_args_list)


async def test_name_alone_never_automatically_reuses_person():
    db = AsyncMock()
    assert await resolution.find_existing(db, entity('p', 'Person', 'Alice'), {}) is None
    db.query.assert_not_called()


async def test_location_without_state_reuses_only_unique_city():
    db = AsyncMock()
    db.query.return_value = [{'location_id': 1, 'city': 'Mumbai', 'state': 'Maharashtra', 'geom': 'ignored'}]
    assert (await resolution.find_existing(db, entity('l', 'Location', ' Mumbai '), {}))[0] == 1
    db.query.return_value += [{'location_id': 2, 'city': 'Mumbai', 'state': 'Other'}]
    assert await resolution.find_existing(db, entity('l', 'Location', 'Mumbai'), {}) is None
    assert (await resolution.find_existing(db, entity('l', 'Location', 'Mumbai'), {'state': 'maharashtra'}))[0] == 1


@pytest.mark.parametrize('count', [0, 2, 3])
async def test_every_same_name_person_is_suggested_with_its_shared_connections(monkeypatch, count):
    async def resolve(db, candidate, props):
        return (candidate.ref, {}) if candidate.kind == 'Location' else None
    monkeypatch.setattr(resolution, 'find_existing', resolve)
    db, graph = AsyncMock(), AsyncMock()
    db.query.side_effect = [[{'person_id': 'P1', 'name': 'ALICE'}, {'person_id': 'P2', 'name': 'Alice'}],
                           [{'person_id': 'P2', 'kind': 'Location', 'id': 'l0', 'name': 'City 0'},
                            {'person_id': 'P1', 'kind': 'Case', 'id': 'C9', 'name': 'FIR/2026/9'}]]
    graph.run.return_value = [{'person_id': 'P1', 'kinds': ['Location'], 'id': f'l{i}'} for i in range(count)] * 2
    suggestions = await resolution.person_suggestions(db, graph, draft())
    # A separate FIR rarely shares three links; the officer still sees the match.
    assert {s['personId'] for s in suggestions} == {'P1', 'P2'}
    shared = {s['personId']: len(s['sharedConnections']) for s in suggestions}
    assert shared == {'P1': count, 'P2': 1}
    assert suggestions[0]['personId'] == ('P1' if count >= 2 else 'P2')  # Most shared first.
    # The officer sees which FIRs each existing record already appears in.
    assert {s['personId']: s['cases'] for s in suggestions} == {'P1': ['FIR/2026/9'], 'P2': []}


async def test_same_name_person_with_no_linked_records_is_still_suggested():
    db, graph = AsyncMock(), AsyncMock()
    db.query.side_effect = [[{'person_id': 'P1', 'name': 'Rohan Mehta', 'age': 29, 'city': 'Nandipur', 'state': None}], []]
    extraction = Extraction(entities=[entity('p', 'Person', 'Rohan Mehta')], relationships=[])
    suggestions = await resolution.person_suggestions(db, graph, extraction)
    assert suggestions == [{'ref': 'p', 'name': 'Rohan Mehta', 'personId': 'P1', 'age': 29, 'city': 'Nandipur',
                            'state': None, 'cases': [], 'sharedConnections': []}]
    graph.run.assert_not_called()


@pytest.mark.parametrize('props', [{'dob': '1990-01-02'}, {'alias': 'Ronny'}, {'phone': '+91 98765 43210'}])
async def test_name_with_matching_strong_identifier_reuses_person(props):
    db = AsyncMock()
    db.query.side_effect = [[{'person_id': 'P1'}], [{'person_id': 'P1', 'name': 'Rohan Mehta'}]]
    assert (await resolution.find_existing(db, entity('p', 'Person', 'rohan  mehta'), props))[0] == 'P1'
    assert db.query.call_args_list[0].args[1][0] == 'rohan mehta'
    if 'phone' in props:
        assert db.query.call_args_list[0].args[1][1] == '9876543210'


async def test_conflicting_strong_identifiers_are_left_for_review():
    db = AsyncMock()
    db.query.side_effect = [[{'person_id': 'P1'}], [{'person_id': 'P2'}]]
    assert await resolution.find_existing(
        db, entity('p', 'Person', 'Rohan Mehta'), {'dob': '1990-01-02', 'alias': 'Ronny'}) is None


async def test_confirmed_person_match_must_still_exist_with_same_name():
    db = AsyncMock()
    db.query.return_value = [{'person_id': 'P1', 'name': 'Alice'}]
    assert (await canonical_entity(db, entity('p', 'Person', ' ALICE '), 'new', {}, 'P1'))[0] == 'P1'
    db.query.return_value = [{'person_id': 'P1', 'name': 'Bob'}]
    with pytest.raises(APIError, match='no longer available'):
        await canonical_entity(db, entity('p', 'Person', 'Alice'), 'new', {}, 'P1')


async def test_suggestions_require_owned_current_draft(officer_client, db):
    db.query.return_value = []
    response = await officer_client.post('/api/documents/5/identity-suggestions', json={'extraction': draft().model_dump()})
    assert response.status_code == 409
    sql, params = db.query.call_args.args
    assert 'officer_id=%s' in sql and 'extraction=%s' in sql
    assert params[:2] == (5, 7)


async def test_suggestion_authentication(client, db):
    response = await client.post('/api/documents/5/identity-suggestions', json={'extraction': draft().model_dump()})
    assert response.status_code == 401
    db.query.assert_not_called()


async def test_suggestions_respect_rejected_entities_and_edges(officer_client, db, monkeypatch):
    db.query.return_value = [{'document_id': 5}]
    suggest = AsyncMock(return_value=[])
    monkeypatch.setattr(documents, 'person_suggestions', suggest)
    response = await officer_client.post('/api/documents/5/identity-suggestions', json={
        'extraction': draft().model_dump(), 'rejected_entity_indices': [1], 'rejected_relationship_indices': [1]})
    assert response.status_code == 200
    reviewed = suggest.call_args.args[2]
    assert len(reviewed.entities) == 3
    assert len(reviewed.relationships) == 1


async def test_forged_identity_selection_cannot_be_saved(officer_client, db, monkeypatch):
    db.query.return_value = [{'document_id': 5}]
    monkeypatch.setattr(documents, 'person_suggestions', AsyncMock(return_value=[]))
    response = await officer_client.post('/api/documents/5/confirm', json={
        'extraction': draft().model_dump(), 'person_matches': {'p': 'unrelated'}})
    assert response.status_code == 409
    assert not any('UPDATE' in call.args[0] for call in db.query.call_args_list)
