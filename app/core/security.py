from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException, Request, status
from jwt.exceptions import InvalidTokenError

from app.core.config import Settings, get_settings

SESSION_COOKIE_NAME = "fincore_session"


def create_session_token(user_id: str, settings: Settings) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


async def get_current_user(request: Request) -> dict:
    """Require a valid FinCore session and return its MongoDB user document."""
    settings = get_settings()
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        authorization = request.headers.get("Authorization", "")
        if authorization.startswith("Bearer "):
            token = authorization.removeprefix("Bearer ")

    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")

    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        user_id = payload.get("sub")
        if not isinstance(user_id, str) or not user_id:
            raise InvalidTokenError("Missing session subject")
    except InvalidTokenError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session.") from error

    user = await request.app.state.mongo.database.users.find_one({"google_sub": user_id})
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session user no longer exists.")
    return user
