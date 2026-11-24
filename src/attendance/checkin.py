import math
import secrets
import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.shared.auth import get_current_user, require_role
from src.shared.db import get_conn

router = APIRouter(prefix="/api/attendance", tags=["attendance"])

QR_TTL_SECONDS = 30  # NFR9: 30-second rotating QR token
ACTIVE_QR_TOKENS: dict[str, dict] = {}


def haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6_371_000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def current_session_id(section_id: str) -> str:
    return f"{section_id}-{datetime.now(timezone.utc).strftime('%Y%m%d')}"


def issue_qr_token(section_id: str) -> dict:
    now = time.time()
    existing = ACTIVE_QR_TOKENS.get(section_id)
    if existing and existing["expires_at"] > now + 1:
        return {
            "section_id": section_id,
            "token": existing["token"],
            "expires_in": int(existing["expires_at"] - now),
        }
    token = f"ADU-{secrets.token_hex(2).upper()}"
    ACTIVE_QR_TOKENS[section_id] = {"token": token, "expires_at": now + QR_TTL_SECONDS}
    return {"section_id": section_id, "token": token, "expires_in": QR_TTL_SECONDS}


class GeoCheckinRequest(BaseModel):
    section_id: str
    lat: float
    lon: float
    session_id: str | None = None


@router.post("/checkin/geo")
def checkin_by_location(req: GeoCheckinRequest, user: dict = Depends(require_role("student"))):
    conn = get_conn()
    enrolled = conn.execute(
        "SELECT 1 FROM enrollments WHERE student_id = ? AND section_id = ?",
        (user["sub"], req.section_id),
    ).fetchone()
    if not enrolled:
        conn.close()
        raise HTTPException(status_code=403, detail="Student not enrolled in this section")

    fence = conn.execute(
        "SELECT g.* FROM geofences g JOIN courses_sections c ON g.building_id = c.building_id WHERE c.section_id = ?",
        (req.section_id,),
    ).fetchone()
    if not fence:
        conn.close()
        raise HTTPException(status_code=404, detail="Geofence not configured for section")

    # Evaluate distance in RAM only; coordinates are never persisted (NFR11)
    distance_m = haversine_meters(req.lat, req.lon, fence["center_lat"], fence["center_lon"])
    inside = distance_m <= fence["radius_m"]

    if not inside:
        conn.close()
        return {
            "checked_in": False,
            "inside_fence": False,
            "distance_m": round(distance_m, 1),
            "offer_qr": True,
            "message": "Outside building geofence. Please use the rotating QR code fallback.",
        }

    sess_id = req.session_id or current_session_id(req.section_id)
    now_iso = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO attendance_records (session_id, section_id, student_id, inside_fence, method, status, logged_at) "
        "VALUES (?, ?, ?, 1, 'GEO', 'PRESENT', ?) "
        "ON CONFLICT(session_id, student_id) DO UPDATE SET inside_fence=1, method='GEO', status='PRESENT', logged_at=excluded.logged_at",
        (sess_id, req.section_id, user["sub"], now_iso),
    )
    conn.commit()
    conn.close()
    return {
        "checked_in": True,
        "inside_fence": True,
        "method": "GEO",
        "distance_m": round(distance_m, 1),
        "privacy": "Coordinates discarded immediately (UAE Law 45/2021).",
    }


@router.get("/qr/{section_id}")
def get_rotating_qr(section_id: str, rotate: bool = False, user: dict = Depends(get_current_user)):
    if rotate:
        if user.get("role") != "instructor":
            raise HTTPException(status_code=403, detail=f"Role '{user.get('role')}' not authorized to rotate QR token")
        ACTIVE_QR_TOKENS.pop(section_id, None)
    return issue_qr_token(section_id)


class QrCheckinRequest(BaseModel):
    section_id: str
    token: str
    session_id: str | None = None


@router.post("/checkin/qr")
def checkin_by_qr(req: QrCheckinRequest, user: dict = Depends(require_role("student"))):
    entry = ACTIVE_QR_TOKENS.get(req.section_id)
    now = time.time()
    if not entry or entry["expires_at"] < now or entry["token"] != req.token.strip().upper():
        raise HTTPException(status_code=400, detail="Invalid or expired QR token")

    conn = get_conn()
    enrolled = conn.execute(
        "SELECT 1 FROM enrollments WHERE student_id = ? AND section_id = ?",
        (user["sub"], req.section_id),
    ).fetchone()
    if not enrolled:
        conn.close()
        raise HTTPException(status_code=403, detail="Student not enrolled in this section")

    sess_id = req.session_id or current_session_id(req.section_id)
    now_iso = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO attendance_records (session_id, section_id, student_id, inside_fence, method, status, logged_at) "
        "VALUES (?, ?, ?, 0, 'QR', 'PRESENT', ?) "
        "ON CONFLICT(session_id, student_id) DO UPDATE SET method='QR', status='PRESENT', logged_at=excluded.logged_at",
        (sess_id, req.section_id, user["sub"], now_iso),
    )
    conn.commit()
    conn.close()
    return {"checked_in": True, "method": "QR", "token": req.token.strip().upper()}
