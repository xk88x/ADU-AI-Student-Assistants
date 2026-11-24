import json
import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from src.shared.auth import get_current_user, require_role
from src.shared.db import REPO_ROOT, get_conn

router = APIRouter(prefix="/api/study", tags=["study"])

STORAGE_DIR = os.path.join(REPO_ROOT, "storage")
TMP_AUDIO_DIR = os.path.join(STORAGE_DIR, "tmp_audio")
PDF_DIR = os.path.join(STORAGE_DIR, "pdfs")


def _generate_pdf(pdf_path: str, section_id: str, lecture_date: str, summary_text: str, exam_focus: list[dict]) -> None:
    os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
    c = canvas.Canvas(pdf_path, pagesize=letter)
    y = 740
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, f"ADU Lecture Summary: {section_id} ({lecture_date})")
    y -= 28
    c.setFont("Helvetica", 11)
    for line in summary_text.splitlines():
        c.drawString(50, y, line[:90])
        y -= 18
    y -= 12
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Exam Focus Points (with Timestamps):")
    y -= 22
    c.setFont("Helvetica", 10.5)
    for item in exam_focus:
        c.drawString(60, y, f"[{item['timestamp']}] {item['topic']}")
        y -= 18
    c.save()


@router.post("/upload")
async def upload_lecture_recording(
    section_id: str = Form(...),
    lecture_date: str = Form("2026-11-24"),
    notes_hint: str = Form(""),
    audio: Optional[UploadFile] = File(default=None),
    user: dict = Depends(require_role("instructor")),
):
    os.makedirs(TMP_AUDIO_DIR, exist_ok=True)
    tmp_audio_path = os.path.join(TMP_AUDIO_DIR, f"{section_id}_{lecture_date}.mp3")

    if audio is not None:
        ext = os.path.splitext(audio.filename or "")[1].lower()
        if ext and ext not in (".mp3", ".wav", ".m4a", ".ogg"):
            raise HTTPException(status_code=400, detail="Unsupported audio format. Use MP3, WAV, M4A, or OGG.")
        data = await audio.read()
        with open(tmp_audio_path, "wb") as f:
            f.write(data)
    else:
        with open(tmp_audio_path, "wb") as f:
            f.write(b"SIMULATED_AUDIO_STREAM")

    # Background transcription simulation + immediate raw audio deletion (NFR11)
    transcribed_at = datetime.now(timezone.utc).isoformat()
    if os.path.exists(tmp_audio_path):
        os.remove(tmp_audio_path)
    audio_deleted_at = datetime.now(timezone.utc).isoformat()

    exam_focus = [
        {"timestamp": "14:22", "topic": "Sequence vs. Communication diagrams (Midterm Q3)"},
        {"timestamp": "38:10", "topic": "Non-functional requirement measurability criteria"},
    ]
    summary_text = (
        f"Summary generated locally for {section_id}.\n"
        f"Key topics: UML behavioral modeling, traceability, and NFR testing.\n"
        + (f"Instructor note: {notes_hint}" if notes_hint else "")
    )

    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO lecture_summaries (section_id, lecture_date, pdf_path, exam_focus_json, approved, transcribed_at, audio_deleted_at) "
        "VALUES (?, ?, '', ?, 0, ?, ?)",
        (section_id, lecture_date, json.dumps(exam_focus), transcribed_at, audio_deleted_at),
    )
    summary_id = cur.lastrowid
    pdf_path = os.path.join(PDF_DIR, f"summary_{summary_id}_{section_id}.pdf")
    _generate_pdf(pdf_path, section_id, lecture_date, summary_text, exam_focus)
    conn.execute("UPDATE lecture_summaries SET pdf_path = ? WHERE summary_id = ?", (pdf_path, summary_id))
    conn.commit()
    conn.close()

    return {
        "summary_id": summary_id,
        "section_id": section_id,
        "approved": False,
        "audio_deleted": not os.path.exists(tmp_audio_path),
        "transcribed_at": transcribed_at,
        "audio_deleted_at": audio_deleted_at,
        "exam_focus": exam_focus,
    }


@router.post("/approve/{summary_id}")
def approve_summary(summary_id: int, withdraw: bool = False, user: dict = Depends(require_role("instructor"))):
    conn = get_conn()
    row = conn.execute("SELECT * FROM lecture_summaries WHERE summary_id = ?", (summary_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Summary not found")
    if withdraw:
        if row["pdf_path"] and os.path.exists(row["pdf_path"]):
            os.remove(row["pdf_path"])
        conn.execute("DELETE FROM lecture_summaries WHERE summary_id = ?", (summary_id,))
        conn.commit()
        conn.close()
        return {"summary_id": summary_id, "withdrawn": True}
    conn.execute("UPDATE lecture_summaries SET approved = 1 WHERE summary_id = ?", (summary_id,))
    conn.commit()
    conn.close()
    return {"summary_id": summary_id, "approved": True}


@router.get("/summaries")
def list_summaries(user: dict = Depends(get_current_user)):
    conn = get_conn()
    if user["role"] == "instructor":
        rows = conn.execute("SELECT * FROM lecture_summaries ORDER BY summary_id DESC").fetchall()
    else:
        rows = conn.execute(
            "SELECT ls.* FROM lecture_summaries ls "
            "JOIN enrollments e ON ls.section_id = e.section_id "
            "WHERE e.student_id = ? AND ls.approved = 1 ORDER BY ls.summary_id DESC",
            (user["sub"],),
        ).fetchall()
    conn.close()
    return {
        "summaries": [
            {
                "summary_id": r["summary_id"],
                "section_id": r["section_id"],
                "lecture_date": r["lecture_date"],
                "approved": bool(r["approved"]),
                "exam_focus": json.loads(r["exam_focus_json"]),
            }
            for r in rows
        ]
    }


@router.get("/summary/{summary_id}/pdf")
def download_summary_pdf(summary_id: int, user: dict = Depends(get_current_user)):
    conn = get_conn()
    row = conn.execute("SELECT * FROM lecture_summaries WHERE summary_id = ?", (summary_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Summary not found")

    if user["role"] == "student":
        enrolled = conn.execute(
            "SELECT 1 FROM enrollments WHERE student_id = ? AND section_id = ?",
            (user["sub"], row["section_id"]),
        ).fetchone()
        if not enrolled or not row["approved"]:
            conn.close()
            raise HTTPException(status_code=403, detail="Access denied: not enrolled in this section or draft not approved")

    conn.close()
    if not row["pdf_path"] or not os.path.exists(row["pdf_path"]):
        raise HTTPException(status_code=404, detail="PDF file missing")
    return FileResponse(row["pdf_path"], media_type="application/pdf", filename=os.path.basename(row["pdf_path"]))
