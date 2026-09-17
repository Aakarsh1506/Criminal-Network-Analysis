"""Reuse unambiguous records; propose, never infer, a person's identity."""

import re

from ..errors import APIError

TABLES = {
    "Person": ("persons", "person_id"), "Case": ("cases", "case_id"),
    "Organization": ("organizations", "organization_id"), "Vehicle": ("vehicles", "vehicle_id"),
    "Location": ("locations", "location_id"), "CrimeType": ("crime_types", "crime_id"),
}


def normalized(value):
    return " ".join((value or "").split()).casefold()


def text_match(column):
    # Column names are internal constants only.
    return f"lower(regexp_replace(btrim({column}), '\\s+', ' ', 'g')) = %s"


def phone_digits(value):
    digits = re.sub(r"\D", "", value or "")
    if digits.startswith("0091") and len(digits) == 14:
        return digits[4:]
    if digits.startswith("91") and len(digits) == 12:
        return digits[2:]
    return digits


async def person_by_strong_identifier(db, name, props):
    """Reuse a same-name person only when a recorded phone, DOB or alias also matches."""
    matches = set()
    if props.get("dob"):
        rows = await db.query(
            f"SELECT person_id FROM persons WHERE {text_match('name')} AND dob=%s::date",
            (normalized(name), props["dob"]),
        )
        matches.update(row["person_id"] for row in rows)
    if props.get("alias"):
        rows = await db.query(
            f"SELECT person_id FROM persons WHERE {text_match('name')} AND {text_match('alias')}",
            (normalized(name), normalized(props["alias"])),
        )
        matches.update(row["person_id"] for row in rows)
    if len(phone_digits(props.get("phone"))) >= 10:
        rows = await db.query(
            f"""SELECT DISTINCT e.canonical_id AS person_id FROM extracted_entities e
               JOIN persons p ON p.person_id=e.canonical_id
               WHERE e.kind='Person' AND {text_match('p.name')}
                 AND right(regexp_replace(e.properties->>'phone', '[^0-9]', '', 'g'), 10)=%s""",
            (normalized(name), phone_digits(props["phone"])[-10:]),
        )
        matches.update(row["person_id"] for row in rows)
    # Conflicting identifiers (two different people) are left for officer review.
    if len(matches) != 1:
        return None
    rows = await db.query("SELECT * FROM persons WHERE person_id=%s", (matches.pop(),))
    return (rows[0]["person_id"], rows[0]) if rows else None


async def find_existing(db, entity, props):
    """Return (canonical ID, row) only for a known, unambiguous identity."""
    kind, identifier = entity.kind, entity.identifier
    if kind == "PhoneNumber":
        digits = phone_digits(identifier or entity.name)
        variants = [digits]
        if len(digits) == 10:
            variants += ["91" + digits, "0091" + digits]
        rows = await db.query(
            """SELECT canonical_id, name, properties FROM extracted_entities
               WHERE kind='PhoneNumber' AND regexp_replace(
                 coalesce(properties->>'source_identifier', name), '[^0-9]', '', 'g') = ANY(%s)
               ORDER BY entity_id LIMIT 1""", (variants,),
        )
        if rows:
            row = rows[0]
            return row["canonical_id"], {"name": row["name"], "number": identifier or entity.name}
        return None
    table, key = TABLES[kind]
    if identifier:
        rows = await db.query(f"SELECT * FROM {table} WHERE {key}::text=%s", (identifier,))
        if rows:
            if kind == "Person" and normalized(rows[0]["name"]) != normalized(entity.name):
                raise APIError("An extracted person ID conflicts with an existing name.", 409)
            return rows[0][key], rows[0]
        matches = await db.query(
            """SELECT DISTINCT canonical_id FROM extracted_entities
               WHERE kind=%s AND lower(btrim(properties->>'source_identifier'))=%s""",
            (kind, identifier.strip().lower()),
        )
        if len(matches) == 1:
            rows = await db.query(f"SELECT * FROM {table} WHERE {key}::text=%s", (matches[0]["canonical_id"],))
            if rows and (kind != "Person" or normalized(rows[0]["name"]) == normalized(entity.name)):
                return rows[0][key], rows[0]
    if kind == "Person":
        # A shared name alone is not an identity key; same-name people go to review.
        return await person_by_strong_identifier(db, entity.name, props)
    if kind in {"Organization", "CrimeType"}:
        column = "name" if kind == "Organization" else "crime_name"
        rows = await db.query(f"SELECT * FROM {table} WHERE {text_match(column)}", (normalized(entity.name),))
    elif kind == "Location":
        city, state = normalized(props.get("city") or entity.name), normalized(props.get("state"))
        rows = await db.query(f"SELECT * FROM locations WHERE {text_match('city')}", (city,))
        if state:
            rows = [r for r in rows if normalized(r.get("state")) == state]
        # Without a state only reuse an unambiguous city, never guess among states.
    elif kind == "Vehicle":
        registration = re.sub(r"[^A-Z0-9]", "", (props.get("registration") or identifier or entity.name).upper())
        rows = await db.query(
            "SELECT * FROM vehicles WHERE regexp_replace(upper(registration), '[^A-Z0-9]', '', 'g')=%s",
            (registration,),
        )
    else:  # FIR labels can exist without a source_identifier.
        matches = await db.query(
            f"SELECT DISTINCT canonical_id FROM extracted_entities WHERE kind='Case' AND {text_match('name')}",
            (normalized(entity.name),),
        )
        rows = await db.query("SELECT * FROM cases WHERE case_id=%s", (matches[0]["canonical_id"],)) if len(matches) == 1 else []
    if len(rows) == 1:
        return rows[0][key], {k: v for k, v in rows[0].items() if k != "geom"}
    return None


async def person_suggestions(db, graph, extraction):
    resolved = {}
    for entity in extraction.entities:
        existing = await find_existing(db, entity, {a.key: a.value for a in entity.attributes})
        if existing:
            resolved[entity.ref] = (entity.kind, str(existing[0]))
    suggestions = []
    for entity in extraction.entities:
        if entity.kind != "Person" or entity.ref in resolved:
            continue
        candidates = await db.query(
            f"SELECT person_id,name,age,city,state FROM persons WHERE {text_match('name')} ORDER BY person_id",
            (normalized(entity.name),),
        )
        if not candidates:
            continue
        neighbours = {}
        by_ref = {e.ref: e for e in extraction.entities}
        for relation in extraction.relationships:
            other = relation.object if relation.subject == entity.ref else relation.subject if relation.object == entity.ref else None
            if other in resolved:
                neighbours[resolved[other]] = by_ref[other].name
        ids = [c["person_id"] for c in candidates]
        # Imported links, including ones not yet synced to Neo4j. Their case names also tell
        # the officer which FIRs each existing record already appears in.
        rows = await db.query(
            """SELECT DISTINCT p.canonical_id AS person_id, n.kind, n.canonical_id AS id, n.name
               FROM extracted_relationships r
               JOIN extracted_entities p ON p.entity_id IN (r.subject_id,r.object_id) AND p.kind='Person'
               JOIN extracted_entities n ON n.entity_id=CASE WHEN r.subject_id=p.entity_id THEN r.object_id ELSE r.subject_id END
               WHERE p.canonical_id=ANY(%s)""", (ids,),
        )
        existing = {identifier: set() for identifier in ids}
        cases = {identifier: set() for identifier in ids}
        for row in rows:
            existing[row["person_id"]].add((row["kind"], str(row["id"])))
            if row["kind"] == "Case":
                cases[row["person_id"]].add(row["name"])
        # Every same-name person is offered for review; shared connections are evidence
        # for the officer, not a threshold. Separate FIRs often share none.
        if neighbours:
            try:
                graph_rows = await graph.run(
                    "MATCH (p:Person)-[]-(n) WHERE p.person_id IN $ids "
                    "RETURN p.person_id AS person_id, labels(n) AS kinds, "
                    "toString(coalesce(n.person_id,n.case_id,n.location_id,n.crime_id,"
                    "n.organization_id,n.vehicle_id,n.phone_id)) AS id", {"ids": ids},
                )
            except Exception:
                raise APIError("Could not check shared connections in Neo4j. Retry identity review when it is available.", 503) from None
            for row in graph_rows:
                for kind in row["kinds"]:
                    existing[row["person_id"]].add((kind, str(row["id"])))
        ranked = sorted(candidates, key=lambda c: -len(existing[c["person_id"]] & neighbours.keys()))
        for candidate in ranked:
            common = sorted(existing[candidate["person_id"]] & neighbours.keys())
            suggestions.append({
                "ref": entity.ref, "name": entity.name, "personId": candidate["person_id"],
                "age": candidate.get("age"), "city": candidate.get("city"), "state": candidate.get("state"),
                "cases": sorted(cases[candidate["person_id"]]),
                "sharedConnections": [{"kind": kind, "id": identifier, "name": neighbours[(kind, identifier)]}
                                      for kind, identifier in common],
            })
    return suggestions
