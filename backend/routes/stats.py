import asyncio

from fastapi import APIRouter, Depends, Request
from psycopg.errors import UndefinedTable

from ..errors import api_errors
from ..security import require_auth

router = APIRouter(prefix="/api/stats", tags=["Statistics"], dependencies=[Depends(require_auth)])


@router.get("/", include_in_schema=False)
@router.get("")
async def get_stats(request: Request):
    db = request.app.state.db
    with api_errors("Failed to load stats"):
        # Fetch independent dashboard totals concurrently.
        totals, tags, cities, cases = await asyncio.gather(
            db.query("SELECT COUNT(*)::int AS count FROM persons"),
            db.query("""SELECT ct.crime_name, COUNT(DISTINCT cp.person_id)::int AS count
                        FROM cases c JOIN case_people cp ON cp.case_id=c.case_id
                        JOIN crime_types ct ON ct.crime_id = c.crime_id
                        GROUP BY ct.crime_name ORDER BY count DESC"""),
            db.query(
                "SELECT city, COUNT(*)::int AS count FROM persons GROUP BY city ORDER BY count DESC"
            ),
            db.query("SELECT COUNT(*)::int AS count FROM cases"),
        )
        traced = 0
        try:
            rows = await db.query("SELECT COUNT(*)::int AS count FROM associations")
            traced = rows[0]["count"]
        except UndefinedTable:
            # Older databases may not have the optional associations table.
            pass
        return {
            "totalCriminals": totals[0]["count"],
            "totalCases": cases[0]["count"],
            "tracedConnections": traced,
            "tagCounts": [[row["crime_name"], row["count"]] for row in tags],
            "cityCounts": [[row["city"], row["count"]] for row in cities],
        }
