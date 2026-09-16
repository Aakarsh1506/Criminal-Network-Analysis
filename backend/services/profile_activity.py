"""Source-backed profile logs and connected locations; no generated activity."""

import logging
from .extraction import evidence_names_entity

logger = logging.getLogger(__name__)

GRAPH_LOCATION_QUERY = """
MATCH path=(p:Person {person_id:$id})-[*1..2]-(l:Location)
WHERE length(path)=1 OR 'Case' IN labels(nodes(path)[1])
RETURN l.city AS city,l.state AS state,l.name AS name
ORDER BY length(path),coalesce(l.city,l.name),elementId(l) LIMIT 1
"""
LOCATION_SQL = """
WITH candidates AS (
  SELECT l.location_id,l.city,l.state, r.predicate AS connection,
         CASE WHEN r.predicate='SEEN_AT' THEN 0 ELSE 1 END AS priority,
         d.uploaded_at AS recorded_at
  FROM extracted_relationships r
  JOIN extracted_entities p ON p.entity_id=r.subject_id AND p.kind='Person'
  JOIN extracted_entities target ON target.entity_id=r.object_id AND target.kind='Location'
  JOIN locations l ON l.location_id::text=target.canonical_id
  JOIN officer_documents d ON d.document_id=r.document_id
  WHERE p.canonical_id=%s AND r.predicate IN ('SEEN_AT','RESIDES_IN')
  UNION ALL
  SELECT l.location_id,l.city,l.state,'LINKED_CASE',2,NULL
  FROM case_people cp JOIN cases c ON c.case_id=cp.case_id
  JOIN locations l ON l.location_id=c.location_id WHERE cp.person_id=%s
)
SELECT * FROM candidates ORDER BY priority, recorded_at DESC NULLS LAST,location_id LIMIT 1
"""

ACTIVITY_SQL = """
SELECT r.relationship_id AS id,r.predicate AS kind,
       subject.name AS subject, target.name AS object,r.evidence,
       d.document_id,d.original_name,d.officer_id,d.uploaded_at AS recorded_at,
       subject.kind AS subject_kind,target.kind AS object_kind,
       subject.properties->>'source_identifier' AS subject_identifier,
       target.properties->>'source_identifier' AS object_identifier
FROM extracted_relationships r
JOIN extracted_entities subject ON subject.entity_id=r.subject_id
JOIN extracted_entities target ON target.entity_id=r.object_id
JOIN officer_documents d ON d.document_id=r.document_id
WHERE (subject.kind='Person' AND subject.canonical_id=%s)
   OR (target.kind='Person' AND target.canonical_id=%s)
UNION ALL
SELECT e.entity_id,'PERSON_RECORD',e.name,NULL,e.evidence,
       d.document_id,d.original_name,d.officer_id,d.uploaded_at,
       e.kind,NULL,e.properties->>'source_identifier',NULL
FROM extracted_entities e JOIN officer_documents d ON d.document_id=e.document_id
WHERE e.kind='Person' AND e.canonical_id=%s
ORDER BY recorded_at DESC,id
"""


async def load_activity(person_id, db, officer_id, graph=None):
    rows = await db.query(ACTIVITY_SQL, (person_id, person_id, person_id))
    entries = [
        {
            "id": row["id"], "kind": row["kind"], "subject": row["subject"],
            "object": row["object"], "evidence": row["evidence"],
            "recordedAt": row["recorded_at"],
            "documentId": row["document_id"], "documentName": row["original_name"],
            "canOpenSource": row["officer_id"] == officer_id,
            "needsReview": any(
                row.get(endpoint) and row.get(f"{endpoint}_kind") != "Case"
                and not evidence_names_entity(
                    row["evidence"], row[endpoint], row.get(f"{endpoint}_identifier")
                ) for endpoint in ("subject", "object")
            ),
        } for row in rows
    ]
    locations = await db.query(LOCATION_SQL, (person_id, person_id))
    location = locations[0] if locations else None
    if location is None and graph is not None:
        try:
            graph_locations = await graph.run(GRAPH_LOCATION_QUERY, {"id": person_id})
            if graph_locations:
                place = graph_locations[0]
                location = {"city": place.get("city") or place.get("name"),
                            "state": place.get("state"), "connection": "GRAPH"}
        except Exception:
            logger.warning("Graph location unavailable for profile")
    return {"entries": entries, "location": location}
