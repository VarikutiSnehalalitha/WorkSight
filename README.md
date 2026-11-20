# WorkSight — AI-Powered Employee Attendance & Workplace Intelligence Platform

**WorkSight** is a production-oriented, privacy-first enterprise web application that unifies **verified employee attendance** (access cards, QR check-in, HR-managed records) with **anonymous on-premise CCTV computer vision telemetry** (workspace occupancy, entry/exit flow, restricted-area alerts, crowd detection, extended vacancy, and camera health).

---

## Ethical AI & Privacy-First Guardrails

WorkSight is engineered around strict workplace privacy principles:

1. **Presence ≠ Productivity**: CCTV physical presence telemetry is strictly for facility occupancy, space planning, safety, and operational awareness. WorkSight never claims physical presence establishes employee productivity.
2. **Strict Separation of Attendance & Vision Telemetry**: Individual employee attendance is attributed exclusively through authorized verification mechanisms (access cards, QR check-in, web portal, or HR-approved adjustments). CCTV vision events remain anonymous (`trk_0001` short-lived ephemeral IDs).
3. **Prohibited Technologies Never Implemented**:
   - Zero facial recognition or biometric identification.
   - Zero emotion or sentiment recognition.
   - Zero covert or undisclosed monitoring.
   - Zero automated employee scoring or automated disciplinary decisions.
4. **Human-in-the-Loop Governance**: Every AI alert and notification is reviewable, confirmable, dismissible, or markable as a false positive by authorized personnel.
5. **Security by Default**:
   - RTSP URLs and camera credentials are encrypted at rest with **Fernet** (`AES-128-CBC + HMAC-SHA256`) and never serialized to frontend clients.
   - Live CCTV streams require explicit role authorization (`super_admin` or authorized `hr_admin` with `can_view_cctv=true`), short-lived signed stream tokens, and generate immutable **Access Audit Trail** entries.
   - Raw video storage is **disabled by default**; configurable retention policies automatically purge expired metadata and clips.
6. **Honest Development Simulation**: Simulated camera feeds and demo AI events carry an unmistakable **`SIMULATED DEV FEED — NOT LIVE CCTV`** banner in both video frames and UI badges.

---

## Architecture Overview

| Layer | Technology |
|---|---|
| **Frontend** | Next.js 15, React 19, TypeScript, Tailwind CSS v4, Shadcn-style UI primitives, Recharts, Lucide Icons |
| **Backend API** | Python, FastAPI, SQLAlchemy 2.0, Alembic Migrations, JWT + bcrypt Auth, WebSockets |
| **CCTV Module** | Independent `backend/app/cctv/` — OpenCV RTSP capture, ONVIF WS-Discovery LAN scanner, connection tester, reconnection backoff, clearly watermarked dev simulator |
| **AI Vision Module** | Independent `backend/app/ai_vision/` — YOLOv8 + PyTorch person-only detection (`COCO class 0`), short-lived ephemeral tracker, polygon zone analytics |
| **Database** | PostgreSQL 16 (with Alembic migrations; SQLite zero-config fallback for local dev without Docker) |
| **Reports** | Real formatted Excel (`.xlsx` via `openpyxl`) and PDF (`.pdf` via `reportlab`) |
| **Infrastructure** | Docker & Docker Compose (`postgres`, `backend`, `frontend`) |

---

## Four Role-Isolated Portals (Demo Accounts)

All demo accounts are seeded automatically on first launch with password **`WorkSight2026!`**:

| Portal Role | Email | Scope & Permissions |
|---|---|---|
| **Super Admin / Owner** | `owner@worksight.io` | Full platform, CCTV live streams & hardware setup, retention policies, user CCTV permissions, immutable audit trail |
| **HR Administrator** | `hr@worksight.io` | Employee directory, verified attendance & corrections approval, leave management, department reports (Excel/PDF), AI event review, authorized CCTV |
| **Department Manager** | `manager@worksight.io` | Strictly scoped to assigned department (**Engineering**); blocked from other departments, global settings, and unauthorized CCTV |
| **Employee** | `employee@worksight.io` | Self-service portal only: personal verified check-in/out, working hours, leave applications, correction requests, and workplace monitoring policy/consent |

---

## Quick Start

### Option 1: Docker Compose (Recommended — PostgreSQL 16 + FastAPI + Next.js)

```bash
cp .env.example .env
# Edit .env to set strong JWT_SECRET_KEY and CAMERA_ENCRYPTION_KEY
docker compose up --build
```

- **Frontend UI**: http://localhost:3000
- **Backend API & OpenAPI Docs**: http://localhost:8000/docs

To include full PyTorch + YOLOv8 + OpenCV dependencies inside the backend container:

```bash
INSTALL_AI_DEPS=true docker compose up --build
```

### Option 2: Local Development (Without Docker)

#### 1. Backend (FastAPI + SQLite/PostgreSQL)

```bash
cd backend
python -m venv .venv

# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
# Optional: install full OpenCV + YOLOv8 + PyTorch on-premise CV engine
# pip install -r requirements-ai.txt

# Run Alembic database migrations
alembic upgrade head

# Start FastAPI server (auto-seeds realistic demo data on first run)
uvicorn app.main:app --reload --port 8000
```

#### 2. Frontend (Next.js)

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000 and sign in with any of the four role demo portals.

---

## Running Unit & Integration Tests

```bash
# Backend RBAC, Attendance, Leave, Reports, CCTV Encryption & AI Vision Tests
cd backend
pytest tests -v

# Frontend TypeScript & Production Build Verification
cd frontend
npm run typecheck
npm run build
```

---

## Additional Documentation

- [System Architecture & Privacy Design](docs/ARCHITECTURE.md)
- [Hardware CCTV Integration (RTSP, ONVIF & Zones)](docs/CCTV_INTEGRATION.md)
