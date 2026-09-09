from datetime import datetime, timezone

import pytest

from backend.routes.documents import MAX_FILE_SIZE


async def test_upload_list_download_delete_preserves_contract(officer_client, db, settings):
    files = {}
    now = datetime(2026, 9, 8, 12, tzinfo=timezone.utc)

    async def query(sql, params=()):
        if sql.lstrip().startswith("INSERT"):
            officer_id, original, stored, mime, size, source_type = params
            assert officer_id == 7
            files[1] = {
                "document_id": 1,
                "officer_id": officer_id,
                "original_name": original,
                "stored_name": stored,
                "mime_type": mime,
                "size_bytes": size,
                "uploaded_at": now,
                "source_type": source_type,
                "processing_status": "queued",
            }
            return [files[1]]
        if "ORDER BY uploaded_at" in sql:
            assert params == (7,)
            return list(files.values())
        assert params == (1, 7)
        assert "officer_id = %s" in sql
        if sql.lstrip().startswith("DELETE"):
            return [files.pop(1)] if 1 in files else []
        return [files[1]] if 1 in files else []

    db.query.side_effect = query
    content = b"%PDF-1.7\nTest PDF content"
    response = await officer_client.post(
        "/api/documents", files={"file": ('report "one".pdf', content, "application/pdf")}
    )
    assert response.status_code == 201
    document = response.json()
    assert set(document) == {
        "id",
        "name",
        "type",
        "size",
        "uploadedAt",
        "sourceType",
        "status",
        "processingError",
        "confirmedAt",
    }
    assert document["status"] == "queued"
    assert document["id"] == 1 and document["size"] == len(content)
    assert document["type"] == "application/pdf"
    stored = files[1]["stored_name"]
    assert stored != document["name"] and stored.endswith(".pdf")
    assert (settings.upload_dir / stored).read_bytes() == content
    assert (await officer_client.get("/api/documents")).json() == [document]
    download = await officer_client.get("/api/documents/1/file")
    assert download.status_code == 200 and download.content == content
    assert download.headers["content-type"] == "application/pdf"
    assert download.headers["content-disposition"].startswith("inline;")
    assert (await officer_client.delete("/api/documents/1")).json() == {"ok": True}
    assert not (settings.upload_dir / stored).exists()
    assert (await officer_client.get("/api/documents/1/file")).status_code == 404


async def test_other_officer_cannot_read_or_delete(officer_client, db, settings):
    path = settings.upload_dir / "private.pdf"
    path.write_bytes(b"private document")
    db.query.return_value = []
    for method, url in [("GET", "/api/documents/10/file"), ("DELETE", "/api/documents/10")]:
        response = await officer_client.request(method, url)
        assert response.status_code == 404
        sql, params = db.query.call_args.args
        assert "officer_id = %s" in sql and params == (10, 7)
    assert path.exists()


async def test_upload_requires_auth_before_saving(client, db, settings):
    response = await client.post(
        "/api/documents", files={"file": ("test.pdf", b"%PDF", "application/pdf")}
    )
    assert response.status_code == 401
    assert list(settings.upload_dir.iterdir()) == []
    db.query.assert_not_called()


@pytest.mark.parametrize(
    "files,message",
    [
        (None, "No file provided"),
        (
            {"file": ("test.exe", b"text", "text/plain")},
            "Upload a PDF, image, TXT, CSV, JSON, or DOCX file",
        ),
        ({"wrong": ("test.pdf", b"%PDF", "application/pdf")}, "Unexpected field"),
    ],
)
async def test_bad_uploads(officer_client, db, settings, files, message):
    response = await officer_client.post("/api/documents", files=files)
    assert response.status_code == 400
    assert response.json() == {"error": message}
    assert list(settings.upload_dir.iterdir()) == []
    db.query.assert_not_called()


async def test_file_size_limit_and_duplicate_files(officer_client, db, settings):
    response = await officer_client.post(
        "/api/documents",
        files={"file": ("large.pdf", b"x" * (MAX_FILE_SIZE + 1), "application/pdf")},
    )
    assert response.status_code == 400 and response.json() == {"error": "File too large"}
    assert list(settings.upload_dir.iterdir()) == []
    response = await officer_client.post(
        "/api/documents",
        files=[
            ("file", ("a.pdf", b"a", "application/pdf")),
            ("file", ("b.pdf", b"b", "application/pdf")),
        ],
    )
    assert response.status_code == 400
    assert "error" in response.json()
    db.query.assert_not_called()


async def test_failed_insert_removes_saved_pdf(officer_client, db, settings):
    db.query.side_effect = RuntimeError("database down")
    response = await officer_client.post(
        "/api/documents", files={"file": ("report.pdf", b"%PDF", "application/pdf")}
    )
    assert response.status_code == 500
    assert response.json() == {"error": "Failed to save document"}
    assert list(settings.upload_dir.iterdir()) == []


async def test_missing_file_and_path_escape(officer_client, db, settings):
    db.query.return_value = [
        {
            "stored_name": "missing.pdf",
            "mime_type": "application/pdf",
            "original_name": "missing.pdf",
        }
    ]
    assert (await officer_client.get("/api/documents/1/file")).status_code == 404
    db.query.return_value[0]["stored_name"] = "../outside.pdf"
    assert (await officer_client.get("/api/documents/1/file")).status_code == 404
