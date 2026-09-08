from neo4j import AsyncGraphDatabase


class GraphDatabase:
    def __init__(self, settings):
        self.driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
            connection_timeout=5,
            connection_acquisition_timeout=10,
        )

    async def run(self, query, params=None):
        async with self.driver.session() as session:
            result = await session.run(query, params or {})
            # record.data() flattens graph objects, losing relationship identities.
            # Preserve native Path/Node/Relationship objects for serialization.
            return [dict(record.items()) async for record in result]

    async def close(self):
        await self.driver.close()
