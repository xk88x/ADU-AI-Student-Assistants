import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from src.advisor.rag_bot import router as advisor_bot_router
from src.advisor.scheduler import router as advisor_sched_router
from src.attendance.checkin import router as attendance_checkin_router
from src.attendance.roster import router as attendance_roster_router
from src.shared.auth import router as auth_router
from src.shared.db import REPO_ROOT, init_db
from src.study_assistant.gpa_model import router as gpa_router
from src.study_assistant.summarizer import router as summarizer_router

init_db()

app = FastAPI(
    title="ADU AI Student Assistant API",
    description="Smart Advising (F1), Automatic Attendance (F2), and Study & GPA Support (F3)",
    version="1.0.0",
)

app.include_router(auth_router)
app.include_router(advisor_bot_router)
app.include_router(advisor_sched_router)
app.include_router(attendance_checkin_router)
app.include_router(attendance_roster_router)
app.include_router(gpa_router)
app.include_router(summarizer_router)


@app.get("/api/health")
def health():
    return {"status": "ok"}


public_dir = os.path.join(REPO_ROOT, "public")
if os.path.isdir(public_dir):
    app.mount("/", StaticFiles(directory=public_dir, html=True), name="public")
