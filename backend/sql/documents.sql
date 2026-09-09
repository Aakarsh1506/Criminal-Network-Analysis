-- Store ownership and file metadata here; PDF contents live in uploads/.
CREATE TABLE IF NOT EXISTS officer_documents (
  document_id   SERIAL PRIMARY KEY,
  officer_id    INTEGER NOT NULL REFERENCES officers(officer_id) ON DELETE CASCADE,
  original_name VARCHAR(255) NOT NULL,
  stored_name   VARCHAR(255) NOT NULL,
  mime_type     VARCHAR(100) NOT NULL,
  size_bytes    INTEGER NOT NULL,
  uploaded_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
