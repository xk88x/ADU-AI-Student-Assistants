import hashlib
import json
import os
import secrets
import sqlite3
from datetime import datetime, timezone

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_db_path() -> str:
    return os.environ.get("DB_PATH", os.path.join(REPO_ROOT, "adu_portal.db"))


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000)
    return f"{salt}${dk.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt, hex_dk = stored_hash.split("$", 1)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000)
        return secrets.compare_digest(dk.hex(), hex_dk)
    except ValueError:
        return False


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(get_db_path(), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    conn = get_conn()
    cur = conn.cursor()

    cur.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        full_name TEXT NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('student','advisor','instructor','registrar','it','mgmt')),
        preferred_lang TEXT NOT NULL DEFAULT 'en',
        major TEXT NOT NULL DEFAULT 'B.Sc. Software Engineering',
        academic_year TEXT NOT NULL DEFAULT 'Junior - Year 3',
        cgpa REAL DEFAULT 2.35,
        completed_credits INTEGER DEFAULT 60,
        completed_courses_json TEXT DEFAULT '[]',
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS geofences (
        building_id TEXT PRIMARY KEY,
        building_name TEXT NOT NULL,
        center_lat REAL NOT NULL,
        center_lon REAL NOT NULL,
        radius_m REAL NOT NULL CHECK(radius_m > 0)
    );

    CREATE TABLE IF NOT EXISTS courses_sections (
        section_id TEXT PRIMARY KEY,
        course_code TEXT NOT NULL,
        title TEXT NOT NULL,
        credits INTEGER NOT NULL CHECK(credits > 0),
        prereq_code TEXT,
        schedule_slot TEXT NOT NULL,
        room_id TEXT NOT NULL,
        building_id TEXT NOT NULL REFERENCES geofences(building_id),
        instructor_id INTEGER NOT NULL REFERENCES users(user_id)
    );

    CREATE TABLE IF NOT EXISTS enrollments (
        student_id INTEGER NOT NULL REFERENCES users(user_id),
        section_id TEXT NOT NULL REFERENCES courses_sections(section_id),
        coursework_avg REAL NOT NULL DEFAULT 78.0,
        total_sessions INTEGER NOT NULL DEFAULT 20,
        absences INTEGER NOT NULL DEFAULT 1,
        PRIMARY KEY (student_id, section_id)
    );

    -- NFR11: Zero GPS coordinates stored here; only boolean inside_fence
    CREATE TABLE IF NOT EXISTS attendance_records (
        record_id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        section_id TEXT NOT NULL REFERENCES courses_sections(section_id),
        student_id INTEGER NOT NULL REFERENCES users(user_id),
        inside_fence INTEGER NOT NULL CHECK(inside_fence IN (0, 1)),
        method TEXT NOT NULL CHECK(method IN ('GEO', 'QR', 'MANUAL')),
        status TEXT NOT NULL DEFAULT 'PRESENT' CHECK(status IN ('PRESENT', 'ABSENT')),
        corrected_by INTEGER REFERENCES users(user_id),
        logged_at TEXT NOT NULL,
        UNIQUE(session_id, student_id)
    );

    CREATE TABLE IF NOT EXISTS schedule_drafts (
        draft_id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL REFERENCES users(user_id),
        section_ids_json TEXT NOT NULL,
        total_credits INTEGER NOT NULL CHECK(total_credits <= 18),
        advisor_status TEXT NOT NULL DEFAULT 'DRAFT',
        comment TEXT DEFAULT ''
    );

    CREATE TABLE IF NOT EXISTS lecture_summaries (
        summary_id INTEGER PRIMARY KEY AUTOINCREMENT,
        section_id TEXT NOT NULL REFERENCES courses_sections(section_id),
        lecture_date TEXT NOT NULL,
        pdf_path TEXT NOT NULL,
        exam_focus_json TEXT NOT NULL,
        approved INTEGER NOT NULL DEFAULT 0 CHECK(approved IN (0, 1)),
        transcribed_at TEXT NOT NULL,
        audio_deleted_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS gpa_predictions (
        pred_id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL REFERENCES users(user_id),
        predicted_gpa REAL NOT NULL CHECK(predicted_gpa >= 0.0 AND predicted_gpa <= 4.0),
        personal_target REAL DEFAULT 3.0,
        reasons_json TEXT NOT NULL,
        warned_at TEXT
    );

    CREATE TABLE IF NOT EXISTS referrals (
        referral_id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL REFERENCES users(user_id),
        question TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'OPEN',
        created_at TEXT NOT NULL
    );
    """)

    # Handle schema migration cleanly for pre-existing DBs
    user_cols = {row[1] for row in cur.execute("PRAGMA table_info(users)").fetchall()}
    if "major" not in user_cols:
        cur.execute("ALTER TABLE users ADD COLUMN major TEXT NOT NULL DEFAULT 'B.Sc. Software Engineering'")
    if "academic_year" not in user_cols:
        cur.execute("ALTER TABLE users ADD COLUMN academic_year TEXT NOT NULL DEFAULT 'Junior - Year 3'")

    # Seed once if users table is empty
    if cur.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        now = datetime.now(timezone.utc).isoformat()
        pw = hash_password("adu12345")
        completed = json.dumps(["CSC 101", "CSC 201", "SWE 301", "MTH 201"])
        users = [
            (1084512, "1084512@students.adu.ac.ae", "Khalid Al-Mansoori", pw, "student", "en", "B.Sc. Software Engineering", "Junior - Year 3", 3.42, 66, completed, now),
            (1089234, "1089234@students.adu.ac.ae", "Omar Al-Nuaimi", pw, "student", "en", "B.Sc. Software Engineering", "Sophomore - Year 2", 1.85, 45, completed, now),
            (1085101, "1085101@students.adu.ac.ae", "Mariam Al-Dhaheri", pw, "student", "en", "B.Sc. Software Engineering", "Junior - Year 3", 3.68, 69, completed, now),
            (1085102, "1085102@students.adu.ac.ae", "Youssef Al-Ketbi", pw, "student", "en", "B.Sc. Software Engineering", "Junior - Year 3", 3.15, 63, completed, now),
            (1085103, "1085103@students.adu.ac.ae", "Noora Al-Mazrouei", pw, "student", "en", "B.Sc. Computer Science", "Junior - Year 3", 3.54, 66, completed, now),
            (1085104, "1085104@students.adu.ac.ae", "Rashid Al-Suwaidi", pw, "student", "en", "B.Sc. Software Engineering", "Senior - Year 4", 2.92, 90, completed, now),
            (1085105, "1085105@students.adu.ac.ae", "Sara Al-Kaabi", pw, "student", "en", "B.Sc. Software Engineering", "Junior - Year 3", 3.28, 66, completed, now),
            (1085106, "1085106@students.adu.ac.ae", "Hamdan Al-Zaabi", pw, "student", "en", "B.Sc. Software Engineering", "Sophomore - Year 2", 2.64, 48, completed, now),
            (2001, "bhutta@adu.ac.ae", "Dr. Muhammad Nasir Mumtaz Bhutta", pw, "instructor", "en", "College of Engineering", "Faculty", 4.0, 0, "[]", now),
            (3001, "advisor@adu.ac.ae", "Dr. Murad Al-Rajab", pw, "advisor", "en", "College of Engineering", "Faculty", 4.0, 0, "[]", now),
            (4001, "registrar@adu.ac.ae", "ADU Registrar", pw, "registrar", "en", "Registrar Office", "Staff", 4.0, 0, "[]", now),
        ]
        cur.executemany(
            "INSERT INTO users (user_id, email, full_name, password_hash, role, preferred_lang, major, academic_year, cgpa, completed_credits, completed_courses_json, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            users,
        )

        cur.execute(
            "INSERT INTO geofences (building_id, building_name, center_lat, center_lon, radius_m) VALUES (?, ?, ?, ?, ?)",
            ("BLDG-B", "Abu Dhabi University Building B", 24.3372, 54.6145, 250.0),
        )

        sections = [
            ("SWE401-11", "SWE 401", "Software Engineering", 3, "SWE 301", "Mon/Wed 10:00-11:15", "B-204", "BLDG-B", 2001),
            ("SWE401-12", "SWE 401", "Software Engineering", 3, "SWE 301", "Tue/Thu 10:00-11:15", "B-205", "BLDG-B", 2001),
            ("CSC305-01", "CSC 305", "Operating Systems", 3, "CSC 201", "Mon/Wed 10:00-11:15", "B-102", "BLDG-B", 2001),
            ("CSC305-02", "CSC 305", "Operating Systems", 3, "CSC 201", "Mon/Wed 13:00-14:15", "B-104", "BLDG-B", 2001),
            ("ITT320-03", "ITT 320", "Computer Networks", 3, "CSC 201", "Tue/Thu 11:30-12:45", "B-301", "BLDG-B", 2001),
            ("CSC410-01", "CSC 410", "Capstone Project I", 3, "SWE 401", "Mon/Wed 14:30-15:45", "B-210", "BLDG-B", 2001),
            ("MGT308-01", "MGT 308", "Engineering Ethics", 3, None, "Tue/Thu 13:00-14:15", "B-110", "BLDG-B", 2001),
            ("GEN200-01", "GEN 200", "Innovation & Entrepreneurship", 3, None, "Fri 09:00-11:30", "B-112", "BLDG-B", 2001),
        ]
        cur.executemany(
            "INSERT INTO courses_sections (section_id, course_code, title, credits, prereq_code, schedule_slot, room_id, building_id, instructor_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            sections,
        )

        # Khalid (1084512) enrolled in 3 courses; 7 additional students in SWE401-11 for Dr. Bhutta's roster
        enrollments = [
            (1084512, "SWE401-11", 89.0, 20, 1),
            (1084512, "CSC305-02", 86.0, 20, 1),
            (1084512, "ITT320-03", 85.0, 20, 2),
            (1089234, "SWE401-11", 65.0, 20, 4),
            (1085101, "SWE401-11", 92.0, 20, 0),
            (1085102, "SWE401-11", 84.0, 20, 1),
            (1085103, "SWE401-11", 88.0, 20, 2),
            (1085104, "SWE401-11", 79.0, 20, 3),
            (1085105, "SWE401-11", 86.0, 20, 4),
            (1085106, "SWE401-11", 73.0, 20, 6),
        ]
        cur.executemany(
            "INSERT INTO enrollments (student_id, section_id, coursework_avg, total_sessions, absences) VALUES (?, ?, ?, ?, ?)",
            enrollments,
        )

        cur.executemany(
            "INSERT INTO attendance_records (session_id, section_id, student_id, inside_fence, method, status, logged_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                ("SWE401-11-S01", "SWE401-11", 1084512, 1, "GEO", "PRESENT", now),
                ("SWE401-11-S01", "SWE401-11", 1089234, 0, "MANUAL", "ABSENT", now),
                ("SWE401-11-S01", "SWE401-11", 1085101, 1, "GEO", "PRESENT", now),
                ("SWE401-11-S01", "SWE401-11", 1085102, 0, "QR", "PRESENT", now),
                ("SWE401-11-S01", "SWE401-11", 1085103, 1, "GEO", "PRESENT", now),
                ("SWE401-11-S01", "SWE401-11", 1085104, 0, "QR", "PRESENT", now),
                ("SWE401-11-S01", "SWE401-11", 1085105, 0, "MANUAL", "ABSENT", now),
                ("SWE401-11-S01", "SWE401-11", 1085106, 0, "MANUAL", "ABSENT", now),
            ],
        )

        cur.executemany(
            "INSERT INTO schedule_drafts (student_id, section_ids_json, total_credits, advisor_status, comment) VALUES (?, ?, ?, ?, ?)",
            [
                (1084512, json.dumps(["SWE401-11", "CSC305-02", "ITT320-03", "MGT308-01"]), 12, "SUBMITTED", ""),
                (1089234, json.dumps(["SWE401-11", "MGT308-01"]), 6, "CHANGES_REQUESTED", "Please meet during advising hours to review probation plan."),
            ],
        )

        cur.execute(
            "INSERT INTO referrals (student_id, question, status, created_at) VALUES (?, ?, 'OPEN', ?)",
            (1084512, "Requesting prerequisite override review for CSC 410 Capstone Project I alongside SWE 401.", now),
        )

        seeded_focus = [
            {"timestamp": "11:15", "topic": "SRS Traceability Matrix & Stakeholder Needs"},
            {"timestamp": "29:40", "topic": "RBAC Security & Privacy-by-Design (NFR11)"},
        ]
        seeded_pdf_path = os.path.join(REPO_ROOT, "storage", "pdfs", "summary_seed_SWE401-11.pdf")
        cur.execute(
            "INSERT INTO lecture_summaries (section_id, lecture_date, pdf_path, exam_focus_json, approved, transcribed_at, audio_deleted_at) "
            "VALUES (?, ?, ?, ?, 1, ?, ?)",
            ("SWE401-11", "2026-11-20", seeded_pdf_path, json.dumps(seeded_focus), now, now),
        )

    # Ensure any seeded/existing approved summary PDF exists on disk
    for row in cur.execute("SELECT section_id, lecture_date, pdf_path, exam_focus_json FROM lecture_summaries WHERE pdf_path != ''").fetchall():
        if row["pdf_path"] and not os.path.exists(row["pdf_path"]):
            os.makedirs(os.path.dirname(row["pdf_path"]), exist_ok=True)
            c = canvas.Canvas(row["pdf_path"], pagesize=letter)
            y = 740
            c.setFont("Helvetica-Bold", 14)
            c.drawString(50, y, f"ADU Lecture Summary: {row['section_id']} ({row['lecture_date']})")
            y -= 28
            c.setFont("Helvetica", 11)
            c.drawString(50, y, "Key topics: Software requirements traceability, RBAC design, and NFR verification.")
            y -= 30
            c.setFont("Helvetica-Bold", 12)
            c.drawString(50, y, "Exam Focus Points (with Timestamps):")
            y -= 22
            c.setFont("Helvetica", 10.5)
            for item in json.loads(row["exam_focus_json"] or "[]"):
                c.drawString(60, y, f"[{item['timestamp']}] {item['topic']}")
                y -= 18
            c.save()

    conn.commit()
    conn.close()
