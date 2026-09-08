from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from .config import BASE_DIR


class Database:
    def __init__(self, settings):
        self.pool = AsyncConnectionPool(
            kwargs={
                "host": settings.pg_host,
                "port": settings.pg_port,
                "user": settings.pg_user,
                "password": settings.pg_password,
                "dbname": settings.pg_database,
                "connect_timeout": 5,
                "row_factory": dict_row,
                "autocommit": True,
                "options": "-c timezone=UTC",
            },
            min_size=0,
            max_size=10,
            max_idle=30,
            timeout=5,
            open=False,
        )

    async def open(self):
        await self.pool.open()

    async def close(self):
        await self.pool.close()

    async def query(self, sql, params=()):
        async with self.pool.connection() as connection:
            async with connection.cursor() as cursor:
                await cursor.execute(sql, params or None)
                return await cursor.fetchall() if cursor.description else []

    async def ensure_schema(self):
        for filename in ("officers.sql", "workspace.sql", "documents.sql"):
            await self.query((BASE_DIR / "sql" / filename).read_text())
