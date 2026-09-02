from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from google.auth.exceptions import GoogleAuthError
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from app.core.config import get_settings
from app.core.security import SESSION_COOKIE_NAME, create_session_token, get_current_user
from app.models.auth import GoogleTokenRequest, SessionUser

router = APIRouter(prefix="/auth", tags=["authentication"])


def serialize_user(user: dict) -> SessionUser:
    return SessionUser(
        id=str(user["_id"]),
        email=user["email"],
        display_name=user.get("display_name"),
        avatar_url=user.get("avatar_url"),
    )


@router.post("/google", response_model=SessionUser)
async def sign_in_with_google(payload: GoogleTokenRequest, request: Request, response: Response) -> SessionUser:
    settings = get_settings()
    try:
        claims = id_token.verify_oauth2_token(
            payload.credential,
            google_requests.Request(),
            settings.google_client_id,
        )
    except (GoogleAuthError, ValueError) as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google ID token is invalid, expired, or issued for another client.",
        ) from error

    google_sub = claims.get("sub")
    email = claims.get("email")
    if not isinstance(google_sub, str) or not isinstance(email, str) or not claims.get("email_verified"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="A verified Google email is required.")

    now = datetime.now(timezone.utc)
    users = request.app.state.mongo.database.users
    existing = await users.find_one({"google_sub": google_sub})
    user_id = existing["_id"] if existing else google_sub
    await users.update_one(
        {"_id": user_id},
        {
            "$set": {
                "google_sub": google_sub,
                "email": email.lower(),
                "display_name": claims.get("name"),
                "avatar_url": claims.get("picture"),
                "last_login_at": now,
                "updated_at": now,
            },
            "$setOnInsert": {"created_at": now},
        },
        upsert=True,
    )
    user = await users.find_one({"_id": user_id})
    token = create_session_token(google_sub, settings)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=settings.jwt_expire_minutes * 60,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )
    return serialize_user(user)


@router.get("/me", response_model=SessionUser)
async def current_session_user(user: dict = Depends(get_current_user)) -> SessionUser:
    return serialize_user(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response) -> None:
    response.delete_cookie(key=SESSION_COOKIE_NAME, path="/")
