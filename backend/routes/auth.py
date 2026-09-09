from fastapi import APIRouter, Depends, Request, Response
from starlette.concurrency import run_in_threadpool

from ..errors import APIError, api_errors
from ..models import LoginBody
from ..security import PROFILE_FIELDS, require_auth, sign_officer_token, verify_password

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/login")
async def login(request: Request, response: Response, body: LoginBody | None = None):
    if body is None or not body.username or not body.password:
        raise APIError("Username and password are required", 400)
    settings = request.app.state.settings
    with api_errors("Login failed"):
        # The configured administrator can log in without an officer database row.
        if (
            settings.admin_username
            and settings.admin_password
            and body.username == settings.admin_username
            and body.password == settings.admin_password
        ):
            profile = {
                "officerId": None,
                "username": settings.admin_username,
                "name": "Administrator",
                "orgName": "System",
                "role": "admin",
            }
        else:
            rows = await request.app.state.db.query(
                """SELECT officer_id, username, password_hash, name, org_name, role, is_active
                   FROM officers WHERE username = %s""",
                (body.username,),
            )
            officer = rows[0] if rows else None
            if not officer or not officer["is_active"]:
                raise APIError("Invalid credentials", 401)
            # Run bcrypt in a thread so password checks do not block other requests.
            if not await run_in_threadpool(
                verify_password, body.password, officer["password_hash"]
            ):
                raise APIError("Invalid credentials", 401)
            profile = {
                "officerId": officer["officer_id"],
                "username": officer["username"],
                "name": officer["name"],
                "orgName": officer["org_name"],
                "role": officer["role"],
            }
        response.set_cookie(
            settings.cookie_name,
            sign_officer_token(profile, settings),
            httponly=True,
            samesite="lax",
            secure=settings.production,
            max_age=12 * 60 * 60,
        )
        return profile


@router.post("/logout")
async def logout(request: Request, response: Response):
    response.delete_cookie(request.app.state.settings.cookie_name)
    return {"ok": True}


@router.get("/me")
async def me(officer=Depends(require_auth)):
    return {field: officer.get(field) for field in PROFILE_FIELDS}
