import json
import os
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src.shared.auth import get_current_user, require_role
from src.shared.db import REPO_ROOT, get_conn
from src.study_assistant.gpa_model import compute_student_gpa

router = APIRouter(prefix="/api/advisor", tags=["advisor"])


def _load_dotenv() -> None:
    env_path = os.path.join(REPO_ROOT, ".env")
    if not os.path.isfile(env_path):
        return
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip().strip('"').strip("'")
            if k and k not in os.environ:
                os.environ[k] = v


_load_dotenv()

HANDBOOK_PASSAGES = [
    {
        "keywords": ["probation", "limit", "12", "credit", "cgpa", "2.0", "below", "إنذار", "انذار", "معدل", "ساعات"],
        "citation": "ADU Undergraduate Student Handbook, p. 53 [Academic Standing & Regulations]",
        "citation_ar": "دليل الطالب الجامعي لجامعة أبوظبي، ص 53 [الوضع الأكاديمي واللوائح]",
        "answer": (
            "Students placed on academic probation (CGPA below 2.0 after completing 30 credit hours) "
            "are restricted to a maximum course load of 12 credit hours per semester."
        ),
        "answer_ar": (
            "يُقيّد الطالب الموضوع تحت الإنذار الأكاديمي (معدل تراكمي أقل من 2.0 بعد إتمام 30 ساعة معتمدة) "
            "بحد أقصى قدره 12 ساعة معتمدة في الفصل الدراسي."
        ),
        "needs_referral": False,
    },
    {
        "keywords": ["waive", "waiver", "exception", "override", "capstone", "appeal", "إعفاء", "اعفاء", "استثناء", "تجاوز"],
        "citation": "ADU Academic Catalog, Section 4.2 [Prerequisite Waiver Regulations]",
        "citation_ar": "الكتالوج الأكاديمي لجامعة أبوظبي، القسم 4.2 [لوائح الإعفاء من المتطلبات السابقة]",
        "answer": (
            "Prerequisites cannot be waived automatically by the assistant. A waiver or policy exception "
            "requires department approval and must be reviewed by your Academic Advisor."
        ),
        "answer_ar": (
            "لا يمكن للمساعد إعفاء المتطلبات السابقة تلقائياً. أي طلب إعفاء أو استثناء يتطلب موافقة القسم "
            "ويجب مراجعته مباشرة من قِبل المرشد الأكاديمي."
        ),
        "needs_referral": True,
    },
    {
        "keywords": ["prereq", "prerequisite", "eligible", "register", "متطلب", "تسجيل", "جدول"],
        "citation": "ADU Undergraduate Student Handbook, p. 51 [Course Prerequisites]",
        "citation_ar": "دليل الطالب الجامعي لجامعة أبوظبي، ص 51 [المتطلبات السابقة للمقررات]",
        "answer": (
            "Students must complete all listed prerequisite courses before registering for an upper-level course "
            "unless an official waiver is granted by the Academic Advisor."
        ),
        "answer_ar": (
            "يجب على الطالب إتمام جميع المتطلبات السابقة المحددة قبل التسجيل في أي مقرر متقدم "
            "ما لم يصدر إعفاء رسمي من المرشد الأكاديمي."
        ),
        "needs_referral": False,
    },
    {
        "keywords": ["absence", "wa", "attendance", "warning", "10%", "20%", "30%", "غياب", "حرمان", "حضور"],
        "citation": "ADU Undergraduate Student Handbook, p. 48 [Attendance & Course Withdrawal]",
        "citation_ar": "دليل الطالب الجامعي لجامعة أبوظبي، ص 48 [الحضور والانسحاب بسبب الغياب]",
        "answer": (
            "ADU issues absence warnings at 10% and 20% of class sessions. Reaching 30% total absence "
            "results in an automatic grade of WA (Withdrawn due to Absence)."
        ),
        "answer_ar": (
            "تصدر جامعة أبوظبي إنذارات غياب عند بلوغ 10% و20% من المحاضرات، وعند الوصول إلى 30% غياب "
            "يتم تسجيل تقدير WA (انسحاب بسبب الغياب) تلقائياً."
        ),
        "needs_referral": False,
    },
]


def retrieve_passage(question: str) -> dict:
    q = question.lower()
    best, best_score = None, 0
    for p in HANDBOOK_PASSAGES:
        score = sum(1 for kw in p["keywords"] if kw in q)
        if score > best_score:
            best, best_score = p, score
    if best and best_score > 0:
        return {**best, "matched": True}
    return {
        "matched": False,
        "citation": "",
        "citation_ar": "",
        "answer": (
            "No specific handbook rule matched your query directly. Please refer this question to your "
            "Academic Advisor for an official decision."
        ),
        "answer_ar": (
            "لم تتطابق قاعدة محددة في دليل الطالب مع سؤالك مباشرة. يرجى إحالة السؤال إلى المرشد الأكاديمي "
            "للحصول على قرار رسمي."
        ),
        "needs_referral": True,
    }


def _student_context(user_id: int) -> dict:
    conn = get_conn()
    student = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    advisor = conn.execute("SELECT full_name FROM users WHERE role = 'advisor' LIMIT 1").fetchone()
    enrollments = conn.execute(
        "SELECT e.section_id, c.course_code, c.title, c.schedule_slot, c.room_id, "
        "instr.full_name AS instructor_name, e.coursework_avg, e.absences, e.total_sessions "
        "FROM enrollments e "
        "JOIN courses_sections c ON e.section_id = c.section_id "
        "JOIN users instr ON c.instructor_id = instr.user_id "
        "WHERE e.student_id = ?",
        (user_id,),
    ).fetchall()
    draft = conn.execute(
        "SELECT draft_id, section_ids_json, total_credits, advisor_status, comment "
        "FROM schedule_drafts WHERE student_id = ? ORDER BY draft_id DESC LIMIT 1",
        (user_id,),
    ).fetchone()
    referrals = conn.execute(
        "SELECT referral_id, question, status, created_at "
        "FROM referrals WHERE student_id = ? AND status = 'OPEN' ORDER BY referral_id DESC",
        (user_id,),
    ).fetchall()
    summaries = conn.execute(
        "SELECT ls.summary_id, ls.section_id, ls.lecture_date "
        "FROM lecture_summaries ls "
        "JOIN enrollments e ON ls.section_id = e.section_id "
        "WHERE e.student_id = ? AND ls.approved = 1 ORDER BY ls.summary_id DESC",
        (user_id,),
    ).fetchall()
    conn.close()

    gpa_info = compute_student_gpa(user_id)
    sections = [
        {
            "course": r["course_code"],
            "title": r["title"],
            "section": r["section_id"],
            "slot": r["schedule_slot"],
            "room": r["room_id"],
            "instructor": r["instructor_name"],
            "absence_pct": round((r["absences"] / max(r["total_sessions"], 1)) * 100.0, 1),
            "coursework_avg": r["coursework_avg"],
        }
        for r in enrollments
    ]
    return {
        "student": dict(student) if student else {},
        "advisor_name": advisor["full_name"] if advisor else "Academic Advisor",
        "gpa_info": gpa_info,
        "sections": sections,
        "latest_draft": dict(draft) if draft else None,
        "open_referrals": [dict(r) for r in referrals],
        "approved_summaries": [dict(s) for s in summaries],
    }


def build_system_prompt(ctx: dict, passage: dict, lang: str) -> str:
    student = ctx["student"]
    gpa_info = ctx["gpa_info"]
    completed = json.loads(student.get("completed_courses_json") or "[]")
    lang_rule = (
        "The student wrote in Arabic: you MUST reply in clear, natural Arabic."
        if lang == "ar"
        else "The student wrote in English: you MUST reply in clear, concise English."
    )
    citation = (passage["citation_ar"] if lang == "ar" else passage["citation"]) if passage.get("matched") else ""
    passage_text = passage["answer_ar"] if lang == "ar" else passage["answer"]
    citation_rule = (
        f"3. State the exact handbook citation ({citation}) in your answer. Keep the reply direct (2-4 sentences), with no filler.\n\n"
        if citation
        else "3. Answer directly from the student's live record below in 2-4 concise sentences, with no filler.\n\n"
    )
    passage_block = f"MATCHED HANDBOOK PASSAGE ({citation}):\n{passage_text}" if citation else "MATCHED HANDBOOK PASSAGE: None (personal/live record query)"

    return (
        "You are the ADU AI Student Assistant (Smart Advising Bot) for Abu Dhabi University, Fall 2026.\n"
        f"{lang_rule}\n\n"
        "STRICT RULES:\n"
        "1. Answer ONLY from the ADU Undergraduate Handbook policies and the student's live record below.\n"
        "2. Do not invent university rules, deadlines, or waivers. If a request needs a prerequisite waiver or policy exception, "
        "tell the student to click 'Refer to Academic Advisor' (UC-02).\n"
        f"{citation_rule}"
        "ADU OFFICIAL POLICIES:\n"
        "- Academic Probation (Handbook p. 53): CGPA < 2.0 after 30 credit hours caps load at 12 credit hours/semester.\n"
        "- Attendance & WA (Handbook p. 48): Warnings at 10% and 20% absence; automatic WA at 30% absence.\n"
        "- Prerequisites (Handbook p. 51 & Catalog Sec 4.2): Must complete prerequisites before registering; waivers require Advisor approval.\n"
        "- Privacy (UAE Federal Decree-Law No. 45 of 2021): Attendance check-in discards GPS coordinates immediately and stores only inside_fence.\n\n"
        f"CURRENT STUDENT RECORD:\n"
        f"- Name: {student.get('full_name', 'Student')} | ID: {student.get('user_id', 'N/A')} | Role: {student.get('role', 'student')}\n"
        f"- Major: {student.get('major', 'B.Sc. Software Engineering')} | Year: {student.get('academic_year', 'Junior - Year 3')}\n"
        f"- Academic Advisor: {ctx['advisor_name']}\n"
        f"- Current CGPA: {student.get('cgpa', 'N/A')} | Completed Credits: {student.get('completed_credits', 0)}\n"
        f"- Completed Courses: {', '.join(completed) if completed else 'None'}\n"
        f"- Predicted Semester GPA (F3): {gpa_info.get('predicted_gpa', 'N/A')} (Target: {gpa_info.get('personal_target', 3.0)})\n"
        f"- Course GPA Guidance: {json.dumps(gpa_info.get('courses', []))}\n"
        f"- Enrolled Sections (with Instructor, Slot, Room, Absence %): {json.dumps(ctx['sections'])}\n"
        f"- Latest Schedule Draft: {json.dumps(ctx['latest_draft'])}\n"
        f"- Open Referrals: {json.dumps(ctx['open_referrals'])}\n"
        f"- Approved Lecture Summaries: {json.dumps(ctx['approved_summaries'])}\n\n"
        f"{passage_block}"
    )


def ask_ai_provider(question: str, passage: dict, user_id: int, lang: str = "en") -> tuple[str, str]:
    _load_dotenv()
    provider = (os.environ.get("AI_PROVIDER") or "local").strip().lower()
    api_key = (os.environ.get("AI_API_KEY") or "").strip()
    model = (os.environ.get("AI_MODEL") or "").strip()

    if provider in ("gemini", "openai") and not api_key:
        return (passage["answer_ar"] if lang == "ar" else passage["answer"]), "local-handbook-rag"

    ctx = _student_context(user_id)
    sys_prompt = build_system_prompt(ctx, passage, lang)

    try:
        if provider == "gemini" and api_key:
            candidates = []
            for m in [model or "gemini-3.5-flash-lite", "gemini-3.5-flash-lite", "gemini-3.8-flash"]:
                if m and m not in candidates:
                    candidates.append(m)
            for m in candidates:
                try:
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={api_key}"
                    r = httpx.post(
                        url,
                        json={"contents": [{"parts": [{"text": f"{sys_prompt}\n\nStudent Question: {question}"}]}]},
                        timeout=25.0,
                    )
                    r.raise_for_status()
                    text = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
                    return text, f"gemini:{m}"
                except Exception:
                    continue

        if provider == "openai" and api_key:
            m = model or "gpt-4o-mini"
            r = httpx.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": m,
                    "messages": [
                        {"role": "system", "content": sys_prompt},
                        {"role": "user", "content": question},
                    ],
                    "max_tokens": 260,
                },
                timeout=15.0,
            )
            r.raise_for_status()
            text = r.json()["choices"][0]["message"]["content"].strip()
            return text, f"openai:{m}"

        if provider == "ollama":
            m = model or "llama3.2"
            r = httpx.post(
                "http://127.0.0.1:11434/api/generate",
                json={"model": m, "prompt": f"{sys_prompt}\n\nStudent Question: {question}", "stream": False},
                timeout=15.0,
            )
            r.raise_for_status()
            text = r.json().get("response", "").strip()
            if text:
                return text, f"ollama:{m}"
    except Exception:
        pass

    return (passage["answer_ar"] if lang == "ar" else passage["answer"]), "local-handbook-rag"


class AskRequest(BaseModel):
    question: str
    lang: str = "en"


@router.post("/ask")
def ask_question(req: AskRequest, user: dict = Depends(get_current_user)):
    has_ar = any("\u0600" <= ch <= "\u06ff" for ch in req.question)
    has_en = any("a" <= ch.lower() <= "z" for ch in req.question)
    if has_ar:
        lang = "ar"
    elif has_en:
        lang = "en"
    else:
        lang = "ar" if (req.lang or "").lower().startswith("ar") else "en"
    passage = retrieve_passage(req.question)
    answer, provider_used = ask_ai_provider(req.question, passage, user_id=user["sub"], lang=lang)
    citation = (passage["citation_ar"] if lang == "ar" else passage["citation"]) if passage.get("matched") else ""
    return {
        "answer": answer,
        "citation": citation,
        "needs_referral": passage["needs_referral"],
        "provider": provider_used,
    }


class ReferRequest(BaseModel):
    question: str


@router.post("/refer")
def refer_to_advisor(req: ReferRequest, user: dict = Depends(require_role("student"))):
    conn = get_conn()
    now = datetime.now(timezone.utc).isoformat()
    cur = conn.execute(
        "INSERT INTO referrals (student_id, question, status, created_at) VALUES (?, ?, 'OPEN', ?)",
        (user["sub"], req.question.strip(), now),
    )
    conn.commit()
    ref_id = cur.lastrowid
    conn.close()
    return {"referral_id": ref_id, "status": "OPEN", "message": "Referral forwarded to Academic Advisor."}


@router.get("/referrals")
def list_referrals(user: dict = Depends(require_role("advisor"))):
    conn = get_conn()
    rows = conn.execute(
        "SELECT r.referral_id, r.student_id, u.full_name AS student_name, u.email AS student_email, "
        "r.question, r.status, r.created_at "
        "FROM referrals r JOIN users u ON r.student_id = u.user_id "
        "ORDER BY r.referral_id DESC"
    ).fetchall()
    conn.close()
    return {
        "referrals": [
            {
                "referral_id": r["referral_id"],
                "student_id": r["student_id"],
                "student_name": r["student_name"],
                "student_email": r["student_email"],
                "question": r["question"],
                "status": r["status"],
                "created_at": r["created_at"],
            }
            for r in rows
        ]
    }


@router.get("/at-risk")
def list_at_risk_students(user: dict = Depends(require_role("advisor"))):
    conn = get_conn()
    students = conn.execute(
        "SELECT user_id, full_name, email, cgpa, completed_credits "
        "FROM users WHERE role = 'student' ORDER BY cgpa ASC"
    ).fetchall()
    conn.close()

    at_risk = []
    for s in students:
        gpa_info = compute_student_gpa(s["user_id"])
        cgpa = float(s["cgpa"] or 0.0)
        pred_gpa = float(gpa_info["predicted_gpa"])
        if cgpa < 2.0 or pred_gpa < 2.0:
            reasons = []
            if cgpa < 2.0:
                reasons.append(f"Current CGPA is {cgpa:.2f} (below 2.0 probation threshold).")
            if pred_gpa < 2.0:
                reasons.append(f"Predicted semester GPA is {pred_gpa:.2f} (below 2.0).")
            for r in gpa_info.get("reasons", []):
                if r not in reasons:
                    reasons.append(r)
            at_risk.append(
                {
                    "student_id": s["user_id"],
                    "full_name": s["full_name"],
                    "email": s["email"],
                    "cgpa": cgpa,
                    "predicted_gpa": pred_gpa,
                    "completed_credits": s["completed_credits"],
                    "reasons": reasons,
                }
            )
    return {"at_risk": at_risk}
