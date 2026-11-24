import json
from datetime import datetime, timezone

import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error

from src.shared.auth import get_current_user
from src.shared.db import get_conn

router = APIRouter(prefix="/api/study", tags=["study"])


def _train_gpa_model() -> tuple[LinearRegression, float]:
    """Train on synthetic ADU grading data (no gender/nationality features per NFR12)."""
    rng = np.random.default_rng(42)
    n = 150
    coursework = rng.uniform(50.0, 98.0, n)
    attendance = rng.uniform(65.0, 100.0, n)
    credits = rng.choice([3, 4], n)

    # ADU 4.0 scale relationship + small realistic noise
    raw_score = 0.80 * coursework + 0.20 * attendance
    gpa_points = np.clip((raw_score - 50.0) / 12.5, 0.0, 4.0) + rng.normal(0.0, 0.12, n)
    gpa_points = np.clip(gpa_points, 0.0, 4.0)

    X = np.column_stack([coursework, attendance, credits])
    X_train, X_test = X[:120], X[120:]
    y_train, y_test = gpa_points[:120], gpa_points[120:]

    model = LinearRegression().fit(X_train, y_train)
    mae = float(mean_absolute_error(y_test, model.predict(X_test)))
    return model, round(mae, 3)


GPA_MODEL, MODEL_TEST_MAE = _train_gpa_model()


def needed_letter_grade(predicted_pts: float, target_gpa: float) -> str:
    gap = target_gpa - predicted_pts
    if gap <= 0.1:
        return "B"
    if gap <= 0.4:
        return "B+"
    if gap <= 0.8:
        return "A-"
    return "A"


def compute_student_gpa(student_id: int, target_gpa: float | None = None) -> dict:
    conn = get_conn()
    rows = conn.execute(
        "SELECT e.section_id, c.course_code, c.credits, e.coursework_avg, e.total_sessions, e.absences "
        "FROM enrollments e JOIN courses_sections c ON e.section_id = c.section_id "
        "WHERE e.student_id = ?",
        (student_id,),
    ).fetchall()
    saved_target = conn.execute(
        "SELECT personal_target FROM gpa_predictions WHERE student_id = ? ORDER BY pred_id DESC LIMIT 1",
        (student_id,),
    ).fetchone()
    user_row = conn.execute("SELECT cgpa FROM users WHERE user_id = ?", (student_id,)).fetchone()
    conn.close()

    current_cgpa = round(float(user_row["cgpa"]), 2) if user_row and user_row["cgpa"] is not None else 2.35
    target = target_gpa if target_gpa is not None else (saved_target["personal_target"] if saved_target else 3.0)
    if not rows:
        return {
            "student_id": student_id,
            "current_cgpa": current_cgpa,
            "predicted_gpa": 2.5,
            "personal_target": target,
            "model_mae": MODEL_TEST_MAE,
            "warn_probation": False,
            "warn_target": False,
            "courses": [],
            "reasons": ["No active enrollments found; using baseline."],
        }

    total_pts = 0.0
    total_cr = 0
    course_guidance = []
    reasons = []
    for r in rows:
        att_pct = max(0.0, 100.0 - (r["absences"] / max(r["total_sessions"], 1)) * 100.0)
        pred_pts = float(np.clip(GPA_MODEL.predict([[r["coursework_avg"], att_pct, r["credits"]]])[0], 0.0, 4.0))
        total_pts += pred_pts * r["credits"]
        total_cr += r["credits"]
        req_grade = needed_letter_grade(pred_pts, target)
        course_guidance.append(
            {
                "course_code": r["course_code"],
                "coursework_avg": r["coursework_avg"],
                "attendance_pct": round(att_pct, 1),
                "predicted_points": round(pred_pts, 2),
                "required_grade": req_grade,
            }
        )
        if att_pct < 85.0:
            reasons.append(f"{r['course_code']} attendance is {att_pct:.0f}% (pulling prediction down).")
        if r["coursework_avg"] < 75.0:
            reasons.append(f"{r['course_code']} coursework average is {r['coursework_avg']:.0f}%.")

    predicted_gpa = round(total_pts / max(total_cr, 1), 2)
    warn_probation = predicted_gpa < 2.0
    warn_target = predicted_gpa < target
    if not reasons:
        reasons.append("Coursework and attendance are currently on steady pace.")

    return {
        "student_id": student_id,
        "current_cgpa": current_cgpa,
        "predicted_gpa": predicted_gpa,
        "personal_target": round(target, 2),
        "model_mae": MODEL_TEST_MAE,
        "warn_probation": warn_probation,
        "warn_target": warn_target,
        "courses": course_guidance,
        "reasons": reasons,
    }


@router.get("/gpa")
def get_gpa_prediction(target: float | None = None, user: dict = Depends(get_current_user)):
    return compute_student_gpa(user["sub"], target_gpa=target)


class TargetRequest(BaseModel):
    target_gpa: float


@router.post("/gpa/target")
def set_gpa_target(req: TargetRequest, user: dict = Depends(get_current_user)):
    if not (2.0 <= req.target_gpa <= 4.0):
        raise HTTPException(status_code=400, detail="Personal GPA target must be between 2.0 and 4.0")
    res = compute_student_gpa(user["sub"], target_gpa=req.target_gpa)
    conn = get_conn()
    now_iso = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO gpa_predictions (student_id, predicted_gpa, personal_target, reasons_json, warned_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (user["sub"], res["predicted_gpa"], req.target_gpa, json.dumps(res["reasons"]), now_iso),
    )
    conn.commit()
    conn.close()
    return res
