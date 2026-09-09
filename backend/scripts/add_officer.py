"""Create an officer: python -m backend1.scripts.add_officer --help."""

import argparse
import asyncio
import getpass
import json
from datetime import date

from psycopg.errors import UniqueViolation
from starlette.concurrency import run_in_threadpool

from ..config import BASE_DIR, Settings
from ..db import Database
from ..security import hash_password


async def create_officer(args):
    db = Database(Settings.from_env())
    await db.open()
    try:
        await db.query((BASE_DIR / "sql" / "officers.sql").read_text())
        password_hash = await run_in_threadpool(hash_password, args.password)
        rows = await db.query(
            """INSERT INTO officers (username, password_hash, name, dob, org_name, role)
               VALUES (%s, %s, %s, %s, %s, %s)
               RETURNING officer_id, username, name, org_name, role""",
            (args.username, password_hash, args.name, args.dob, args.org, args.role),
        )
        print("Officer account created:")
        print(json.dumps(rows[0], indent=2))
    except UniqueViolation:
        raise SystemExit(
            f'Username "{args.username}" already exists — pick a different one.'
        ) from None
    finally:
        await db.close()


def main():
    parser = argparse.ArgumentParser(description="Create an officer in PostgreSQL")
    for name in ("username", "name", "org"):
        parser.add_argument(f"--{name}", required=True)
    parser.add_argument("--password", help="Omit to enter the password privately")
    parser.add_argument("--dob", type=date.fromisoformat)
    parser.add_argument("--role", default="officer")
    args = parser.parse_args()
    # Prompt without echoing the password when it is omitted from the command.
    args.password = args.password if args.password is not None else getpass.getpass("Password: ")
    if len(args.password) < 8:
        parser.error("Password must be at least 8 characters.")
    asyncio.run(create_officer(args))


if __name__ == "__main__":
    main()
