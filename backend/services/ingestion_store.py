"""Commit extracted records and a replayable graph payload in one SQL transaction."""

from datetime import date

from psycopg.types.json import Jsonb

from ..errors import APIError
from .extraction import RELATION_RULES, stable_id

NODE_KEYS = {
    "Person": "person_id",
    "Case": "case_id",
    "Location": "location_id",
    "CrimeType": "crime_id",
    "Organization": "organization_id",
    "Vehicle": "vehicle_id",
    "PhoneNumber": "phone_id",
}


def properties_for(entity):
    props = {item.key: item.value for item in entity.attributes}
    for field in ("dob", "last_seen", "case_month"):
        if field in props:
            try:
                props[field] = date.fromisoformat(props[field]).isoformat()
            except ValueError:
                raise APIError(f"AI returned an invalid {field} date.", 502) from None
    for field in ("age", "height_cm"):
        if field in props:
            try:
                props[field] = int(props[field])
                if not 0 <= props[field] <= (130 if field == "age" else 300):
                    raise ValueError
            except ValueError:
                raise APIError(f"AI returned an invalid {field} value.", 502) from None
    # Existing relational columns are bounded to 100 characters.
    if any(len(str(value)) > 100 for key, value in props.items() if key != "description"):
        raise APIError("AI returned a field exceeding the database limit.", 502)
    return props


async def canonical_entity(tx, entity, entity_id, props):
    kind, identifier = entity.kind, entity.identifier
    if kind in ("Person", "Case", "Organization", "Vehicle"):
        table = {
            "Person": "persons",
            "Case": "cases",
            "Organization": "organizations",
            "Vehicle": "vehicles",
        }[kind]
        key = NODE_KEYS[kind]
        if identifier:
            matches = await tx.query(
                """SELECT DISTINCT canonical_id FROM extracted_entities
                   WHERE kind=%s AND properties->>'source_identifier'=%s""",
                (kind, identifier),
            )
            if len(matches) == 1:
                existing = await tx.query(
                    f"SELECT * FROM {table} WHERE {key}=%s", (matches[0]["canonical_id"],)
                )
                if existing and (
                    kind != "Person" or existing[0]["name"].casefold() == entity.name.casefold()
                ):
                    return matches[0]["canonical_id"], existing[0]
        # Reuse explicit source IDs, never merge people merely because names match.
        if identifier and len(identifier) <= 20:
            rows = await tx.query(f"SELECT * FROM {table} WHERE {key} = %s", (identifier,))
            if rows:
                if kind == "Person" and rows[0]["name"].casefold() != entity.name.casefold():
                    raise APIError("An extracted person ID conflicts with an existing name.", 409)
                return identifier, rows[0]
        canonical = entity_id
        if kind == "Person":
            await tx.query(
                """INSERT INTO persons (person_id, name, alias, dob, age, height_cm,
                   city, state, last_seen, record_status)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,'Extracted (unverified)')
                   ON CONFLICT (person_id) DO NOTHING""",
                (
                    canonical,
                    entity.name,
                    props.get("alias"),
                    props.get("dob"),
                    props.get("age"),
                    props.get("height_cm"),
                    props.get("city"),
                    props.get("state"),
                    props.get("last_seen"),
                ),
            )
        elif kind == "Case":
            # Role-specific links live in extracted_relationships; no invented primary suspect.
            await tx.query(
                """INSERT INTO cases (case_id, case_month, case_status)
                   VALUES (%s,%s,%s) ON CONFLICT (case_id) DO NOTHING""",
                (canonical, props.get("case_month"), props.get("case_status")),
            )
        elif kind == "Organization":
            await tx.query(
                "INSERT INTO organizations VALUES (%s,%s) ON CONFLICT DO NOTHING",
                (canonical, entity.name),
            )
        else:
            await tx.query(
                "INSERT INTO vehicles VALUES (%s,%s,%s) ON CONFLICT DO NOTHING",
                (canonical, props.get("registration") or identifier, entity.name),
            )
        rows = await tx.query(f"SELECT * FROM {table} WHERE {key} = %s", (canonical,))
        return canonical, rows[0]
    if kind == "CrimeType":
        rows = await tx.query(
            "SELECT * FROM crime_types WHERE lower(crime_name) = lower(%s)", (entity.name,)
        )
        if not rows:
            # The supplied dump resets this sequence below existing IDs.
            await tx.query("""SELECT setval(pg_get_serial_sequence('crime_types','crime_id'),
                GREATEST(COALESCE((SELECT MAX(crime_id) FROM crime_types),0)+1,
                nextval(pg_get_serial_sequence('crime_types','crime_id'))), false)""")
            rows = await tx.query(
                """INSERT INTO crime_types (crime_name, description) VALUES (%s,%s)
                   ON CONFLICT (crime_name) DO UPDATE SET crime_name=EXCLUDED.crime_name
                   RETURNING *""",
                (entity.name, props.get("description")),
            )
        return rows[0]["crime_id"], rows[0]
    if kind == "Location":
        city, state = props.get("city") or entity.name, props.get("state")
        rows = await tx.query(
            "SELECT * FROM locations WHERE lower(city)=lower(%s) AND state IS NOT DISTINCT FROM %s",
            (city, state),
        )
        if not rows:
            rows = await tx.query(
                "INSERT INTO locations (city,state) VALUES (%s,%s) RETURNING *", (city, state)
            )
        # Geometry is not a Neo4j property; preserve only the mapped source fields.
        return rows[0]["location_id"], {k: v for k, v in rows[0].items() if k != "geom"}
    return entity_id, {"name": entity.name, "number": identifier or entity.name}


async def persist_extraction(db, document_id, result):
    async with db.transaction() as tx:
        # Serialize imports to avoid duplicate shared lookups across server workers.
        await tx.query("SELECT pg_advisory_xact_lock(724013)")
        rows = await tx.query(
            "SELECT graph_payload, confirmed_at FROM officer_documents WHERE document_id=%s FOR UPDATE",
            (document_id,),
        )
        if rows[0]["graph_payload"] is not None:
            return rows[0]["graph_payload"]
        if rows[0]["confirmed_at"] is None:
            raise APIError("Review and confirm the extraction before saving records.", 409)
        nodes, refs = [], {}
        for entity in result.entities:
            entity_id = stable_id(document_id, entity.ref)
            props = properties_for(entity)
            canonical, row = await canonical_entity(tx, entity, entity_id, props)
            # Convert dates and numeric coordinates to graph-compatible scalar values.
            graph_props = {
                k: (v if isinstance(v, (str, int, float, bool)) else str(v))
                for k, v in row.items()
                if v is not None
            }
            graph_props.setdefault("name", entity.name)
            graph_props[NODE_KEYS[entity.kind]] = canonical
            graph_props["source"] = "document_extraction"
            graph_props["review_status"] = "unverified"
            nodes.append({"kind": entity.kind, "id": canonical, "properties": graph_props})
            refs[entity.ref] = {"entity_id": entity_id, "kind": entity.kind, "id": canonical}
            await tx.query(
                """INSERT INTO extracted_entities
                   (entity_id,document_id,kind,canonical_id,name,properties,evidence)
                   VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                (
                    entity_id,
                    document_id,
                    entity.kind,
                    str(canonical),
                    entity.name,
                    Jsonb({**props, "source_identifier": entity.identifier}),
                    entity.evidence,
                ),
            )
        edges = []
        for relation in result.relationships:
            subject, target = refs[relation.subject], refs[relation.object]
            relation_id = stable_id(
                document_id, relation.subject, relation.predicate, relation.object
            )
            await tx.query(
                """INSERT INTO extracted_relationships
                   (relationship_id,document_id,subject_id,predicate,object_id,evidence)
                   VALUES (%s,%s,%s,%s,%s,%s)""",
                (
                    relation_id,
                    document_id,
                    subject["entity_id"],
                    relation.predicate,
                    target["entity_id"],
                    relation.evidence,
                ),
            )
            edges.append(
                {
                    "id": relation_id,
                    "subject": subject,
                    "object": target,
                    "predicate": relation.predicate,
                    "evidence": relation.evidence,
                }
            )
            # Populate legacy single-value case columns only for newly imported cases.
            if relation.predicate in ("OCCURRED_AT", "OF_TYPE") and str(subject["id"]).startswith(
                "D"
            ):
                column = "location_id" if relation.predicate == "OCCURRED_AT" else "crime_id"
                await tx.query(
                    f"UPDATE cases SET {column}=COALESCE({column},%s) WHERE case_id=%s",
                    (target["id"], subject["id"]),
                )
        payload = {"document_id": document_id, "nodes": nodes, "edges": edges}
        await tx.query(
            """UPDATE officer_documents SET graph_payload=%s,
            processing_status='syncing' WHERE document_id=%s""",
            (Jsonb(payload), document_id),
        )
        return payload


async def sync_graph(graph, payload):
    # Labels and predicates come only from validated allowlists, never raw model strings.
    async def write(tx):
        for node in payload["nodes"]:
            kind, key = node["kind"], NODE_KEYS[node["kind"]]
            result = await tx.run(
                f"MERGE (n:{kind} {{{key}: $id}}) ON CREATE SET n += $props",
                id=node["id"],
                props=node["properties"],
            )
            await result.consume()
        for edge in payload["edges"]:
            subject, target = edge["subject"], edge["object"]
            # Validate again at the database boundary, including replays from stored payloads.
            allowed_s, allowed_o = RELATION_RULES[edge["predicate"]]
            if subject["kind"] not in allowed_s or target["kind"] not in allowed_o:
                raise ValueError("Invalid stored relationship")
            result = await tx.run(
                f"MATCH (a:{subject['kind']} {{{NODE_KEYS[subject['kind']]}: $subject}}), "
                f"(b:{target['kind']} {{{NODE_KEYS[target['kind']]}: $object}}) "
                f"MERGE (a)-[r:{edge['predicate']} {{extraction_id: $id}}]->(b) "
                "SET r.source='document_extraction', r.document_id=$document, "
                "r.evidence=$evidence, r.review_status='unverified'",
                subject=subject["id"],
                object=target["id"],
                id=edge["id"],
                document=payload["document_id"],
                evidence=edge["evidence"],
            )
            await result.consume()

    async with graph.driver.session() as session:
        for kind, key in NODE_KEYS.items():
            result = await session.run(
                f"CREATE CONSTRAINT ingestion_{key}_unique IF NOT EXISTS "
                f"FOR (n:{kind}) REQUIRE n.{key} IS UNIQUE"
            )
            await result.consume()
        await session.execute_write(write)
