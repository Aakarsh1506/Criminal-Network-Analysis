"""Small, source-grounded retrieval layer for investigator questions."""

CHUNK_SIZE = 4500
CHUNK_OVERLAP = 400


def chunk_text(text):
    text = (text or "").strip()
    chunks = []
    start = 0
    while start < len(text):
        end = min(len(text), start + CHUNK_SIZE)
        if end < len(text):
            boundary = text.rfind("\n", start + 2500, end)
            if boundary > start:
                end = boundary
        chunks.append((start, text[start:end].strip()))
        if end >= len(text):
            break
        start = max(end - CHUNK_OVERLAP, start + 1)
    return [(offset, value) for offset, value in chunks if value]


async def index_document(db, document_id, text):
    chunks = chunk_text(text)
    await db.query("DELETE FROM document_chunks WHERE document_id=%s", (document_id,))
    for offset, chunk in chunks:
        await db.query(
            """INSERT INTO document_chunks
               (document_id, chunk_text, source_start, source_end, search_vector)
               VALUES (%s,%s,%s,%s,to_tsvector('simple',%s))""",
            (document_id, chunk, offset + 1, offset + len(chunk), chunk),
        )


async def retrieve_context(db, officer_id, question, limit=5):
    if not question or not question.strip():
        return []
    return await db.query(
        """SELECT c.document_id, d.original_name, c.chunk_text,
                  c.source_start, c.source_end,
                  ts_rank(c.search_vector, plainto_tsquery('simple', %s)) AS score
           FROM document_chunks c
           JOIN officer_documents d ON d.document_id=c.document_id
           WHERE d.officer_id=%s AND d.confirmed_at IS NOT NULL
             AND c.search_vector @@ plainto_tsquery('simple', %s)
           ORDER BY score DESC, c.document_id DESC
           LIMIT %s""",
        (question, officer_id, question, limit),
    )
