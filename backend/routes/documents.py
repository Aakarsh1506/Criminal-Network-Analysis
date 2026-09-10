import logging
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, Request
from psycopg.types.json import Jsonb
from pydantic import BaseModel, Field, StrictInt
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile
from starlette.responses import FileResponse

from ..errors import APIError, api_errors
from ..security import require_auth
from ..services.document_text import FORMATS
from ..services.extraction import SOURCE_TYPES, ExcludedEntity, ExcludedRelationship, Extraction

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/documents", tags=["Documents"])
MAX_FILE_SIZE = 20 * 1024 * 1024


def map_document(row):
    return {
        "id": row["document_id"],
        "name": row["original_name"],
        "type": row["mime_type"],
        "size": row["size_bytes"],
        "uploadedAt": row["uploaded_at"],
        "sourceType": row.get("source_type"),
        "status": row.get("processing_status", "stored"),
        "processingError": row.get("processing_error"),
        "confirmedAt": row.get("confirmed_at"),
    }


def document_path(directory, filename):
    # Resolved paths must stay directly inside the upload directory.
    path = (directory / filename).resolve()
    if path.parent != directory.resolve():
        raise APIError("Document not found", 404)
    return path


def remove_file(path):
    try:
        path.unlink(missing_ok=True)
    except OSError:
        logger.warning("Could not remove uploaded file %s", path.name)


def save_upload(source, path):
    size = 0
    try:
        with path.open("xb") as destination:
            # Copy in chunks and enforce the limit as bytes are written.
            while chunk := source.read(64 * 1024):
                size += len(chunk)
                if size > MAX_FILE_SIZE:
                    raise APIError("File too large", 400)
                destination.write(chunk)
    except BaseException:
        remove_file(path)
        raise
    return size


@router.get("/source-types")
async def source_types(officer=Depends(require_auth)):
    return {"sourceTypes": SOURCE_TYPES, "extensions": list(FORMATS)}


@router.get("/", include_in_schema=False)
@router.get("")
async def list_documents(request: Request, officer=Depends(require_auth)):
    with api_errors("Failed to load documents"):
        rows = await request.app.state.db.query(
            """SELECT document_id, original_name, mime_type, size_bytes, uploaded_at,
               source_type, processing_status, processing_error, confirmed_at FROM officer_documents
               WHERE officer_id = %s ORDER BY uploaded_at DESC""",
            (officer["officerId"],),
        )
        return [map_document(row) for row in rows]


@router.post("/", status_code=201, include_in_schema=False)
@router.post(
    "",
    status_code=201,
    openapi_extra={
        "requestBody": {
            "content": {
                "multipart/form-data": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "file": {"type": "string", "format": "binary"},
                            "sourceType": {"type": "string", "enum": list(SOURCE_TYPES)},
                        },
                        "required": ["file"],
                    }
                }
            }
        },
    },
)
async def upload_document(request: Request, officer=Depends(require_auth)):
    # Parse after authentication, and close the parser's temporary files on all paths.
    async with request.form(max_files=1, max_fields=20) as form:
        file = form.get("file")
        if any(
            isinstance(value, UploadFile) and key != "file" for key, value in form.multi_items()
        ):
            raise APIError("Unexpected field", 400)
        if not isinstance(file, UploadFile) or not file.filename:
            raise APIError("No file provided", 400)
        if len(file.filename) > 255:
            raise APIError("Filename must be 255 characters or fewer", 400)
        source_type = form.get("sourceType", "fir")
        if not isinstance(source_type, str) or source_type not in SOURCE_TYPES:
            raise APIError("Select a valid document source type", 400)
        suffix = Path(file.filename).suffix.lower()
        if suffix not in FORMATS:
            raise APIError("Upload a PDF, image, TXT, CSV, JSON, or DOCX file", 400)
        if officer.get("officerId") is None:
            raise APIError("An officer account is required to upload documents", 403)
        if file.size is not None and file.size > MAX_FILE_SIZE:
            raise APIError("File too large", 400)
        directory = request.app.state.settings.upload_dir
        filename = f"{uuid4()}{suffix}"
        path = document_path(directory, filename)
        with api_errors("Failed to save document"):
            size = await run_in_threadpool(save_upload, file.file, path)
            try:
                rows = await request.app.state.db.query(
                    """INSERT INTO officer_documents
                       (officer_id, original_name, stored_name, mime_type, size_bytes,
                        source_type, processing_status)
                       VALUES (%s, %s, %s, %s, %s, %s, 'queued') RETURNING *""",
                    (
                        officer["officerId"],
                        file.filename,
                        filename,
                        FORMATS[suffix],
                        size,
                        source_type,
                    ),
                )
                return map_document(rows[0])
            except BaseException:
                # Remove the file if its metadata could not be stored.
                await run_in_threadpool(remove_file, path)
                raise


@router.get("/{document_id}")
async def document_details(document_id: int, request: Request, officer=Depends(require_auth)):
    with api_errors("Failed to load document"):
        rows = await request.app.state.db.query(
            "SELECT * FROM officer_documents WHERE document_id=%s AND officer_id=%s",
            (document_id, officer["officerId"]),
        )
        if not rows:
            raise APIError("Document not found", 404)
        row = rows[0]
        return {
            **map_document(row),
            "text": row.get("extracted_text"),
            "extraction": row.get("extraction"),
        }


@router.post("/{document_id}/process")
async def retry_document(document_id: int, request: Request, officer=Depends(require_auth)):
    with api_errors("Failed to queue document"):
        rows = await request.app.state.db.query(
            """UPDATE officer_documents SET processing_status='queued', processing_error=NULL,
               extraction=CASE WHEN graph_payload IS NULL AND confirmed_at IS NULL THEN NULL ELSE extraction END,
               source_type=COALESCE(source_type,'fir'), lease_until=NULL
               WHERE document_id=%s AND officer_id=%s
                 AND processing_status IN ('stored','failed','sync_failed') RETURNING *""",
            (document_id, officer["officerId"]),
        )
        if not rows:
            raise APIError("Document unavailable or already processing/completed", 409)
        return map_document(rows[0])


class ConfirmBody(BaseModel):
    extraction: Extraction
    rejected_relationship_indices: list[StrictInt] = Field(default_factory=list, max_length=400)
    rejected_entity_indices: list[StrictInt] = Field(default_factory=list, max_length=200)


@router.post("/{document_id}/confirm")
async def confirm_document(
    document_id: int, body: ConfirmBody, request: Request, officer=Depends(require_auth)
):
    with api_errors("Failed to confirm extraction"):
        rejected = set(body.rejected_relationship_indices)
        if len(rejected) != len(body.rejected_relationship_indices) or any(
            index < 0 or index >= len(body.extraction.relationships) for index in rejected
        ):
            raise APIError("Rejected relationship selections are invalid. Reload the draft.", 400)
        reviewed = body.extraction.model_copy(deep=True)
        rejected_entities = set(body.rejected_entity_indices)
        if len(rejected_entities) != len(body.rejected_entity_indices) or any(
            index < 0 or index >= len(body.extraction.entities) for index in rejected_entities
        ):
            raise APIError("Rejected entity selections are invalid. Reload the draft.", 400)
        rejected_refs = {
            entity.ref for index, entity in enumerate(body.extraction.entities)
            if index in rejected_entities
        }
        reviewed.entities = []
        for index, entity in enumerate(body.extraction.entities):
            if index in rejected_entities:
                reviewed.excluded_entities.append(ExcludedEntity(
                    **entity.model_dump(), reason="Rejected by reviewer during confirmation."
                ))
            else:
                reviewed.entities.append(entity)
        reviewed.relationships = []
        for index, relation in enumerate(body.extraction.relationships):
            endpoint_rejected = relation.subject in rejected_refs or relation.object in rejected_refs
            if index in rejected or endpoint_rejected:
                reviewed.excluded_relationships.append(
                    ExcludedRelationship(
                        **relation.model_dump(),
                        reason="An endpoint entity was rejected by the reviewer."
                        if endpoint_rejected else "Rejected by reviewer during confirmation."
                    )
                )
            else:
                reviewed.relationships.append(relation)
        # JSON equality prevents approval of a different or stale draft.
        rows = await request.app.state.db.query(
            """UPDATE officer_documents SET processing_status='queued',
               confirmed_at=now(), confirmed_by=%s, processing_error=NULL, lease_until=NULL,
               extraction=%s
               WHERE document_id=%s AND officer_id=%s AND processing_status='awaiting_review'
                 AND confirmed_at IS NULL AND graph_payload IS NULL AND extraction=%s
               RETURNING *""",
            (
                officer["officerId"],
                Jsonb(reviewed.model_dump()),
                document_id,
                officer["officerId"],
                Jsonb(body.extraction.model_dump()),
            ),
        )
        if not rows:
            raise APIError("Draft changed or is unavailable. Reload it before confirming.", 409)
        return {**map_document(rows[0]), "extraction": reviewed.model_dump()}


@router.get("/{document_id}/file")
async def get_document(document_id: int, request: Request, officer=Depends(require_auth)):
    with api_errors("Failed to load document"):
        # Check ownership in the query before serving any file.
        rows = await request.app.state.db.query(
            """SELECT stored_name, mime_type, original_name FROM officer_documents
               WHERE document_id = %s AND officer_id = %s""",
            (document_id, officer["officerId"]),
        )
        if not rows:
            raise APIError("Document not found", 404)
        doc = rows[0]
        path = document_path(request.app.state.settings.upload_dir, doc["stored_name"])
        if not await run_in_threadpool(path.is_file):
            raise APIError("Document not found", 404)
        return FileResponse(
            path,
            media_type=doc["mime_type"],
            filename=doc["original_name"],
            content_disposition_type="inline"
            if doc["mime_type"] in ("application/pdf", "image/png", "image/jpeg")
            else "attachment",
            headers={"X-Content-Type-Options": "nosniff"},
        )


@router.delete("/{document_id}")
async def delete_document(document_id: int, request: Request, officer=Depends(require_auth)):
    with api_errors("Failed to delete document"):
        rows = await request.app.state.db.query(
            """DELETE FROM officer_documents WHERE document_id = %s AND officer_id = %s
               AND processing_status IN ('stored','failed','awaiting_review')
               AND confirmed_at IS NULL AND graph_payload IS NULL
               AND NOT EXISTS (SELECT 1 FROM extracted_entities e
                               WHERE e.document_id=officer_documents.document_id)
               RETURNING stored_name""",
            (document_id, officer["officerId"]),
        )
        if not rows:
            existing = await request.app.state.db.query(
                "SELECT document_id FROM officer_documents WHERE document_id = %s AND officer_id = %s",
                (document_id, officer["officerId"]),
            )
            if not existing:
                raise APIError("Document not found", 404)
            raise APIError("Document is processing or retained as an extraction source", 409)
        path = document_path(request.app.state.settings.upload_dir, rows[0]["stored_name"])
        await run_in_threadpool(remove_file, path)
        return {"ok": True}
