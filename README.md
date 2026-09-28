# ADU AI Student Assistant

**Smart Advising, Automatic Attendance and Study & GPA Support**

SWE 401: Software Engineering, Fall 2026, Abu Dhabi University
Instructor: Dr. Muhammad Nasir Mumtaz Bhutta

## Team Members

| Name | Student ID | GitHub | Leads | Project Manager |
|---|---|---|---|---|
| Ahmed Alameri | 1090726 | [xk88x](https://github.com/xk88x) | F1 Smart advising bot | Phase 5 |
| Said Taha | 1093667 | [saeed789987](https://github.com/saeed789987) | F2 Automatic attendance | Phases 1 and 4 |
| Rayyan Daqqa | 1097796 | [y0-x9](https://github.com/y0-x9) | F3 Study assistant and GPA support | Phases 2 and 3 |

## Problem Description

Students at ADU need an advisor meeting to register, and some pick courses that clash or lack a prerequisite. Attendance is taken by hand. The portal warns about absence at 10% and 20% but does not predict grades or help students review lectures.

## Key Features

The AI Student Assistant is a module inside the ADU student portal with three functions:

1. **Smart advising bot (F1):** answers registration questions from the student handbook and builds a clash-free next-semester schedule.
2. **Automatic attendance (F2):** marks students present from their location during the class time, with a rotating QR code as the fallback.
3. **Study assistant and GPA support (F3):** turns lecture recordings into PDF summaries with an exam-focus list, predicts the end-of-semester GPA and warns before it falls below 2.0 or a personal target.

## Technologies Used

React, Python (FastAPI), PostgreSQL, Browser Geolocation API, Whisper, Ollama (local LLM) with RAG, ChromaDB, scikit-learn, ReportLab, draw.io, pytest, Postman.

## Prerequisites

To be added in Phase 5.

## Installation

To be added in Phase 5.

## Configuration

To be added in Phase 5.

## How to Run

To be added in Phase 5.

## How to Test

To be added in Phase 5.

## Repository Layout

```
docs/    reports for each phase
src/     source code (advisor, attendance, study_assistant)
tests/   test cases
```

## Branches

- `main`: stable version
- `feature/advisor`, `feature/attendance`, `feature/study-assistant`: one branch per function, merged into `main` through a pull request reviewed by another member

## Project Status

- [x] Phase 1: Proposal (28 Sep 2026)
- [ ] Phase 2: Requirements engineering (25 Oct 2026)
- [ ] Phase 3: Analysis diagrams (8 Nov 2026)
- [ ] Phase 4: System design (15 Nov 2026)
- [ ] Phase 5: Implementation and testing (22 Nov 2026)
