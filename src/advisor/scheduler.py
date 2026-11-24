import json
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.shared.auth import require_role
from src.shared.db import get_conn
from src.study_assistant.gpa_model import compute_student_gpa

router = APIRouter(prefix="/api/advisor", tags=["advisor"])


def parse_slot(slot_str: str) -> tuple[set[str], int, int]:
    """Parse 'Mon/Wed 10:00-11:15' -> ({'Mon', 'Wed'}, 600, 675)."""
    days_part, time_part = slot_str.split(" ", 1)
    days = set(days_part.split("/"))
    start_s, end_s = time_part.split("-", 1)
    sh, sm = map(int, start_s.split(":"))
    eh, em = map(int, end_s.split(":"))
    return days, sh * 60 + sm, eh * 60 + em


def slots_clash(slot_a: str, slot_b: str) -> bool:
    da, sa, ea = parse_slot(slot_a)
    db, sb, eb = parse_slot(slot_b)
    if not (da & db):
        return False
    return sa < eb and sb < ea


@router.get("/eligible")
def get_eligible_courses(user: dict = Depends(require_role("student"))):
    conn = get_conn()
    student = conn.execute("SELECT * FROM users WHERE user_id = ?", (user["sub"],)).fetchone()
    sections = conn.execute("SELECT * FROM courses_sections").fetchall()
    conn.close()

    completed = set(json.loads(student["completed_courses_json"]))
    gpa_info = compute_student_gpa(user["sub"])
    probation = gpa_info["predicted_gpa"] < 2.0 or (student["cgpa"] < 2.0 and student["completed_credits"] >= 30)
    max_credits = 12 if probation else 18

    courses = {}
    for s in sections:
        code = s["course_code"]
        prereq = s["prereq_code"]
        eligible = (prereq is None) or (prereq in completed)
        if code not in courses:
            courses[code] = {
                "course_code": code,
                "title": s["title"],
                "credits": s["credits"],
                "prereq_code": prereq,
                "eligible": eligible,
                "sections": [],
            }
        courses[code]["sections"].append(
            {"section_id": s["section_id"], "schedule_slot": s["schedule_slot"], "room_id": s["room_id"]}
        )

    return {
        "current_cgpa": gpa_info["current_cgpa"],
        "predicted_gpa": gpa_info["predicted_gpa"],
        "probation_guard": probation,
        "max_credits": max_credits,
        "courses": list(courses.values()),
    }


class ScheduleRequest(BaseModel):
    course_codes: List[str]
    send_to_advisor: Optional[bool] = False


@router.post("/schedule")
def build_clash_free_schedule(req: ScheduleRequest, user: dict = Depends(require_role("student"))):
    conn = get_conn()
    student = conn.execute("SELECT * FROM users WHERE user_id = ?", (user["sub"],)).fetchone()
    rows = conn.execute("SELECT * FROM courses_sections").fetchall()
    conn.close()

    completed = set(json.loads(student["completed_courses_json"]))
    gpa_info = compute_student_gpa(user["sub"])
    probation = gpa_info["predicted_gpa"] < 2.0 or (student["cgpa"] < 2.0 and student["completed_credits"] >= 30)
    max_credits = 12 if probation else 18

    by_course: dict[str, list[dict]] = {}
    for r in rows:
        by_course.setdefault(r["course_code"], []).append(dict(r))

    selected = []
    total_credits = 0
    for code in req.course_codes:
        secs = by_course.get(code, [])
        if not secs:
            return {"ok": False, "error": f"Unknown course {code}"}
        prereq = secs[0]["prereq_code"]
        if prereq and prereq not in completed:
            return {"ok": False, "error": f"Prerequisite {prereq} not completed for {code}"}
        total_credits += secs[0]["credits"]
        selected.append((code, secs))

    if total_credits > max_credits:
        return {
            "ok": False,
            "probation_guard": probation,
            "max_credits": max_credits,
            "requested_credits": total_credits,
            "error": f"Selected {total_credits} credits exceeds the {max_credits}-credit limit.",
        }

    chosen: list[dict] = []

    def backtrack(idx: int) -> bool:
        if idx == len(selected):
            return True
        _, secs = selected[idx]
        for s in secs:
            if not any(slots_clash(s["schedule_slot"], c["schedule_slot"]) for c in chosen):
                chosen.append(s)
                if backtrack(idx + 1):
                    return True
                chosen.pop()
        return False

    if not backtrack(0):
        return {
            "ok": False,
            "clashing_courses": [c for c, _ in selected],
            "error": "No clash-free section combination exists for the selected courses.",
        }

    schedule_out = []
    for s in chosen:
        alts = [
            {"section_id": a["section_id"], "schedule_slot": a["schedule_slot"], "room_id": a["room_id"]}
            for a in by_course[s["course_code"]]
            if a["section_id"] != s["section_id"]
        ][:2]
        schedule_out.append(
            {
                "course_code": s["course_code"],
                "section_id": s["section_id"],
                "title": s["title"],
                "credits": s["credits"],
                "schedule_slot": s["schedule_slot"],
                "room_id": s["room_id"],
                "alternatives": alts,
            }
        )

    status = "SUBMITTED" if req.send_to_advisor else "DRAFT"
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO schedule_drafts (student_id, section_ids_json, total_credits, advisor_status) VALUES (?, ?, ?, ?)",
        (user["sub"], json.dumps([s["section_id"] for s in chosen]), total_credits, status),
    )
    conn.commit()
    draft_id = cur.lastrowid
    conn.close()

    return {
        "ok": True,
        "draft_id": draft_id,
        "advisor_status": status,
        "total_credits": total_credits,
        "max_credits": max_credits,
        "probation_guard": probation,
        "schedule": schedule_out,
    }


@router.get("/my-drafts")
def list_my_schedule_drafts(user: dict = Depends(require_role("student"))):
    conn = get_conn()
    rows = conn.execute(
        "SELECT draft_id, section_ids_json, total_credits, advisor_status, comment "
        "FROM schedule_drafts WHERE student_id = ? ORDER BY draft_id DESC",
        (user["sub"],),
    ).fetchall()
    conn.close()
    return {
        "drafts": [
            {
                "draft_id": r["draft_id"],
                "section_ids": json.loads(r["section_ids_json"]),
                "total_credits": r["total_credits"],
                "advisor_status": r["advisor_status"],
                "comment": r["comment"] or "",
            }
            for r in rows
        ]
    }


@router.get("/drafts")
def list_schedule_drafts(user: dict = Depends(require_role("advisor"))):
    conn = get_conn()
    rows = conn.execute(
        "SELECT sd.draft_id, sd.student_id, u.full_name AS student_name, u.email AS student_email, "
        "sd.section_ids_json, sd.total_credits, sd.advisor_status, sd.comment "
        "FROM schedule_drafts sd JOIN users u ON sd.student_id = u.user_id "
        "ORDER BY sd.draft_id DESC"
    ).fetchall()
    conn.close()
    return {
        "drafts": [
            {
                "draft_id": r["draft_id"],
                "student_id": r["student_id"],
                "student_name": r["student_name"],
                "student_email": r["student_email"],
                "section_ids": json.loads(r["section_ids_json"]),
                "total_credits": r["total_credits"],
                "advisor_status": r["advisor_status"],
                "comment": r["comment"] or "",
            }
            for r in rows
        ]
    }


class DraftReviewRequest(BaseModel):
    status: str  # APPROVED or CHANGES_REQUESTED
    comment: str = ""


@router.post("/drafts/{draft_id}/review")
def review_schedule_draft(draft_id: int, req: DraftReviewRequest, user: dict = Depends(require_role("advisor"))):
    if req.status not in ("APPROVED", "CHANGES_REQUESTED"):
        raise HTTPException(status_code=400, detail="Status must be APPROVED or CHANGES_REQUESTED")
    conn = get_conn()
    row = conn.execute("SELECT draft_id FROM schedule_drafts WHERE draft_id = ?", (draft_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Schedule draft not found")
    conn.execute(
        "UPDATE schedule_drafts SET advisor_status = ?, comment = ? WHERE draft_id = ?",
        (req.status, req.comment.strip(), draft_id),
    )
    conn.commit()
    conn.close()
    return {
        "ok": True,
        "draft_id": draft_id,
        "advisor_status": req.status,
        "comment": req.comment.strip(),
    }
