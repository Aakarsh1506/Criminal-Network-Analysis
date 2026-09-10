import re
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, Request

from .errors import APIError

PROFILE_FIELDS = ("officerId", "username", "name", "orgName", "role")


def token_lifetime(value):
    # jsonwebtoken treats a unitless environment string as milliseconds.
    match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*([a-zA-Z]*)\s*", str(value))
    units = {
        "": 0.001,
        "ms": 0.001,
        "millisecond": 0.001,
        "milliseconds": 0.001,
        "s": 1,
        "sec": 1,
        "secs": 1,
        "second": 1,
        "seconds": 1,
        "m": 60,
        "min": 60,
        "mins": 60,
        "minute": 60,
        "minutes": 60,
        "h": 3600,
        "hr": 3600,
        "hrs": 3600,
        "hour": 3600,
        "hours": 3600,
        "d": 86400,
        "day": 86400,
        "days": 86400,
        "w": 604800,
        "week": 604800,
        "weeks": 604800,
        "y": 31557600,
        "yr": 31557600,
        "yrs": 31557600,
        "year": 31557600,
        "years": 31557600,
    }
    if not match or match[2].lower() not in units:
        raise ValueError("JWT_EXPIRES_IN must be a duration such as 12h or 7d")
    return timedelta(seconds=float(match[1]) * units[match[2].lower()])


def sign_officer_token(profile, settings):
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {**profile, "iat": now, "exp": now + token_lifetime(settings.jwt_expires_in)},
        settings.jwt_secret,
        algorithm="HS256",
    )


def hash_password(password):
    # Node bcrypt truncates at 72 UTF-8 bytes; preserve existing hash semantics.
    return bcrypt.hashpw(password.encode("utf-8")[:72], bcrypt.gensalt(rounds=12)).decode()


def verify_password(password, password_hash):
    try:
        return bcrypt.checkpw(password.encode("utf-8")[:72], password_hash.encode())
    except (ValueError, TypeError, AttributeError):
        return False


def require_auth(request: Request):
    settings = request.app.state.settings
    token = request.cookies.get(settings.cookie_name)
    if not token:
        raise APIError("Not authenticated", 401)
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        # Use officer details only after verifying the token's signature and expiry.
        if not all(field in payload for field in PROFILE_FIELDS):
            raise jwt.InvalidTokenError("Missing officer claims")
        return payload
    except jwt.InvalidTokenError:
        raise APIError("Session expired, please log in again", 401, clear_cookie=True) from None


def require_admin(officer=Depends(require_auth)):
    if officer.get("role") != "admin":
        raise APIError("Admin access required", 403)
    return officer
