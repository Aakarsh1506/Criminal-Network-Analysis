import asyncio
import logging
from datetime import date, datetime, timezone

from ..utils.avatar import color_for_id, initials_avatar
from ..utils.map_coordinates import coordinates_for_city

logger = logging.getLogger(__name__)

PERSONS_SQL = "\n      SELECT p.*,\n             array_remove(array_agg(DISTINCT ct.crime_name), NULL) AS crime_tags\n      FROM persons p\n      LEFT JOIN cases c ON c.person_id = p.person_id\n      LEFT JOIN crime_types ct ON ct.crime_id = c.crime_id\n      {where_clause}\n      GROUP BY p.person_id\n    "
CASES_SQL = "\n  SELECT c.case_id, c.case_month, c.case_status, l.city, l.state, ct.crime_name\n  FROM cases c\n  LEFT JOIN crime_types ct ON ct.crime_id = c.crime_id\n  LEFT JOIN locations l ON l.location_id = c.location_id\n  WHERE c.person_id = %s\n  ORDER BY c.case_month DESC\n"
ASSOCIATES_QUERY = "\n      MATCH (p1:Person {person_id: $id})-[:INVOLVED_IN]->(c1:Case)\n      MATCH (p2:Person)-[:INVOLVED_IN]->(c2:Case)\n      WHERE p1 <> p2\n      OPTIONAL MATCH (c1)-[:OCCURRED_AT]->(l:Location)<-[:OCCURRED_AT]-(c2)\n      OPTIONAL MATCH (c1)-[:OF_TYPE]->(crime:CrimeType)<-[:OF_TYPE]-(c2)\n      WITH p2, l, crime\n      WHERE l IS NOT NULL OR crime IS NOT NULL\n      RETURN DISTINCT\n        p2.person_id AS other_id,\n        p2.name AS other_name,\n        p2.alias AS other_alias,\n        p2.city AS other_city,\n        p2.state AS other_state,\n        l.city AS shared_location,\n        crime.crime_name AS shared_crime\n      LIMIT 25\n      "


def date_string(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        value = value.astimezone(timezone.utc) if value.tzinfo else value
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value)[:10]


def map_person(row):
    city = row.get("city")
    last_seen = row.get("last_seen")
    if last_seen:
        seen = date.fromisoformat(date_string(last_seen))
        months = (
            "Jan",
            "Feb",
            "Mar",
            "Apr",
            "May",
            "Jun",
            "Jul",
            "Aug",
            "Sept",
            "Oct",
            "Nov",
            "Dec",
        )
        last_seen = f"{city} — {seen.day:02d} {months[seen.month - 1]} {seen.year}"
    return {
        "id": row["person_id"],
        "name": row["name"],
        "alias": row.get("alias"),
        "dob": date_string(row.get("dob")),
        "age": row.get("age"),
        "heightCm": row.get("height_cm"),
        "location": {"city": city, "state": row.get("state"), **coordinates_for_city(city)},
        "lastSeen": last_seen or city,
        "familyKnown": row.get("family_known"),
        "recordStatus": row.get("record_status"),
        "crimeTags": list(filter(None, row.get("crime_tags") or [])),
        "photo": row.get("photo") or initials_avatar(row["name"], color_for_id(row["person_id"])),
    }


async def fetch_associates(person_id, graph):
    try:
        records = await graph.run(ASSOCIATES_QUERY, {"id": person_id})
        return [
            {
                "criminal": {
                    "id": row["other_id"],
                    "name": row["other_name"],
                    "alias": row.get("other_alias"),
                    "location": {"city": row.get("other_city"), "state": row.get("other_state")},
                    "photo": initials_avatar(row["other_name"], color_for_id(row["other_id"])),
                },
                "type": f"Shared Crime: {row['shared_crime']}"
                if row.get("shared_crime")
                else f"Shared Location: {row.get('shared_location')}",
            }
            for row in records
        ]
    except Exception:
        logger.exception("Neo4j associate lookup failed")
        return []


async def load_profile(person_id, db, graph):
    rows = await db.query(PERSONS_SQL.format(where_clause="WHERE p.person_id = %s"), (person_id,))
    if not rows:
        return None
    criminal = map_person(rows[0])
    cases, relations = await asyncio.gather(
        db.query(CASES_SQL, (person_id,)),
        fetch_associates(person_id, graph),
    )
    criminal["cases"] = [
        {
            "caseId": row["case_id"],
            "crime": row.get("crime_name"),
            "location": f"{row['city']}, {row.get('state')}" if row.get("city") else None,
            "status": row.get("case_status"),
            "month": date_string(row.get("case_month")),
        }
        for row in cases
    ]
    return {"criminal": criminal, "relations": relations}
