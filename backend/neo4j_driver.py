import re

from neo4j import AsyncGraphDatabase


def _trust_self_signed_scheme(uri):
    # Python's ssl module (unlike Node's TLS stack here) rejects our
    # self-signed certificate under strict "+s" verification. Swap to
    # "+ssc" so the connection is still encrypted, but the certificate
    # isn't checked against a CA — matching what already works for the
    # Express backend against this same instance.
    return re.sub(r"^(bolt|neo4j)\+s://", r"\1+ssc://", uri)


class GraphDatabase:
    def __init__(self, settings):
        self.driver = AsyncGraphDatabase.driver(
            _trust_self_signed_scheme(settings.neo4j_uri),
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