from fastapi import APIRouter, Depends, Request

from ..errors import api_errors
from ..security import require_auth

router = APIRouter(
    prefix="/api/crime-types", tags=["Crime types"], dependencies=[Depends(require_auth)]
)


# Accept both trailing-slash forms while documenting one endpoint.
@router.get("/", include_in_schema=False)
@router.get("")
async def get_crime_types(request: Request):
    with api_errors("Failed to load crime types"):
        rows = await request.app.state.db.query(
            "SELECT crime_name FROM crime_types ORDER BY crime_name"
        )
        return [row["crime_name"] for row in rows]
