import os
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from fastapi import Request, HTTPException
from fastapi.responses import RedirectResponse

SECRET_KEY = os.environ.get("SECRET_KEY", "contalibra-secret-change-me")
APP_USER = os.environ.get("APP_USER", "admin")
APP_PASSWORD = os.environ.get("APP_PASSWORD", "admin")

_signer = URLSafeTimedSerializer(SECRET_KEY)
COOKIE_NAME = "cl_session"


def create_session_cookie(response, username: str):
    token = _signer.dumps(username)
    response.set_cookie(COOKIE_NAME, token, httponly=True, samesite="lax")


def clear_session_cookie(response):
    response.delete_cookie(COOKIE_NAME)


def get_current_user(request: Request) -> str | None:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    try:
        return _signer.loads(token, max_age=86400 * 7)
    except (BadSignature, SignatureExpired):
        return None


def require_auth(request: Request) -> str:
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=307, headers={"Location": "/login"})
    return user


def check_credentials(username: str, password: str) -> bool:
    return username == APP_USER and password == APP_PASSWORD
