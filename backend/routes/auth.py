"""
Auth - Single-operator gate.

Replaces the previous Emergent-managed OAuth path with a vendor-neutral
OPERATOR_TOKEN flow:

  - Set OPERATOR_TOKEN=<long_random_string>  in the backend .env
  - Set OPERATOR_EMAIL=<your_email>          in the backend .env
  - Frontend prompts for the token at /login → POST /api/auth/login
  - On success, the server issues an httpOnly session cookie that lasts 7d

For multi-user / Google-OAuth deployments later, drop a new dependency at
`get_current_user` — the cookie + session_token schema below is generic.
"""
from fastapi import APIRouter, HTTPException, Request, Response, Depends, Header
from pydantic import BaseModel
from datetime import datetime, timezone, timedelta
from typing import Optional
import hmac
import os
import uuid

router = APIRouter()

SESSION_TTL_DAYS = 7
COOKIE_NAME = "session_token"


class User(BaseModel):
    user_id: str
    email: str
    name: str
    picture: Optional[str] = None


class LoginBody(BaseModel):
    operator_token: str
    name: Optional[str] = None  # display name (optional)


async def get_db():
    from server import db
    return db


def _operator_email() -> Optional[str]:
    return (os.environ.get("OPERATOR_EMAIL") or "").strip().lower() or None


def _operator_token() -> Optional[str]:
    return (os.environ.get("OPERATOR_TOKEN") or "").strip() or None


async def _resolve_session_token(
    token_from_cookie: Optional[str], authorization: Optional[str]
) -> Optional[str]:
    if token_from_cookie:
        return token_from_cookie
    if authorization and authorization.lower().startswith("bearer "):
        return authorization.split(" ", 1)[1].strip()
    return None


async def get_current_user(
    request: Request,
    authorization: Optional[str] = Header(None),
    db=Depends(get_db),
) -> User:
    """Auth dependency - reads session_token from cookie or Bearer header."""
    token = await _resolve_session_token(request.cookies.get(COOKIE_NAME), authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    session = await db.user_sessions.find_one({"session_token": token}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=401, detail="Session not found")

    expires_at = session["expires_at"]
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Session expired")

    user_doc = await db.users.find_one({"user_id": session["user_id"]}, {"_id": 0})
    if not user_doc:
        raise HTTPException(status_code=401, detail="User not found")
    return User(**{k: user_doc.get(k) for k in ("user_id", "email", "name", "picture")})


@router.post("/login")
async def login(body: LoginBody, response: Response, db=Depends(get_db)):
    """Exchange a valid OPERATOR_TOKEN for a session cookie."""
    expected = _operator_token()
    if not expected:
        raise HTTPException(
            status_code=503,
            detail=(
                "OPERATOR_TOKEN is not configured on the server. Set it in "
                "the backend .env and restart."
            ),
        )

    # Constant-time compare to defeat timing oracles
    if not hmac.compare_digest(body.operator_token.strip(), expected):
        raise HTTPException(status_code=401, detail="Invalid operator token")

    email = _operator_email() or "operator@localhost"

    existing = await db.users.find_one({"email": email}, {"_id": 0})
    if existing:
        user_id = existing["user_id"]
        await db.users.update_one(
            {"user_id": user_id},
            {"$set": {"name": body.name or existing.get("name") or "Operator",
                      "updated_at": datetime.now(timezone.utc).isoformat()}},
        )
    else:
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        await db.users.insert_one({
            "user_id": user_id,
            "email": email,
            "name": body.name or "Operator",
            "picture": None,
            "created_at": datetime.now(timezone.utc),
        })

    session_token = f"st_{uuid.uuid4().hex}"
    expires_at = datetime.now(timezone.utc) + timedelta(days=SESSION_TTL_DAYS)
    # One active session per operator (kicks out any other open tabs)
    await db.user_sessions.delete_many({"user_id": user_id})
    await db.user_sessions.insert_one({
        "user_id": user_id,
        "session_token": session_token,
        "expires_at": expires_at,
        "created_at": datetime.now(timezone.utc),
    })

    response.set_cookie(
        key=COOKIE_NAME, value=session_token, httponly=True,
        secure=True, samesite="none", path="/",
        max_age=SESSION_TTL_DAYS * 86400,
    )
    return {"user_id": user_id, "email": email, "name": body.name or "Operator"}


@router.get("/me", response_model=User)
async def whoami(user: User = Depends(get_current_user)):
    return user


@router.post("/logout")
async def logout(request: Request, response: Response, authorization: Optional[str] = Header(None), db=Depends(get_db)):
    token = await _resolve_session_token(request.cookies.get(COOKIE_NAME), authorization)
    if token:
        await db.user_sessions.delete_one({"session_token": token})
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"logged_out": True}


@router.get("/config")
async def config():
    """Frontend reads this to know which login flow to render + who the operator is."""
    op_email = _operator_email()
    op_token_set = bool(_operator_token())
    return {
        "required": bool(op_email or op_token_set),
        "operator_email_hint": (op_email[:2] + "***@" + op_email.split("@")[-1]) if op_email else None,
        "auth_mode": "operator_token",  # locked to this for now; future: 'google_oauth' | 'saml'
        "operator_token_required": op_token_set,
    }
