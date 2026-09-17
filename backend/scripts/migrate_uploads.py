"""Copy files saved in backend/uploads/ into the shared database.

Run once, from the repository root, on each computer that uploaded documents before file
contents moved to the database:
  backend/.venv/bin/python -m backend.scripts.migrate_uploads
Documents already stored in the database are skipped; nothing on disk is deleted.
"""

import asyncio

from backend.config import Settings
from backend.db import Database
from backend.services.document_files import load_document_file


async def migrate():
    settings = Settings.from_env()
    db = Database(settings)
    await db.open()
    try:
        await db.ensure_schema()
        rows = await db.query(
            """SELECT d.document_id, d.stored_name, d.original_name FROM officer_documents d
               WHERE NOT EXISTS (SELECT 1 FROM officer_document_files f WHERE f.document_id = d.document_id)
               ORDER BY d.document_id"""
        )
        copied, missing = 0, []
        for document in rows:
            if await load_document_file(db, settings.upload_dir, document) is None:
                missing.append(f"{document['document_id']} ({document['original_name']})")
            else:
                copied += 1
        print(f"Copied {copied} file(s) into the database.")
        if missing:
            print("Not on this computer (run this script where they were uploaded, or re-upload):")
            for item in missing:
                print(f"  - document {item}")
    finally:
        await db.close()


def main():
    asyncio.run(migrate())


if __name__ == "__main__":
    main()
