import logging
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, Request
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile
from starlette.responses import FileResponse

from ..errors import APIError, api_errors
from ..security import require_auth

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
    }


def document_path(directory, filename):
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
            while chunk := source.read(64 * 1024):
                size += len(chunk)
                if size > MAX_FILE_SIZE:
                    raise APIError("File too large", 400)
                destination.write(chunk)
    except BaseException:
        remove_file(path)
        raise
    return size


@router.get("/", include_in_schema=False)
@router.get("")
async def list_documents(request: Request, officer=Depends(require_auth)):
    with api_errors("Failed to load documents"):
        rows = await request.app.state.db.query(
            "SELECT * FROM officer_documents WHERE officer_id = %s ORDER BY uploaded_at DESC",
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
                        "properties": {"file": {"type": "string", "format": "binary"}},
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
        if file.content_type != "application/pdf":
            raise APIError("Only PDF files are allowed", 400)
        if file.size is not None and file.size > MAX_FILE_SIZE:
            raise APIError("File too large", 400)
        directory = request.app.state.settings.upload_dir
        filename = f"{uuid4()}{Path(file.filename).suffix}"
        path = document_path(directory, filename)
        with api_errors("Failed to save document"):
            size = await run_in_threadpool(save_upload, file.file, path)
            try:
                rows = await request.app.state.db.query(
                    """INSERT INTO officer_documents
                       (officer_id, original_name, stored_name, mime_type, size_bytes)
                       VALUES (%s, %s, %s, %s, %s) RETURNING *""",
                    (officer["officerId"], file.filename, filename, file.content_type, size),
                )
                return map_document(rows[0])
            except BaseException:
                await run_in_threadpool(remove_file, path)
                raise


@router.get("/{document_id}/file")
async def get_document(document_id: int, request: Request, officer=Depends(require_auth)):
    with api_errors("Failed to load document"):
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
            content_disposition_type="inline",
        )


@router.delete("/{document_id}")
async def delete_document(document_id: int, request: Request, officer=Depends(require_auth)):
    with api_errors("Failed to delete document"):
        rows = await request.app.state.db.query(
            """DELETE FROM officer_documents WHERE document_id = %s AND officer_id = %s
               RETURNING stored_name""",
            (document_id, officer["officerId"]),
        )
        if not rows:
            raise APIError("Document not found", 404)
        path = document_path(request.app.state.settings.upload_dir, rows[0]["stored_name"])
        await run_in_threadpool(remove_file, path)
        return {"ok": True}
