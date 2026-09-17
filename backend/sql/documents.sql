-- Store ownership and file metadata here; contents live in officer_document_files.
CREATE TABLE IF NOT EXISTS officer_documents (
  document_id   SERIAL PRIMARY KEY,
  officer_id    INTEGER NOT NULL REFERENCES officers(officer_id) ON DELETE CASCADE,
  original_name VARCHAR(255) NOT NULL,
  stored_name   VARCHAR(255) NOT NULL,
  mime_type     VARCHAR(100) NOT NULL,
  size_bytes    INTEGER NOT NULL,
  uploaded_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- File contents live in the database so every backend sharing it can process and serve
-- any upload. Older rows may still have their bytes only in uploads/ (see document_files.py).
CREATE TABLE IF NOT EXISTS officer_document_files (
  document_id INTEGER PRIMARY KEY REFERENCES officer_documents(document_id) ON DELETE CASCADE,
  content     BYTEA NOT NULL
);
