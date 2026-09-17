from unittest.mock import AsyncMock

import pytest

from backend.services import profile_record


async def test_record_keeps_all_accessible_details_and_marks_wrong_person_evidence(monkeypatch):
    monkeypatch.setattr(profile_record, 'load_profile', AsyncMock(return_value={'criminal': {
        'name': 'Alice', 'alias': 'Al', 'age': 39, 'cases': [], 'location': {'city': 'Mumbai'}}, 'relations': []}))
    monkeypatch.setattr(profile_record, 'load_activity', AsyncMock(return_value={'location': None, 'entries': [
        {'id': 'r1', 'kind': 'CONTACTED', 'subject': 'Alice', 'object': 'Bob', 'evidence': 'Alice called Bob',
         'canOpenSource': True, 'documentId': 1, 'documentName': 'Allowed', 'needsReview': False},
        {'id': 'r2', 'kind': 'CONTACTED', 'subject': 'Alice', 'object': 'Private', 'evidence': 'Private quote',
         'canOpenSource': False, 'documentId': 2, 'documentName': 'Private', 'needsReview': False},
    ]}))
    db = AsyncMock()
    db.query.side_effect = [[{'entity_id': 'e1', 'properties': {'age': '39'}, 'evidence': 'Bob, age 39',
                             'document_id': 1, 'original_name': 'Allowed'}], [{'chunks': 3, 'embedded': 3, 'documents': 1}]]
    result = await profile_record.load_record('P1', db, AsyncMock(), 7, 'embeddinggemma')
    assert any(f['label'] == 'alias' and f['text'] == 'Al' for f in result['facts'])
    assert next(f for f in result['facts'] if f['id'] == 'e1')['needsReview']
    assert 'Private' not in str(result)
    assert result['location']['city'] == 'Mumbai'
    assert 'd.officer_id=%s' in db.query.call_args_list[0].args[0]


async def test_record_routes_require_auth(client):
    assert (await client.get('/api/criminals/P1/record')).status_code == 401
    assert (await client.post('/api/criminals/P1/record/generate', json={})).status_code == 401


async def test_generation_releases_capacity_on_failure(officer_client, app, monkeypatch):
    from backend.errors import APIError
    from backend.routes import criminals
    monkeypatch.setattr(criminals, 'load_record', AsyncMock(side_effect=APIError('Not found', 404)))
    response = await officer_client.post('/api/criminals/P1/record/generate', json={'language': 'en'})
    assert response.status_code == 404
    assert app.state.active_explanations == 0


@pytest.mark.parametrize('body', [None, {'language': 'unsupported'}])
async def test_generation_rejects_invalid_language(officer_client, body):
    response = await officer_client.post('/api/criminals/P1/record/generate', json=body)
    assert response.status_code == 400
