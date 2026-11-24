import base64
import hashlib
import hmac
import json
import os
import time
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from src.shared.db import get_conn, verify_password

SECRET_KEY = os.environ.get("ADU_JWT_SECRET", "adu-swe401-local-secret-key").encode("utf-8")
SESSION_TTL_SECONDS = 3600  # NFR9: 60 minutes

router = APIRouter(prefix="/api/auth", tags=["auth"])


def create_token(user_id: int, role: str, email: str, ttl_seconds: int = SESSION_TTL_SECONDS) -> str:
    payload = {"sub": user_id, "role": role, "email": email, "exp": int(time.time()) + ttl_seconds}
    raw = base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8")
    sig = hmac.new(SECRET_KEY, raw.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{raw}.{sig}"


def decode_token(token: str) -> dict:
    try:
        raw, sig = token.split(".", 1)
        expected = hmac.new(SECRET_KEY, raw.encode("utf-8"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            raise ValueError("Bad signature")
        payload = json.loads(base64.urlsafe_b64decode(raw.encode("utf-8")).decode("utf-8"))
        if payload.get("exp", 0) < int(time.time()):
            raise HTTPException(status_code=401, detail="Session token expired")
        return payload
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid session token")


def get_current_user(authorization: Optional[str] = Header(default=None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required")
    return decode_token(authorization.split(" ", 1)[1].strip())


def require_role(*roles: str):
    def _checker(user: dict = Depends(get_current_user)) -> dict:
        if user.get("role") not in roles:
            raise HTTPException(status_code=403, detail=f"Role '{user.get('role')}' not authorized")
        return user
    return _checker


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/login")
def login(req: LoginRequest):
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE email = ?", (req.email.strip(),)).fetchone()
    conn.close()
    if not row or not verify_password(req.password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_token(row["user_id"], row["role"], row["email"])
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": SESSION_TTL_SECONDS,
        "user": {
            "user_id": row["user_id"],
            "email": row["email"],
            "full_name": row["full_name"],
            "role": row["role"],
            "cgpa": row["cgpa"],
        },
    }


@router.get("/me")
def me(user: dict = Depends(get_current_user)):
    return user
