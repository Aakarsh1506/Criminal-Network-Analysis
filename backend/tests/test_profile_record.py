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


def record_for_generation():
    return {'personId': 'P1', 'name': 'Alice', 'location': None, 'index': {},
            'sources': [{'id': 'document-1', 'label': 'FIR.docx', 'documentId': 1}],
            'facts': [{'id': 'f1', 'category': 'identity', 'label': 'name', 'text': 'Alice',
                       'evidence': 'Alice', 'source': 'document-1', 'needsReview': False}]}


def reply(payload, done_reason='stop'):
    import json as _json

    import httpx
    content = payload if isinstance(payload, str) else _json.dumps(payload)
    return httpx.Response(200, json={'message': {'content': content}, 'done_reason': done_reason})


async def generate(client, settings, monkeypatch):
    from dataclasses import replace
    monkeypatch.setattr(profile_record, 'retrieve_context', AsyncMock(return_value=[]))
    return await profile_record.generate_record(
        record_for_generation(), AsyncMock(), client, replace(settings, extraction_provider='ollama'), 7)


async def test_unusable_items_are_dropped_but_a_valid_record_is_kept(settings, monkeypatch):
    client = AsyncMock()
    client.post.return_value = reply({'sections': [
        {'category': 'identity', 'items': [
            {'text': 'Alice is named in FIR.docx.', 'sources': ['document-1'], 'confidence': 'high'},
            {'text': 'Invented claim', 'sources': ['document-9']},
            {'text': '   ', 'sources': ['document-1']},
        ]},
        {'category': 'invented-category', 'items': [{'text': 'x', 'sources': ['document-1']}]},
    ]})
    result = await generate(client, settings, monkeypatch)
    assert result['sections'] == [{'category': 'identity', 'items': [
        {'text': 'Alice is named in FIR.docx.', 'sources': ['document-1']}]}]
    assert client.post.await_count == 1


async def test_truncated_output_retries_once_with_more_room(settings, monkeypatch):
    client = AsyncMock()
    good = {'sections': [{'category': 'identity', 'items': [{'text': 'Alice.', 'sources': ['document-1']}]}]}
    client.post.side_effect = [reply(good, done_reason='length'), reply(good)]
    result = await generate(client, settings, monkeypatch)
    assert result['sections'][0]['items'][0]['text'] == 'Alice.'
    budgets = [call.kwargs['json']['options']['num_predict'] for call in client.post.call_args_list]
    assert budgets == [1200, 2400]
    assert 'under 250 words' in client.post.call_args.kwargs['json']['messages'][0]['content']


@pytest.mark.parametrize('payload', ['not json', {'sections': []}, {'sections': [
    {'category': 'identity', 'items': [{'text': 'Claim', 'sources': ['document-9']}]}]}])
async def test_unusable_answers_fail_after_one_retry(settings, monkeypatch, payload):
    from backend.errors import APIError
    client = AsyncMock()
    client.post.return_value = reply(payload)
    with pytest.raises(APIError, match='invalid citations'):
        await generate(client, settings, monkeypatch)
    assert client.post.await_count == 2
