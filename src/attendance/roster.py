import csv
import io
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from src.shared.auth import get_current_user, require_role
from src.shared.db import get_conn

router = APIRouter(prefix="/api/attendance", tags=["attendance"])


def absence_status(absences: int, total_sessions: int) -> tuple[float, str]:
    if total_sessions <= 0:
        return 0.0, "OK"
    pct = round((absences / total_sessions) * 100.0, 1)
    if pct >= 30.0:
        return pct, "WA (30%)"
    if pct >= 20.0:
        return pct, "WARNING 20%"
    if pct >= 10.0:
        return pct, "WARNING 10%"
    return pct, "OK"


@router.get("/summary/{student_id}")
def get_student_absence_summary(student_id: int, user: dict = Depends(get_current_user)):
    if user["role"] == "student" and user["sub"] != student_id:
        raise HTTPException(status_code=403, detail="Cannot view another student's attendance")
    conn = get_conn()
    rows = conn.execute(
        "SELECT e.section_id, c.course_code, c.title, e.total_sessions, e.absences "
        "FROM enrollments e JOIN courses_sections c ON e.section_id = c.section_id "
        "WHERE e.student_id = ?",
        (student_id,),
    ).fetchall()
    conn.close()
    items = []
    for r in rows:
        pct, flag = absence_status(r["absences"], r["total_sessions"])
        items.append(
            {
                "section_id": r["section_id"],
                "course_code": r["course_code"],
                "title": r["title"],
                "total_sessions": r["total_sessions"],
                "absences": r["absences"],
                "absence_pct": pct,
                "warning": flag,
            }
        )
    return {"student_id": student_id, "courses": items}


@router.get("/roster/{section_id}")
def get_section_roster(section_id: str, user: dict = Depends(require_role("instructor", "registrar", "advisor"))):
    conn = get_conn()
    rows = conn.execute(
        "SELECT u.user_id, u.full_name, e.absences, e.total_sessions, "
        "COALESCE((SELECT status FROM attendance_records ar WHERE ar.student_id = u.user_id AND ar.section_id = e.section_id ORDER BY ar.record_id DESC LIMIT 1), 'ABSENT') AS latest_status, "
        "COALESCE((SELECT method FROM attendance_records ar WHERE ar.student_id = u.user_id AND ar.section_id = e.section_id ORDER BY ar.record_id DESC LIMIT 1), 'NONE') AS latest_method "
        "FROM enrollments e JOIN users u ON e.student_id = u.user_id WHERE e.section_id = ?",
        (section_id,),
    ).fetchall()
    conn.close()
    roster = []
    for r in rows:
        pct, flag = absence_status(r["absences"], r["total_sessions"])
        roster.append(
            {
                "student_id": r["user_id"],
                "full_name": r["full_name"],
                "latest_status": r["latest_status"],
                "method": r["latest_method"],
                "absence_pct": pct,
                "warning": flag,
            }
        )
    return {"section_id": section_id, "roster": roster}


class CorrectRequest(BaseModel):
    section_id: str
    student_id: int
    status: str  # PRESENT or ABSENT
    session_id: str | None = None


@router.post("/correct")
def correct_attendance(req: CorrectRequest, user: dict = Depends(require_role("instructor"))):
    if req.status not in ("PRESENT", "ABSENT"):
        raise HTTPException(status_code=400, detail="Status must be PRESENT or ABSENT")
    conn = get_conn()
    sess_id = req.session_id or f"{req.section_id}-{datetime.now(timezone.utc).strftime('%Y%m%d')}"
    now_iso = datetime.now(timezone.utc).isoformat()
    prev = conn.execute(
        "SELECT status FROM attendance_records WHERE session_id = ? AND student_id = ?",
        (sess_id, req.student_id),
    ).fetchone()

    if req.status == "ABSENT" and (prev is None or prev["status"] == "PRESENT"):
        conn.execute(
            "UPDATE enrollments SET absences = absences + 1 WHERE student_id = ? AND section_id = ?",
            (req.student_id, req.section_id),
        )
    elif req.status == "PRESENT" and prev is not None and prev["status"] == "ABSENT":
        conn.execute(
            "UPDATE enrollments SET absences = MAX(0, absences - 1) WHERE student_id = ? AND section_id = ?",
            (req.student_id, req.section_id),
        )

    conn.execute(
        "INSERT INTO attendance_records (session_id, section_id, student_id, inside_fence, method, status, corrected_by, logged_at) "
        "VALUES (?, ?, ?, 0, 'MANUAL', ?, ?, ?) "
        "ON CONFLICT(session_id, student_id) DO UPDATE SET method='MANUAL', status=excluded.status, corrected_by=excluded.corrected_by, logged_at=excluded.logged_at",
        (sess_id, req.section_id, req.student_id, req.status, user["sub"], now_iso),
    )
    conn.commit()
    conn.close()
    return {"ok": True, "student_id": req.student_id, "status": req.status, "corrected_by": user["sub"]}


@router.get("/export")
def export_attendance_csv(user: dict = Depends(require_role("registrar", "instructor"))):
    conn = get_conn()
    rows = conn.execute(
        "SELECT record_id, session_id, section_id, student_id, inside_fence, method, status, corrected_by, logged_at "
        "FROM attendance_records ORDER BY record_id"
    ).fetchall()
    conn.close()
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["record_id", "session_id", "section_id", "student_id", "inside_fence", "method", "status", "corrected_by", "logged_at"])
    for r in rows:
        writer.writerow(list(r))
    return PlainTextResponse(buf.getvalue(), media_type="text/csv")
