"""Delete a source and its unshared imported records, with retryable graph cleanup."""

from ..errors import APIError
from .ingestion_store import NODE_KEYS

TABLES = {
    "Case": "cases", "Person": "persons", "Organization": "organizations",
    "Vehicle": "vehicles", "Location": "locations", "CrimeType": "crime_types",
}

async def referenced_elsewhere(tx, table, key, identifier):
    # Respect all installed foreign keys, including deployments with extra
    # association tables. Workspace pins/list entries may cascade on removal.
    references = await tx.query(
        """SELECT quote_ident(ns.nspname)||'.'||quote_ident(target.relname) AS relation,
                  quote_ident(column_info.attname) AS column_name
           FROM pg_constraint c
           JOIN pg_class target ON target.oid=c.conrelid
           JOIN pg_namespace ns ON ns.oid=target.relnamespace
           CROSS JOIN LATERAL unnest(c.conkey,c.confkey) AS keys(local_key,foreign_key)
           JOIN pg_attribute column_info ON column_info.attrelid=c.conrelid
               AND column_info.attnum=keys.local_key
           JOIN pg_attribute referenced ON referenced.attrelid=c.confrelid
               AND referenced.attnum=keys.foreign_key
           WHERE c.contype='f' AND c.confrelid=%s::regclass AND referenced.attname=%s
             AND target.relname NOT IN ('officer_pinned_criminal','officer_working_list')""",
        (table, key),
    )
    for reference in references:
        rows = await tx.query(
            f"SELECT 1 FROM {reference['relation']} WHERE {reference['column_name']}=%s LIMIT 1",
            (identifier,),
        )
        if rows:
            return True
    return False


async def remove_graph_records(graph, document_id, nodes):
    async def write(tx):
        result = await tx.run(
            "MATCH ()-[r]->() WHERE r.document_id=$document "
            "AND r.source='document_extraction' DELETE r",
            document=document_id,
        )
        await result.consume()
        for kind, ids in nodes.items():
            # Delete only isolated import-created nodes, never detach unrelated links.
            result = await tx.run(
                f"MATCH (n:{kind}) WHERE n.{NODE_KEYS[kind]} IN $ids "
                "AND n.source='document_extraction' AND NOT (n)--() DELETE n",
                ids=ids,
            )
            await result.consume()

    async with graph.driver.session() as session:
        await session.execute_write(write)


async def remove_document_records(db, graph, document_id, officer_id):
    async with db.transaction() as tx:
        # Share the import lock so a new import cannot claim an orphan mid-deletion.
        await tx.query("SELECT pg_advisory_xact_lock(724013)")
        rows = await tx.query(
            "SELECT * FROM officer_documents WHERE document_id = %s AND officer_id = %s FOR UPDATE",
            (document_id, officer_id),
        )
        if not rows:
            raise APIError("Document not found", 404)
        document = rows[0]
        if document.get("processing_status") in ("queued", "processing", "syncing"):
            raise APIError("Stop document processing before removing it.", 409)
        entities = await tx.query(
            "SELECT kind,canonical_id FROM extracted_entities WHERE document_id=%s",
            (document_id,),
        )
        await tx.query("DELETE FROM extracted_relationships WHERE document_id=%s", (document_id,))
        await tx.query("DELETE FROM extracted_entities WHERE document_id=%s", (document_id,))
        removed_nodes = {}
        # Remove cases first to release their references to people and lookup records.
        for kind in (*TABLES, "PhoneNumber"):
            candidates = [entity["canonical_id"] for entity in entities if entity["kind"] == kind]
            if not candidates:
                continue
            orphans = await tx.query(
                """SELECT DISTINCT candidate AS canonical_id,
                       EXISTS (SELECT 1 FROM ingestion_owned_entities owned
                           WHERE owned.kind=%s AND owned.canonical_id=candidate) AS owned
                   FROM unnest(%s::text[]) candidate
                   WHERE NOT EXISTS (SELECT 1 FROM extracted_entities e
                       WHERE e.kind=%s AND e.canonical_id=candidate)""",
                (kind, candidates, kind),
            )
            graph_ids = [
                int(row["canonical_id"]) if kind in ("Location", "CrimeType")
                else row["canonical_id"] for row in orphans
            ]
            try:
                retained = await graph.run(
                    f"MATCH (n:{kind}) WHERE n.{NODE_KEYS[kind]} IN $ids "
                    "AND (coalesce(n.source,'') <> 'document_extraction' OR EXISTS { "
                    "MATCH (n)-[r]-() WHERE coalesce(r.source,'') <> 'document_extraction' "
                    "OR r.document_id IS NULL OR r.document_id <> $document }) "
                    f"RETURN toString(n.{NODE_KEYS[kind]}) AS id",
                    {"ids": graph_ids, "document": document_id},
                ) if graph_ids else []
            except Exception:
                raise APIError(
                    "Could not check Neo4j records. The document was retained; retry removal when Neo4j is available.",
                    503,
                ) from None
            retained_ids = {row["id"] for row in retained}
            for row in orphans:
                identifier = row["canonical_id"]
                if identifier in retained_ids:
                    continue
                if kind in TABLES:
                    table, key = TABLES[kind], NODE_KEYS[kind]
                    if await referenced_elsewhere(tx, table, key, identifier):
                        continue
                    if row["owned"]:
                        await tx.query(
                            f"DELETE FROM {table} WHERE {key}=%s RETURNING {key}",
                            (identifier,),
                        )
                graph_id = int(identifier) if kind in ("Location", "CrimeType") else identifier
                removed_nodes.setdefault(kind, []).append(graph_id)
                await tx.query(
                    "DELETE FROM ingestion_owned_entities WHERE kind=%s AND canonical_id=%s",
                    (kind, identifier),
                )
        # All SQL changes remain uncommitted until Neo4j succeeds. If Neo4j is down,
        # keep the document and its provenance so Remove can be retried.
        if entities or document.get("graph_payload") is not None:
            try:
                await remove_graph_records(graph, document_id, removed_nodes)
            except Exception:
                raise APIError(
                    "Could not remove Neo4j records. The document was retained; "
                    "check Neo4j and retry Remove document.", 503,
                ) from None
        await tx.query(
            "DELETE FROM officer_documents WHERE document_id = %s AND officer_id = %s",
            (document_id, officer_id),
        )
        return document["stored_name"]
