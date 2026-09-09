from datetime import date

from fastapi import APIRouter, Depends, Request
from psycopg.errors import UniqueViolation
from starlette.concurrency import run_in_threadpool

from ..errors import APIError, api_errors
from ..models import OfficerBody
from ..security import hash_password, require_admin

router = APIRouter(prefix="/api/officers", tags=["Officers"], dependencies=[Depends(require_admin)])


@router.get("/", include_in_schema=False)
@router.get("")
async def list_officers(request: Request):
    with api_errors("Failed to load officers"):
        return await request.app.state.db.query(
            """SELECT officer_id, username, name, dob, org_name, role, is_active, created_at
               FROM officers ORDER BY created_at DESC"""
        )


@router.post("/", status_code=201, include_in_schema=False)
@router.post("", status_code=201)
async def create_officer(request: Request, body: OfficerBody | None = None):
    missing = [
        key
        for key in ("username", "password", "name", "orgName")
        if body is None or not getattr(body, key)
    ]
    if missing:
        raise APIError(f"Missing required field(s): {', '.join(missing)}", 400)
    if len(body.password) < 8:
        raise APIError("Password must be at least 8 characters", 400)
    with api_errors("Failed to create officer"):
        password_hash = await run_in_threadpool(hash_password, body.password)
        try:
            rows = await request.app.state.db.query(
                """INSERT INTO officers (username, password_hash, name, dob, org_name, role)
                   VALUES (%s, %s, %s, %s, %s, 'officer')
                   RETURNING officer_id, username, name, dob, org_name, role, is_active, created_at""",
                (
                    body.username,
                    password_hash,
                    body.name,
                    date.fromisoformat(body.dob) if body.dob else None,
                    body.orgName,
                ),
            )
        except UniqueViolation:
            raise APIError(f'Username "{body.username}" already exists', 409) from None
        return rows[0]


@router.patch("/{officer_id}/deactivate")
async def deactivate_officer(officer_id: int, request: Request):
    with api_errors("Failed to deactivate officer"):
        rows = await request.app.state.db.query(
            """UPDATE officers SET is_active = FALSE WHERE officer_id = %s
               RETURNING officer_id, username, is_active""",
            (officer_id,),
        )
        if not rows:
            raise APIError("Officer not found", 404)
        return rows[0]
