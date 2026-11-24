import os
import sqlite3
import tempfile
import time

import pytest
from fastapi.testclient import TestClient

# Use an isolated temp SQLite database and deterministic local RAG for tests
_tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp_db.close()
os.environ["DB_PATH"] = _tmp_db.name
os.environ["AI_PROVIDER"] = "local"

from main import app  # noqa: E402
from src.attendance.checkin import ACTIVE_QR_TOKENS  # noqa: E402
from src.attendance.roster import absence_status  # noqa: E402
from src.shared.db import init_db  # noqa: E402
from src.study_assistant.gpa_model import MODEL_TEST_MAE  # noqa: E402

init_db()
client = TestClient(app)


def _login(email: str) -> dict:
    r = client.post("/api/auth/login", json={"email": email, "password": "adu12345"})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_tc_1_1_advising_probation_citation():
    hdrs = _login("1084512@students.adu.ac.ae")
    r = client.post("/api/advisor/ask", json={"question": "What is the credit limit on probation?"}, headers=hdrs)
    assert r.status_code == 200
    data = r.json()
    assert "12" in data["answer"]
    assert "p. 53" in data["citation"]


def test_advising_arabic_reply():
    hdrs = _login("1084512@students.adu.ac.ae")
    r = client.post("/api/advisor/ask", json={"question": "ما هو حد الساعات عند الإنذار؟", "lang": "ar"}, headers=hdrs)
    assert r.status_code == 200
    data = r.json()
    assert "12" in data["answer"]
    assert "دليل الطالب" in data["citation"]


def test_advising_arabic_autodetect_even_with_en_ui():
    hdrs = _login("1084512@students.adu.ac.ae")
    r = client.post("/api/advisor/ask", json={"question": "ما هو حد الساعات عند الإنذار؟", "lang": "en"}, headers=hdrs)
    assert r.status_code == 200
    data = r.json()
    assert any("\u0600" <= ch <= "\u06ff" for ch in data["answer"])
    assert "دليل الطالب" in data["citation"]


def test_tc_1_2_advising_waiver_referral():
    hdrs = _login("1084512@students.adu.ac.ae")
    r = client.post("/api/advisor/ask", json={"question": "Can I waive a capstone prerequisite?"}, headers=hdrs)
    assert r.status_code == 200
    assert r.json()["needs_referral"] is True


def test_tc_1_4_clash_free_schedule_solver():
    hdrs = _login("1084512@students.adu.ac.ae")
    t0 = time.perf_counter()
    r = client.post(
        "/api/advisor/schedule",
        json={"course_codes": ["SWE 401", "CSC 305", "ITT 320", "MGT 308"]},
        headers=hdrs,
    )
    elapsed = time.perf_counter() - t0
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert len(data["schedule"]) == 4
    assert elapsed < 5.0


def test_tc_1_5_probation_credit_cap_enforced():
    # Omar (1089234) has CGPA 1.85 -> 12-credit cap must block 15 credits
    hdrs = _login("1089234@students.adu.ac.ae")
    r = client.post(
        "/api/advisor/schedule",
        json={"course_codes": ["SWE 401", "CSC 305", "ITT 320", "MGT 308", "GEN 200"]},
        headers=hdrs,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is False
    assert data["max_credits"] == 12


def test_tc_2_2_geofence_checkin_and_zero_coords_in_db():
    hdrs = _login("1084512@students.adu.ac.ae")
    r = client.post(
        "/api/attendance/checkin/geo",
        json={"section_id": "SWE401-11", "lat": 24.3372, "lon": 54.6145},
        headers=hdrs,
    )
    assert r.status_code == 200
    assert r.json()["checked_in"] is True

    # Verify NFR11: attendance_records table has no latitude/longitude columns
    conn = sqlite3.connect(_tmp_db.name)
    cols = [row[1].lower() for row in conn.execute("PRAGMA table_info(attendance_records)").fetchall()]
    conn.close()
    assert "lat" not in cols and "lon" not in cols and "latitude" not in cols and "longitude" not in cols
    assert "inside_fence" in cols


def test_tc_2_4_qr_valid_and_expired_rejected():
    # Unauthenticated QR fetch must return 401
    assert client.get("/api/attendance/qr/SWE401-11").status_code == 401

    hdrs = _login("1084512@students.adu.ac.ae")
    # Student cannot rotate QR token (403)
    assert client.get("/api/attendance/qr/SWE401-11?rotate=true", headers=hdrs).status_code == 403

    # Authenticated student can fetch current QR token for check-in
    qr = client.get("/api/attendance/qr/SWE401-11", headers=hdrs).json()
    ok = client.post("/api/attendance/checkin/qr", json={"section_id": "SWE401-11", "token": qr["token"]}, headers=hdrs)
    assert ok.status_code == 200

    # Instructor can rotate QR token
    inst_hdrs = _login("bhutta@adu.ac.ae")
    rot = client.get("/api/attendance/qr/SWE401-11?rotate=true", headers=inst_hdrs)
    assert rot.status_code == 200
    assert "token" in rot.json()

    # Expire the token and confirm HTTP 400 (NFR9)
    ACTIVE_QR_TOKENS["SWE401-11"]["expires_at"] = time.time() - 5
    bad = client.post("/api/attendance/checkin/qr", json={"section_id": "SWE401-11", "token": rot.json()["token"]}, headers=hdrs)
    assert bad.status_code == 400


def test_tc_2_6_absence_thresholds():
    assert absence_status(2, 20) == (10.0, "WARNING 10%")
    assert absence_status(4, 20) == (20.0, "WARNING 20%")
    assert absence_status(6, 20) == (30.0, "WA (30%)")


def test_tc_3_2_and_tc_3_3_and_tc_4_1_summary_lifecycle_and_rbac():
    inst_hdrs = _login("bhutta@adu.ac.ae")
    up = client.post(
        "/api/study/upload",
        data={"section_id": "SWE401-11", "lecture_date": "2026-11-24"},
        files={"audio": ("lecture.mp3", b"FAKE_MP3_BYTES", "audio/mpeg")},
        headers=inst_hdrs,
    )
    assert up.status_code == 200
    up_data = up.json()
    assert up_data["audio_deleted"] is True  # NFR11
    sid = up_data["summary_id"]

    # Approve draft (UC-10)
    app_r = client.post(f"/api/study/approve/{sid}", headers=inst_hdrs)
    assert app_r.status_code == 200 and app_r.json()["approved"] is True

    # Enrolled student (1084512) can download PDF (TC-3.3)
    stu_hdrs = _login("1084512@students.adu.ac.ae")
    pdf_ok = client.get(f"/api/study/summary/{sid}/pdf", headers=stu_hdrs)
    assert pdf_ok.status_code == 200
    assert pdf_ok.headers["content-type"] == "application/pdf"

    # Non-enrolled student for CSC305-02 -> test TC-4.1 HTTP 403
    up2 = client.post(
        "/api/study/upload",
        data={"section_id": "CSC305-02", "lecture_date": "2026-11-24"},
        headers=inst_hdrs,
    )
    sid2 = up2.json()["summary_id"]
    client.post(f"/api/study/approve/{sid2}", headers=inst_hdrs)

    said_hdrs = _login("1089234@students.adu.ac.ae")  # Omar is NOT enrolled in CSC305-02
    forbidden = client.get(f"/api/study/summary/{sid2}/pdf", headers=said_hdrs)
    assert forbidden.status_code == 403


def test_tc_3_5_gpa_model_mae_and_prediction():
    assert MODEL_TEST_MAE <= 0.30  # NFR6
    hdrs = _login("1084512@students.adu.ac.ae")
    r = client.get("/api/study/gpa?target=3.0", headers=hdrs)
    assert r.status_code == 200
    data = r.json()
    assert 0.0 <= data["predicted_gpa"] <= 4.0
    assert len(data["courses"]) == 3


def test_frontend_and_openapi_served():
    assert client.get("/").status_code == 200
    assert client.get("/docs").status_code == 200


def test_advisor_endpoints_referrals_drafts_and_at_risk():
    stu_hdrs = _login("1084512@students.adu.ac.ae")
    adv_hdrs = _login("advisor@adu.ac.ae")

    # Student creates a referral
    ref_r = client.post("/api/advisor/refer", json={"question": "Need capstone prereq waiver"}, headers=stu_hdrs)
    assert ref_r.status_code == 200
    ref_id = ref_r.json()["referral_id"]

    # Advisor lists referrals joined with student name/email
    refs = client.get("/api/advisor/referrals", headers=adv_hdrs)
    assert refs.status_code == 200
    ref_list = refs.json()["referrals"]
    assert any(
        r["referral_id"] == ref_id
        and r["student_name"] == "Khalid Al-Mansoori"
        and r["student_email"] == "1084512@students.adu.ac.ae"
        for r in ref_list
    )

    # Student submits a schedule draft to advisor
    sched_r = client.post(
        "/api/advisor/schedule",
        json={"course_codes": ["SWE 401", "CSC 305"], "send_to_advisor": True},
        headers=stu_hdrs,
    )
    assert sched_r.status_code == 200
    draft_id = sched_r.json()["draft_id"]

    # Advisor lists drafts joined with student name/email
    drafts_r = client.get("/api/advisor/drafts", headers=adv_hdrs)
    assert drafts_r.status_code == 200
    assert any(
        d["draft_id"] == draft_id
        and d["student_name"] == "Khalid Al-Mansoori"
        and d["student_email"] == "1084512@students.adu.ac.ae"
        and d["advisor_status"] == "SUBMITTED"
        for d in drafts_r.json()["drafts"]
    )

    # Advisor reviews draft (APPROVED)
    rev_r = client.post(
        f"/api/advisor/drafts/{draft_id}/review",
        json={"status": "APPROVED", "comment": "Approved for Fall 2026"},
        headers=adv_hdrs,
    )
    assert rev_r.status_code == 200
    assert rev_r.json()["advisor_status"] == "APPROVED"
    assert rev_r.json()["comment"] == "Approved for Fall 2026"

    # Invalid review status -> 400; missing draft -> 404
    assert (
        client.post(
            f"/api/advisor/drafts/{draft_id}/review",
            json={"status": "INVALID", "comment": ""},
            headers=adv_hdrs,
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/api/advisor/drafts/999999/review",
            json={"status": "CHANGES_REQUESTED", "comment": "Fix"},
            headers=adv_hdrs,
        ).status_code
        == 404
    )

    # Advisor views at-risk students (Omar Al-Nuaimi has CGPA 1.85 < 2.0)
    risk_r = client.get("/api/advisor/at-risk", headers=adv_hdrs)
    assert risk_r.status_code == 200
    at_risk = risk_r.json()["at_risk"]
    assert any(s["student_id"] == 1089234 and s["cgpa"] < 2.0 and len(s["reasons"]) > 0 for s in at_risk)


def test_strict_rbac_403_across_roles():
    stu_hdrs = _login("1084512@students.adu.ac.ae")
    inst_hdrs = _login("bhutta@adu.ac.ae")
    adv_hdrs = _login("advisor@adu.ac.ae")

    # Student-only actions must return 403 for Instructor and Advisor
    for bad_hdrs in (inst_hdrs, adv_hdrs):
        assert client.post("/api/attendance/checkin/geo", json={"section_id": "SWE401-11", "lat": 24.3372, "lon": 54.6145}, headers=bad_hdrs).status_code == 403
        assert client.post("/api/attendance/checkin/qr", json={"section_id": "SWE401-11", "token": "ADU-0000"}, headers=bad_hdrs).status_code == 403
        assert client.post("/api/advisor/schedule", json={"course_codes": ["SWE 401"]}, headers=bad_hdrs).status_code == 403
        assert client.get("/api/advisor/eligible", headers=bad_hdrs).status_code == 403
        assert client.post("/api/advisor/refer", json={"question": "test"}, headers=bad_hdrs).status_code == 403

    # Instructor-only actions must return 403 for Student and Advisor
    for bad_hdrs in (stu_hdrs, adv_hdrs):
        assert client.get("/api/attendance/qr/SWE401-11?rotate=true", headers=bad_hdrs).status_code == 403
        assert client.post("/api/attendance/correct", json={"section_id": "SWE401-11", "student_id": 1084512, "status": "PRESENT"}, headers=bad_hdrs).status_code == 403
        assert client.post("/api/study/upload", data={"section_id": "SWE401-11", "lecture_date": "2026-11-24"}, headers=bad_hdrs).status_code == 403
        assert client.post("/api/study/approve/1", headers=bad_hdrs).status_code == 403

    # Advisor-only actions must return 403 for Student and Instructor
    for bad_hdrs in (stu_hdrs, inst_hdrs):
        assert client.get("/api/advisor/referrals", headers=bad_hdrs).status_code == 403
        assert client.get("/api/advisor/drafts", headers=bad_hdrs).status_code == 403
        assert client.post("/api/advisor/drafts/1/review", json={"status": "APPROVED", "comment": ""}, headers=bad_hdrs).status_code == 403
        assert client.get("/api/advisor/at-risk", headers=bad_hdrs).status_code == 403

    # Student-only my-drafts must return 403 for Instructor and Advisor
    for bad_hdrs in (inst_hdrs, adv_hdrs):
        assert client.get("/api/advisor/my-drafts", headers=bad_hdrs).status_code == 403


def test_enriched_seed_my_drafts_empty_citation_and_attendance_sync():
    stu_hdrs = _login("1084512@students.adu.ac.ae")
    inst_hdrs = _login("bhutta@adu.ac.ae")

    # current_cgpa returned consistently by F1 eligible and F3 gpa
    elig = client.get("/api/advisor/eligible", headers=stu_hdrs).json()
    gpa = client.get("/api/study/gpa", headers=stu_hdrs).json()
    assert elig["current_cgpa"] == 3.42
    assert gpa["current_cgpa"] == 3.42

    # Student my-drafts returns seeded and submitted drafts
    my_drafts = client.get("/api/advisor/my-drafts", headers=stu_hdrs)
    assert my_drafts.status_code == 200
    assert len(my_drafts.json()["drafts"]) >= 1

    # Unmatched personal query returns empty citation
    unmatched = client.post("/api/advisor/ask", json={"question": "Hello, how is my day looking?"}, headers=stu_hdrs)
    assert unmatched.status_code == 200
    assert unmatched.json()["citation"] == ""

    # Seeded pre-approved SWE401-11 summary PDF is downloadable immediately
    summaries = client.get("/api/study/summaries", headers=stu_hdrs).json()["summaries"]
    assert any(s["section_id"] == "SWE401-11" and s["approved"] is True for s in summaries)
    seed_id = next(s["summary_id"] for s in summaries if s["section_id"] == "SWE401-11")
    assert client.get(f"/api/study/summary/{seed_id}/pdf", headers=stu_hdrs).status_code == 200

    # Attendance correction updates enrollments.absences cleanly
    before_abs = next(
        c["absences"] for c in client.get("/api/attendance/summary/1084512", headers=stu_hdrs).json()["courses"]
        if c["section_id"] == "SWE401-11"
    )
    client.post(
        "/api/attendance/correct",
        json={"section_id": "SWE401-11", "student_id": 1084512, "status": "ABSENT", "session_id": "TEST-SESS-SYNC"},
        headers=inst_hdrs,
    )
    after_abs = next(
        c["absences"] for c in client.get("/api/attendance/summary/1084512", headers=stu_hdrs).json()["courses"]
        if c["section_id"] == "SWE401-11"
    )
    assert after_abs == before_abs + 1

    client.post(
        "/api/attendance/correct",
        json={"section_id": "SWE401-11", "student_id": 1084512, "status": "PRESENT", "session_id": "TEST-SESS-SYNC"},
        headers=inst_hdrs,
    )
    reverted_abs = next(
        c["absences"] for c in client.get("/api/attendance/summary/1084512", headers=stu_hdrs).json()["courses"]
        if c["section_id"] == "SWE401-11"
    )
    assert reverted_abs == before_abs
