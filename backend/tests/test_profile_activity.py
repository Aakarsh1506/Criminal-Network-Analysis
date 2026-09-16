from datetime import datetime, timezone
from unittest.mock import AsyncMock

from backend.services.profile_activity import load_activity


async def test_activity_requires_existing_person(officer_client, db, graph):
    db.query.return_value = []
    response = await officer_client.get('/api/criminals/missing/activity')
    assert response.status_code == 404
    graph.run.assert_not_awaited()


async def test_activity_keeps_evidence_and_source_ownership(officer_client, db):
    timestamp = datetime(2026, 9, 16, tzinfo=timezone.utc)
    entries = [dict(id='r1', kind='CONTACTED', subject='Alice', object='Bob',
                    evidence='Alice contacted Bob.', recorded_at=timestamp,
                    document_id=8, original_name='fir.txt', officer_id=7),
               dict(id='r2', kind='PERSON_RECORD', subject='Alice', object=None,
                    evidence='Name: Alice', recorded_at=timestamp,
                    document_id=9, original_name='report.txt', officer_id=10)]
    db.query.side_effect = [[{'person_id': 'P001'}], entries, [{'city': 'Mumbai', 'state': None}]]
    response = await officer_client.get('/api/criminals/P001/activity')
    assert response.status_code == 200
    body = response.json()
    assert body['entries'][0]['evidence'] == 'Alice contacted Bob.'
    assert body['entries'][0]['canOpenSource'] is True
    assert body['entries'][1]['canOpenSource'] is False
    assert body['location']['city'] == 'Mumbai'
    assert 'eventDate' not in body['entries'][0]  # Never treat upload time as event time.


async def test_graph_only_location_is_displayable_without_sql_location():
    db = AsyncMock()
    db.query.side_effect = [[], []]
    graph = AsyncMock()
    graph.run.return_value = [{'city': None, 'name': 'Warehouse', 'state': None}]
    data = await load_activity('P001', db, 7, graph)
    assert data['location']['city'] == 'Warehouse'
    assert data['entries'] == []


async def test_graph_outage_does_not_hide_sql_activity():
    db = AsyncMock()
    db.query.side_effect = [[], []]
    graph = AsyncMock()
    graph.run.side_effect = RuntimeError('offline')
    assert await load_activity('P001', db, 7, graph) == {'entries': [], 'location': None}
