"""Uploaded file contents, shared through the database by every connected backend."""

import logging
from pathlib import Path

from starlette.concurrency import run_in_threadpool

logger = logging.getLogger(__name__)


def legacy_path(upload_dir, stored_name):
    """A file saved on disk before contents moved to the database, if it is safely inside uploads/."""
    path = (Path(upload_dir) / stored_name).resolve()
    return path if path.parent == Path(upload_dir).resolve() else None


async def load_document_file(db, upload_dir, document):
    """Return a document's bytes, or None when no backend has stored them in the database.

    Documents uploaded before the move to database storage are read from this computer's
    uploads/ folder once and copied into the database, so other backends can use them too.
    """
    rows = await db.query(
        "SELECT content FROM officer_document_files WHERE document_id=%s", (document["document_id"],)
    )
    if rows:
        return bytes(rows[0]["content"])
    path = legacy_path(upload_dir, document["stored_name"])
    if path is None or not await run_in_threadpool(path.is_file):
        return None
    content = await run_in_threadpool(path.read_bytes)
    await db.query(
        """INSERT INTO officer_document_files (document_id, content) VALUES (%s, %s)
           ON CONFLICT (document_id) DO NOTHING""",
        (document["document_id"], content),
    )
    logger.info("Copied document %s from uploads/ into the shared database", document["document_id"])
    return content
