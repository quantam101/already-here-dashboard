"""
Emergent-managed Google Auth - Operator-only gate.

Single-user mode: only the email in OPERATOR_EMAIL env can pass.
Anyone else who logs in with Google is rejected at the session-creation step.
"""
from fastapi import APIRouter, HTTPException, Request, Response, Depends, Header
from pydantic import BaseModel
from datetime import datetime, timezone, timedelta
from typing import Optional
import os
import uuid
import httpx

router = APIRouter()

SESSION_TTL_DAYS = 7
COOKIE_NAME = "session_token"
EMERGENT_SESSION_DATA_URL = "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data"


class User(BaseModel):
    user_id: str
    email: str
    name: str
    picture: Optional[str] = None


class SessionExchangeBody(BaseModel):
    session_id: str


async def get_db():
    from server import db
    return db


def _operator_email() -> Optional[str]:
    return (os.environ.get("OPERATOR_EMAIL") or "").strip().lower() or None


def _ensure_allowed(email: str) -> None:
    op = _operator_email()
    if not op:
        return  # no allowlist configured → first-logged-in user becomes the operator
    if email.lower() != op:
        raise HTTPException(status_code=403, detail=f"Not the operator. Configured: {op}")


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


@router.post("/session")
async def exchange_session(body: SessionExchangeBody, response: Response, db=Depends(get_db)):
    """Frontend calls this after Emergent OAuth lands user back with #session_id=..."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            r = await client.get(EMERGENT_SESSION_DATA_URL, headers={"X-Session-ID": body.session_id})
            r.raise_for_status()
        except Exception as e:
            raise HTTPException(status_code=401, detail=f"Emergent auth lookup failed: {e}") from e
        data = r.json()

    email = (data.get("email") or "").strip()
    if not email:
        raise HTTPException(status_code=400, detail="No email returned from Emergent")
    _ensure_allowed(email)

    # Upsert user
    existing = await db.users.find_one({"email": email}, {"_id": 0})
    if existing:
        user_id = existing["user_id"]
        await db.users.update_one(
            {"user_id": user_id},
            {"$set": {"name": data.get("name"), "picture": data.get("picture"),
                      "updated_at": datetime.now(timezone.utc).isoformat()}},
        )
    else:
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        await db.users.insert_one({
            "user_id": user_id,
            "email": email,
            "name": data.get("name", ""),
            "picture": data.get("picture"),
            "created_at": datetime.now(timezone.utc),
        })

    # Store session
    session_token = data.get("session_token") or f"st_{uuid.uuid4().hex}"
    expires_at = datetime.now(timezone.utc) + timedelta(days=SESSION_TTL_DAYS)
    await db.user_sessions.delete_many({"user_id": user_id})  # one active session per operator
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
    return {"user_id": user_id, "email": email, "name": data.get("name"), "picture": data.get("picture")}


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
    """Frontend reads this to know if auth is required + who the operator is."""
    op = _operator_email()
    return {"required": bool(op), "operator_email_hint": (op[:2] + "***@" + op.split("@")[-1]) if op else None}
