"""A persistent queue with leased jobs and replayable Neo4j writes."""

import asyncio
import logging

from psycopg.types.json import Jsonb
from starlette.concurrency import run_in_threadpool

from ..errors import APIError
from .document_text import extract_text
from .extraction import Extraction, extract_entities
from .ingestion_store import persist_extraction, sync_graph

logger = logging.getLogger(__name__)


class ProcessingCancelled(Exception):
    """The officer stopped this job while it was being processed."""


async def process_document(state, doc):
    document_id = doc["document_id"]
    last_percent = 0

    async def progress(percent, label):
        nonlocal last_percent
        status_rows = await state.db.query(
            "SELECT processing_status FROM officer_documents WHERE document_id=%s",
            (document_id,),
        )
        if isinstance(status_rows, list) and status_rows and status_rows[0].get("processing_status") == "cancelled":
            raise ProcessingCancelled
        last_percent = max(last_percent, percent)
        await state.db.query(
            "UPDATE officer_documents SET processing_progress=%s WHERE document_id=%s",
            (Jsonb({"percent": last_percent, "label": label}), document_id),
        )

    try:
        async with asyncio.timeout(600):
            await progress(5, "Starting document processing")
            payload = doc.get("graph_payload")
            if payload is None:
                text = doc.get("extracted_text")
                if text is None:
                    await progress(10, "Reading document and extracting text")
                    path = (state.settings.upload_dir / doc["stored_name"]).resolve()
                    if path.parent != state.settings.upload_dir.resolve():
                        raise APIError("Document path is invalid.", 422)
                    text = await run_in_threadpool(extract_text, path, state.settings.ocr_language)
                    await state.db.query(
                        "UPDATE officer_documents SET extracted_text=%s WHERE document_id=%s",
                        (text, document_id),
                    )
                if doc.get("extraction") is not None:
                    result = Extraction.model_validate(doc["extraction"])
                else:
                    await progress(20, "Extracting entities and relationships")
                    result = await extract_entities(
                        text, doc["source_type"], state.settings, state.http_client,
                        progress=progress,
                    )
                    await state.db.query(
                        "UPDATE officer_documents SET extraction=%s WHERE document_id=%s",
                        (Jsonb(result.model_dump()), document_id),
                    )
                if doc.get("confirmed_at") is None:
                    # Stage the extraction for review; do not create entity records yet.
                    await state.db.query(
                        """UPDATE officer_documents SET processing_status='awaiting_review',
                           processing_progress='{"percent":100,"label":"Extraction complete — ready for review"}'::jsonb,
                           processing_error=NULL, lease_until=NULL WHERE document_id=%s""",
                        (document_id,),
                    )
                    return
                await progress(30, "Saving reviewed records")
                payload = await persist_extraction(state.db, document_id, result)
            await progress(85, "Saving network relationships")
            await sync_graph(state.graph, payload)
            await progress(99, "Finalizing saved relationships")
            await state.db.query(
                """UPDATE officer_documents SET processing_status='complete',
                processing_progress='{"percent":100,"label":"Reviewed records saved"}'::jsonb,
                processing_error=NULL, lease_until=NULL WHERE document_id=%s""",
                (document_id,),
            )
    except asyncio.CancelledError:
        # Shutdown makes the job available to the next worker immediately.
        await state.db.query(
            """UPDATE officer_documents SET processing_status='queued',
            lease_until=NULL, processing_progress=NULL WHERE document_id=%s""",
            (document_id,),
        )
        raise
    except ProcessingCancelled:
        logger.info("Document %s processing stopped by officer", document_id)
        return
    except Exception as exc:
        logger.warning("Document %s processing failed (%s)", document_id, type(exc).__name__)
        message = (
            exc.message if isinstance(exc, APIError) else "Processing failed. Retry this document."
        )
        await state.db.query(
            """UPDATE officer_documents
            SET processing_status=CASE WHEN graph_payload IS NULL THEN 'failed' ELSE 'sync_failed' END,
                processing_error=%s, lease_until=NULL WHERE document_id=%s""",
            (message, document_id),
        )


async def worker(state):
    while True:
        try:
            # A lease allows a different worker to recover jobs after a process crash.
            rows = await state.db.query("""UPDATE officer_documents SET
                processing_status='processing', lease_until=now()+interval '20 minutes',
                processing_error=NULL, processing_progress=NULL
                WHERE document_id=(SELECT document_id FROM officer_documents
                    WHERE processing_status='queued'
                       OR (processing_status IN ('processing','syncing') AND lease_until < now())
                    ORDER BY uploaded_at FOR UPDATE SKIP LOCKED LIMIT 1)
                RETURNING *""")
            if rows:
                await process_document(state, rows[0])
                continue
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.warning("Document queue unavailable; retrying shortly")
        await asyncio.sleep(3)
