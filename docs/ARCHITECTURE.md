# WorkSight — System Architecture & Privacy Design

## 1. Modular Repository Layout

```text
Worksight/
├── docker-compose.yml            # PostgreSQL 16 + FastAPI Backend + Next.js Frontend
├── backend/
│   ├── alembic/                  # Versioned SQL migrations (0001_initial_schema.py)
│   ├── app/
│   │   ├── core/                 # Config, SQLAlchemy engine, JWT/bcrypt/Fernet cryptography
│   │   ├── models/               # Normalized relational ORM schema (13 tables)
│   │   ├── schemas/              # Strictly credential-free Pydantic v2 contracts
│   │   ├── cctv/                 # Independent CCTV integration module (RTSP, ONVIF, health, simulator)
│   │   ├── ai_vision/            # Independent CV module (YOLOv8 person detector, ephemeral tracker, zones)
│   │   ├── services/             # Audit log, WebSocket hub, retention purger, Excel/PDF reports, seeder
│   │   └── api/                  # Strictly RBAC-guarded REST routers
│   └── tests/                    # Pytest unit & integration suite
└── frontend/
    └── src/
        ├── app/                  # Login + 10-module role-filtered enterprise portal
        ├── components/           # Shadcn-style UI primitives, Recharts analytics, self-service portal
        └── lib/                  # Typed API client, Auth context, WebSocket real-time provider
```

## 2. Role-Based Access Control (RBAC) Matrix

| Endpoint / Module | Super Admin | HR Admin | Dept Manager | Employee |
|---|:---:|:---:|:---:|:---:|
| Admin Dashboard Overview | All Depts | All Depts | Own Dept Only | `403 Forbidden` |
| Employee Self-Service Overview | Self | Self | Self | Self |
| Employee Directory & CRUD | Read/Write | Read/Write | Read Own Dept | `403 Forbidden` |
| Verified Attendance & Corrections | All + Review | All + Review | Own Dept + Review | Own Only + Submit |
| Leave Applications & Approval | All + Review | All + Review | Own Dept + Review | Own Only + Apply |
| CCTV Cameras & Live Video | If `can_view_cctv` | If `can_view_cctv` | `403 Forbidden` | `403 Forbidden` |
| AI Monitoring Events Review | All | All | Own Dept Only | `403 Forbidden` |
| Excel & PDF Reports | All Depts | All Depts | Own Dept Only | `403 Forbidden` |
| Retention Policy & Audit Logs | Read/Write | Read/Write | `403 Forbidden` | `403 Forbidden` |
| User CCTV Access Governance | Read/Write | `403 Forbidden` | `403 Forbidden` | `403 Forbidden` |
| Transparent Monitoring Policy | Read | Read | Read | Read + Consent |

## 3. Data Separation Guarantee

- **Verified Attendance (`attendance_records`)** is populated strictly by access-card taps, QR check-ins, web portal check-ins, or HR-approved attendance corrections (`record_category = "verified_attendance"`).
- **AI Vision Telemetry (`vision_events`)** is stored separately (`source_category = "ai_presence_telemetry"`) with anonymous ephemeral track IDs (`trk_0001`), zone counts, and automatic `expires_at` timestamps enforced by the retention service.
- No foreign key or inference pipeline connects `vision_events` to `employees`.
