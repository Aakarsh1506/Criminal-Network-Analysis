"""Rebuild derived search passages/embeddings without rerunning entity extraction.

  backend/.venv/bin/python -m backend.scripts.reindex_documents
  backend/.venv/bin/python -m backend.scripts.reindex_documents --document 5
"""

import argparse
import asyncio

import httpx

from backend.config import Settings
from backend.db import Database
from backend.services.rag import index_document


async def run(document_id=None):
    settings = Settings.from_env()
    db = Database(settings)
    await db.open()
    failed = False
    try:
        await db.ensure_schema()
        rows = await db.query(
            """SELECT document_id,extracted_text FROM officer_documents
               WHERE confirmed_at IS NOT NULL AND extracted_text IS NOT NULL
                 AND (%s::integer IS NULL OR document_id=%s) ORDER BY document_id""", (document_id, document_id),
        )
        async with httpx.AsyncClient() as client:
            for row in rows:
                result = await index_document(db, row['document_id'], row['extracted_text'], settings=settings, client=client)
                failed |= result['chunks'] != result['embedded']
                print(f"Document {row['document_id']}: {result['chunks']} passages, {result['embedded']} embeddings", flush=True)
        print(f'Reindexed {len(rows)} confirmed documents. Original records and graph links were not changed.')
    finally:
        await db.close()
    if failed:
        raise SystemExit('Some embeddings were unavailable; keyword search remains available. Retry after checking Ollama.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--document', type=int)
    asyncio.run(run(parser.parse_args().document))
