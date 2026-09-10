import asyncio

from fastapi import APIRouter, Depends, Request

from ..errors import APIError, api_errors
from ..models import PersonBody
from ..security import require_auth

router = APIRouter(prefix="/api/workspace", tags=["Workspace"])
LIST_ITEMS_SQL = """
  SELECT p.person_id, p.name,
         array_remove(array_agg(DISTINCT ct.crime_name), NULL) AS crime_tags
  FROM officer_working_list w
  JOIN persons p ON p.person_id = w.person_id
  LEFT JOIN case_people cp ON cp.person_id = p.person_id
  LEFT JOIN cases c ON c.case_id = cp.case_id
  LEFT JOIN crime_types ct ON ct.crime_id = c.crime_id
  WHERE w.officer_id = %s
  GROUP BY p.person_id, w.added_at
  ORDER BY w.added_at ASC
"""


@router.get("/", include_in_schema=False)
@router.get("")
async def get_workspace(request: Request, officer=Depends(require_auth)):
    # Scope both the pin and working list to the signed-in officer.
    with api_errors("Failed to load workspace"):
        pinned, rows = await asyncio.gather(
            request.app.state.db.query(
                "SELECT person_id FROM officer_pinned_criminal WHERE officer_id = %s",
                (officer["officerId"],),
            ),
            request.app.state.db.query(LIST_ITEMS_SQL, (officer["officerId"],)),
        )
        return {
            "pinnedId": pinned[0]["person_id"] if pinned else None,
            "workingList": [
                {
                    "id": row["person_id"],
                    "name": row["name"],
                    "crimeTags": list(filter(None, row.get("crime_tags") or [])),
                }
                for row in rows
            ],
        }


@router.put("/pin")
async def pin(request: Request, body: PersonBody | None = None, officer=Depends(require_auth)):
    if body is None or not body.personId:
        raise APIError("personId is required", 400)
    with api_errors("Failed to pin criminal"):
        # Each officer has one pin; pinning again replaces it.
        await request.app.state.db.query(
            """INSERT INTO officer_pinned_criminal (officer_id, person_id, pinned_at)
               VALUES (%s, %s, now())
               ON CONFLICT (officer_id) DO UPDATE
               SET person_id = EXCLUDED.person_id, pinned_at = now()""",
            (officer["officerId"], body.personId),
        )
        return {"pinnedId": body.personId}


@router.delete("/pin")
async def unpin(request: Request, officer=Depends(require_auth)):
    with api_errors("Failed to unpin criminal"):
        await request.app.state.db.query(
            "DELETE FROM officer_pinned_criminal WHERE officer_id = %s",
            (officer["officerId"],),
        )
        return {"pinnedId": None}


@router.post("/list", status_code=201)
async def add_to_list(
    request: Request, body: PersonBody | None = None, officer=Depends(require_auth)
):
    if body is None or not body.personId:
        raise APIError("personId is required", 400)
    with api_errors("Failed to add to list"):
        # Repeated additions leave the existing list entry unchanged.
        await request.app.state.db.query(
            """INSERT INTO officer_working_list (officer_id, person_id) VALUES (%s, %s)
               ON CONFLICT (officer_id, person_id) DO NOTHING""",
            (officer["officerId"], body.personId),
        )
        return {"ok": True}


@router.delete("/list/{person_id}")
async def remove_from_list(person_id: str, request: Request, officer=Depends(require_auth)):
    with api_errors("Failed to remove from list"):
        await request.app.state.db.query(
            "DELETE FROM officer_working_list WHERE officer_id = %s AND person_id = %s",
            (officer["officerId"], person_id),
        )
        return {"ok": True}
