import json
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock

import httpx
import pytest

from backend.errors import APIError
from backend.services import rag
from backend.services.profile_record import validate_sections


def test_passages_preserve_exact_source_offsets_and_cover_document():
    text = '   \n' + ('Alice visited Mumbai.\n\n' * 300) + ' अंतिम जानकारी।  '
    spans = rag.chunk_text(text)
    coverage = set()
    for start, passage in spans:
        assert passage == text[start:start + len(passage)]
        assert len(passage) <= rag.CHUNK_SIZE
        coverage.update(range(start, start + len(passage)))
    assert all(index in coverage for index, char in enumerate(text) if not char.isspace())
    assert spans[-1][1].endswith('अंतिम जानकारी।')


async def test_embedding_vectors_are_normalized_and_never_truncated(settings):
    client = AsyncMock()
    client.post.return_value = httpx.Response(200, json={'embeddings': [[3, 4]]})
    assert await rag.embed_texts(client, settings, ['source']) == [[.6, .8]]
    assert client.post.call_args.kwargs['json']['truncate'] is False


@pytest.mark.parametrize('vectors', [[], [[0, 0]], [[1, 'bad']], [[True, 0]], [[1], [1, 2]]])
async def test_invalid_embedding_results_fail_clearly(settings, vectors):
    client = AsyncMock()
    client.post.return_value = httpx.Response(200, json={'embeddings': vectors})
    with pytest.raises(APIError):
        await rag.embed_texts(client, settings, ['source'])


async def test_index_replacement_is_transactional_with_exact_citations(settings):
    tx = AsyncMock()
    db = AsyncMock()
    entered = []
    @asynccontextmanager
    async def transaction():
        entered.append(True)
        yield tx
    db.transaction = transaction
    source = ' \n Alice met Bob.  '
    result = await rag.index_document(db, 1, source)
    assert entered and result == {'chunks': 1, 'embedded': 0, 'mode': 'keyword'}
    sql, values = tx.query.call_args.args
    assert 'INSERT INTO document_chunks' in sql
    assert source[values[2] - 1:values[3]] == values[1]


async def test_retrieval_scopes_both_searches_and_fuses_shared_hits(settings, monkeypatch):
    row = {'chunk_id': 1, 'document_id': 5, 'original_name': 'test', 'chunk_text': 'evidence', 'source_start': 1, 'source_end': 8}
    db = AsyncMock()
    db.query.side_effect = [[row], [row]]
    monkeypatch.setattr(rag, 'embed_texts', AsyncMock(return_value=[[1, 0]]))
    result = await rag.retrieve_context(db, 7, 'Alice location', person_id='P1', settings=settings, client=AsyncMock())
    assert len(result) == 1 and result[0]['retrieval_mode'] == 'hybrid'
    for call in db.query.call_args_list:
        assert 'd.officer_id=%s' in call.args[0]
        assert 'd.confirmed_at IS NOT NULL' in call.args[0]
        assert "e.kind='Person' AND e.canonical_id=%s" in call.args[0]
        assert 7 in call.args[1] and 'P1' in call.args[1]


async def test_embedding_outage_preserves_keyword_results(settings, monkeypatch):
    row = {'chunk_id': 1, 'document_id': 5, 'original_name': 'test', 'chunk_text': 'source', 'source_start': 1, 'source_end': 6}
    db = AsyncMock(query=AsyncMock(return_value=[row]))
    monkeypatch.setattr(rag, 'embed_texts', AsyncMock(side_effect=APIError('Unavailable', 503)))
    result = await rag.retrieve_context(db, 7, 'Alice', settings=settings, client=AsyncMock())
    assert result[0]['retrieval_mode'] == 'keyword'


@pytest.mark.parametrize('citation', ['invented', None, {}, 12])
def test_generated_record_cannot_cite_unknown_sources(citation):
    value = {'sections': [{'category': 'identity', 'items': [{'text': 'Claim', 'sources': [citation]}]}]}
    with pytest.raises(ValueError):
        validate_sections(value, {'profile'})


def test_generated_record_accepts_known_citations_only():
    value = json.loads('{"sections":[{"category":"identity","items":[{"text":"Alice","sources":["profile"]}]}]}')
    assert validate_sections(value, {'profile'}) == value['sections']


def test_repeated_record_paragraphs_are_shown_once_and_empty_sections_omitted():
    item = {'text': 'Alice witnessed case C1.', 'sources': ['profile']}
    value = {'sections': [{'category': 'cases', 'items': [item]},
                          {'category': 'locations', 'items': [item]},
                          {'category': 'sourceDetails', 'items': []}]}
    assert validate_sections(value, {'profile'}) == [{'category': 'cases', 'items': [item]}]
