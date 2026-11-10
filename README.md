# Engagement Pulse

**A secure, multi-tenant engagement risk management application with asynchronous imports and live client updates.**

Engagement Pulse allows consultants to manage projects and risks across assigned client organisations while providing client stakeholders with a read-only, continuously updated dashboard of delivery health. Built around strict tenant isolation, non-blocking background imports, and instant real-time updates across multiple application instances.

---

## Features

- **Multi-Tenant Authorization:** Role-based access control with consultant organisation mapping (`ConsultantOrganisationAccess`) and single-tenant client viewers. Enforced in database queries and API dependencies, returning HTTP 404 for inaccessible resources and HTTP 403 for unauthorized actions.
- **Deterministic Risk Scoring:** Weighted risk scores calculated transactionally with database row-level locking (`SELECT ... FOR UPDATE`), cached on projects, and automatically refreshed on risk changes or CSV imports.
- **Asynchronous CSV Imports:** Non-blocking bulk risk uploads via Dramatiq and Redis, featuring SHA-256 fingerprint deduplication, dedicated worker queue isolation (`fastapi`), transactional record creation, and persisted job status tracking.
- **Real-Time Cross-Instance Updates:** Live change broadcasts powered by FastAPI WebSockets and Redis Pub/Sub. Connected dashboards invalidate React Query caches upon mutation events, updating metrics immediately without page reloads.
- **One-Command Startup:** Docker Compose orchestrates the entire application (Next.js frontend, FastAPI API, PostgreSQL 16, Redis 7, and Dramatiq worker) with automated container health checks, Alembic migrations, and demo data seeding.
- **Automated CI:** GitHub Actions workflow executes backend unit and API tests with PostgreSQL and Redis service containers, frontend Jest test suites, and Next.js production builds.

---

## Technology Stack

| Layer | Technology | Purpose |
| --- | --- | --- |
| **Frontend** | Next.js 14 (App Router), React 18, TypeScript | Layout routing, server-rendered views, and interactive client dashboards |
| | Material UI (MUI v6) | Responsive, accessible UI components and design system |
| | React Query (`@tanstack/react-query` v5) | Server state management, caching, background invalidation, and deduplication |
| **Backend (Active)** | Python 3.12, FastAPI, Pydantic v2 | High-performance ASGI REST API and WebSocket endpoints |
| | SQLAlchemy 2.0, Psycopg 3 (`postgresql+psycopg`) | Typed database models, transactions, and row-level locking |
| | Alembic | Relational database schema migrations |
| | Uvicorn | Asynchronous HTTP and WebSocket ASGI web server |
| **Database** | PostgreSQL 16 | Relational storage, unique constraints, and foreign key integrity |
| **Message Broker** | Redis 7 | Message broker for Dramatiq queues, Pub/Sub channels, and ticket store |
| **Background Tasks** | Dramatiq | Asynchronous CSV parsing, validation, and risk import on dedicated `fastapi` queue |
| **Real-Time** | FastAPI WebSockets, `redis.asyncio` | Cross-instance event distribution with single-use connection tickets |
| **Testing** | Pytest, TestClient | Backend unit, API, tenant isolation, and scoring tests (13 tests) |
| | Jest, React Testing Library | Frontend unit, component, and user-flow tests (37 tests across 6 suites) |
| **DevOps & CI** | Docker Compose v2, GitHub Actions | Multi-container orchestration, health checks, and automated CI pipelines |
| **Reference Backend**| Django 5, Django REST Framework, Channels | Preserved alternative reference implementation in `backend/` |

---

## Repository Structure

```text
engagement-pulse/
├── backend-fastapi/             # Active FastAPI backend application
│   ├── alembic/                 # Alembic migration revisions and configuration
│   ├── routers/                 # Route controllers (auth, organisations, projects, risks, csv_jobs, websocket)
│   ├── tests/                   # Pytest test suite (13 unit and API tests)
│   ├── broadcast_service.py     # Redis Pub/Sub broadcast utility
│   ├── config.py                # Pydantic Settings and environment configuration
│   ├── csv_service.py           # CSV validation, fingerprinting, and parsing logic
│   ├── database.py              # SQLAlchemy engine and session factory
│   ├── dependencies.py          # FastAPI dependencies (database sessions, authentication)
│   ├── Dockerfile               # Multi-stage container build for API and worker
│   ├── entrypoint.sh            # Health verification, migration, seed, and execution script
│   ├── main.py                  # Application entrypoint, CORS configuration, and lifespan
│   ├── models.py                # Declarative SQLAlchemy ORM models
│   ├── permissions.py           # Tenant and role authorization checks
│   ├── scoring_service.py       # Transactional risk score calculation logic
│   ├── security.py              # Password hashing and JWT generation
│   ├── seed.py                  # Idempotent demo data seeder
│   ├── tasks.py                 # Dramatiq task definitions for background CSV processing
│   ├── websocket_manager.py     # Connection manager and Redis Pub/Sub listener loop
│   └── ws_ticket_service.py     # Single-use WebSocket connection ticket manager
├── frontend/                    # Next.js 14 frontend application
│   ├── src/
│   │   ├── app/                 # Next.js App Router pages and layouts
│   │   ├── components/          # Dashboard, risk drawer, CSV dialog, and layout components
│   │   ├── context/             # AuthContext (session state, silent refresh)
│   │   ├── hooks/               # Custom hooks (useOrganisationUpdates WebSocket client)
│   │   ├── lib/                 # Typed API client (`apiClient`)
│   │   ├── types/               # TypeScript domain interfaces
│   │   └── __tests__/           # Jest test suites (37 tests across 6 suites)
│   ├── Dockerfile               # Production Next.js container build
│   └── package.json             # Frontend dependencies and test scripts
├── backend/                     # Preserved reference implementation (Django 5 + Channels)
├── docs/                        # Architecture decision records and deployment documentation
├── .github/workflows/           # GitHub Actions CI workflow (ci.yml)
├── docker-compose.yml           # Unified orchestration for FastAPI stack and services
└── README.md                    # Project documentation
```

---

## One-Command Startup

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) or Docker Engine with Docker Compose v2.

### Start the Application

From the repository root:

```bash
docker compose up --build -d
```

Startup is fully automated:
1. PostgreSQL (`db`) and Redis (`redis`) initialize with container health checks.
2. The `api` container waits for database readiness, applies `alembic upgrade head`, runs idempotent demo data seeding, and launches Uvicorn on port `8000`.
3. The `worker` container verifies schema availability and starts Dramatiq on the isolated `fastapi` queue.
4. The `frontend` container serves the Next.js production build on port `3000`.

### Service URLs

| Service | URL | Description |
| --- | --- | --- |
| **Frontend Web App** | [http://localhost:3000](http://localhost:3000) | Next.js interactive risk dashboard |
| **FastAPI Backend API** | [http://localhost:8000](http://localhost:8000) | REST API base endpoint |
| **Interactive API Docs** | [http://localhost:8000/docs](http://localhost:8000/docs) | Swagger UI for exploring and testing endpoints |
| **ReDoc Documentation** | [http://localhost:8000/redoc](http://localhost:8000/redoc) | Alternative OpenAPI documentation viewer |
| **Health Check** | [http://localhost:8000/health](http://localhost:8000/health) | Returns `{"status": "ok"}` for orchestration checks |
| **Live WebSocket** | `ws://localhost:8000/ws/organisations/{id}/updates/?ticket={ticket}` | Real-time organisation event stream |
| **PostgreSQL** | `localhost:5432` | Accessible to local database tools |
| **Redis** | `localhost:6379` | Accessible to Redis CLI and monitoring tools |

### Service Health Status

To verify that all containers are healthy:

```bash
docker compose ps
```

---

## Seeded Demo Accounts

The application automatically seeds initial organisations, demo users, projects, and risks via [`backend-fastapi/seed.py`](backend-fastapi/seed.py).

| Role | Email | Password Reference | Assigned Organisations | Permissions |
| --- | --- | --- | --- | --- |
| **Consultant** | `consultant@engagementpulse.com` | `$SEED_CONSULTANT_PASSWORD` | Acme Health, Beta Care, Acme Corp, Globex Corporation | Read/write across assigned organisations, edit risks, import CSVs |
| **Client Viewer** | `viewer.acme@example.com` | `$SEED_CLIENT_VIEWER_PASSWORD` | Acme Health | Read-only access locked to Acme Health |
| **Client Viewer** | `viewer.beta@example.com` | `$SEED_CLIENT_VIEWER_PASSWORD` | Beta Care | Read-only access locked to Beta Care |
| **Client Viewer** | `viewer.globex@example.com` | `$SEED_CLIENT_VIEWER_PASSWORD` | Globex Corporation | Read-only access locked to Globex Corporation |

> [!NOTE]
> Seed credentials are read from environment variables (`SEED_CONSULTANT_PASSWORD` and `SEED_CLIENT_VIEWER_PASSWORD`). Passwords are not hardcoded or committed to version control.

---

## Environment Configuration

Configuration is managed via environment variables and validated through Pydantic Settings in [`backend-fastapi/config.py`](backend-fastapi/config.py).

| Variable | Default Value (Docker Compose) | Description |
| --- | --- | --- |
| `DATABASE_URL` | `postgresql+psycopg://${DB_USER}:${DB_PASSWORD}@db:5432/${FASTAPI_DB_NAME}` | PostgreSQL connection string |
| `FASTAPI_DB_NAME` | `engagement_pulse_fastapi` | Dedicated database name for the FastAPI backend |
| `DB_USER` | `pulse_user` | PostgreSQL database user |
| `DB_PASSWORD` | *(Set via environment)* | PostgreSQL database password |
| `REDIS_URL` | `redis://redis:6379/0` | Redis broker and Pub/Sub connection URL |
| `DRAMATIQ_QUEUE_NAME` | `fastapi` | Dedicated worker queue name for task isolation |
| `CSV_UPLOAD_DIR` | `media/csv_imports` | Destination directory on shared volume `media_data` |
| `JWT_SECRET_KEY` | *(Set via environment)* | Secret key for signing JWT tokens (at least 32 characters) |
| `JWT_ALGORITHM` | `HS256` | Cryptographic algorithm for JWT signatures |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Access token lifespan in minutes |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token lifespan in days |
| `SEED_CONSULTANT_PASSWORD` | *(Set via environment)* | Password for seeded consultant user |
| `SEED_CLIENT_VIEWER_PASSWORD` | *(Set via environment)* | Password for seeded client viewer users |
| `DJANGO_INTERNAL_URL` | `http://backend:8000` | Next.js internal server-side proxy target |
| `NEXT_PUBLIC_WS_URL` | `ws://localhost:8000` | Browser WebSocket URL for real-time live updates |

---

## Multi-Tenant Authentication & Authorization

### Authentication Flow

1. **Sign-In:** Users authenticate via `POST /api/auth/login/` with email and password.
2. **Tokens:**
   - **Access Token:** Short-lived JWT (30 minutes) returned in the JSON payload and held in memory.
   - **Refresh Token:** Long-lived JWT (7 days) set in a secure, `HttpOnly`, `SameSite=Lax` cookie.
3. **Silent Refresh:** The frontend API client intercepts HTTP 401 responses and requests a fresh access token via `POST /api/auth/refresh/` using the HttpOnly cookie.
4. **Sign-Out:** `POST /api/auth/logout/` invalidates client session state and clears the refresh cookie.

### Tenant Isolation Model

- **Consultant Access:** Consultants map to multiple organisations through the `ConsultantOrganisationAccess` join table (composite unique constraint on `user_id, organisation_id`). Consultants can switch between assigned organisations and perform write operations.
- **Client Viewer Access:** Client viewers have a direct foreign key to exactly one organisation (`user.organisation_id`). They have read-only access locked to that single tenant.
- **Backend Enforcement:**
  - Accessible resource queries filter explicitly by authorized organisation IDs.
  - Inaccessible tenant resources return **HTTP 404 (Not Found)** to prevent cross-tenant discovery.
  - Unauthorized mutation attempts return **HTTP 403 (Forbidden)**.

---

## Project, Risk Management & Scoring Logic

### Data Hierarchy

- **Organisations** own projects.
- **Projects** own risks and maintain a cached `risk_score` (0–100).
- **Risks** contain:
  - `title` (required, 1–255 characters)
  - `description` (optional text)
  - `severity`: `low`, `medium`, `high`, `critical`
  - `status`: `open`, `mitigating`, `closed`
  - `owner` (optional text)

### Risk Scoring Formula

Scores are calculated based on configurable weights stored in PostgreSQL:

$$\text{Individual Risk Score} = \text{SeverityWeight} \times \text{StatusWeight}$$

$$\text{Project Risk Score} = \min\left(100, \sum \text{Individual Risk Scores}\right)$$

#### Default Weights

| Severity | Weight | Status | Weight |
| --- | --- | --- | --- |
| **Low** | 1 | **Open** | 3 |
| **Medium** | 2 | **Mitigating** | 2 |
| **High** | 3 | **Closed** | 0 |
| **Critical** | 4 | | |

*Example Calculation:*
- Risk 1: High severity (3) × Open status (3) = **9**
- Risk 2: Medium severity (2) × Mitigating status (2) = **4**
- Risk 3: Low severity (1) × Closed status (0) = **0**
- **Project Risk Score:** $\min(100, 9 + 4 + 0) = \mathbf{13}$

### Transactional Recalculation

Score recalculation is executed transactionally using PostgreSQL row-level locks (`SELECT ... FOR UPDATE` on `projects`) to guarantee concurrency safety during concurrent risk mutations or CSV imports.

---

## Background CSV Processing (Dramatiq + Redis)

1. **Non-Blocking Upload:** The consultant uploads a CSV file via `POST /api/projects/{project_id}/csv-jobs/`.
2. **Fingerprint Deduplication:** The backend calculates a SHA-256 hash of the file contents. If a job with the same `(project_id, submitting_user_id, file_fingerprint)` already exists (enforced by database unique constraint `uq_csv_jobs_dedup`), the existing job ID is returned immediately without duplicate processing.
3. **Queue Isolation:** The task is dispatched to Dramatiq on the dedicated `fastapi` queue, avoiding collision with Django workers on the shared Redis instance.
4. **Immediate Response:** The API responds with HTTP 201 containing the `job_id` and initial status `queued`.
5. **Worker Execution:** The Dramatiq worker validates CSV headers and rows, inserts or updates risks within a database transaction, recalculates the project risk score, and marks the job `completed`.
6. **Live Notification:** The worker publishes a `data_changed` event to Redis Pub/Sub upon successful completion.
7. **Client Polling:** The frontend polls `GET /api/csv-jobs/{job_id}/` every second until reaching a terminal state (`completed` or `failed`).

---

## Cross-Instance Real-Time WebSockets

Engagement Pulse uses Redis Pub/Sub to broadcast change notifications across multiple running API instances without sticky sessions or page refreshes.

### Secure Single-Use Connection Tickets

To avoid placing long-lived JWTs in WebSocket URLs:
1. The authenticated client requests a ticket via `POST /api/auth/ws-ticket/`.
2. The backend generates a random ticket stored in Redis with a 30-second TTL (`ws_ticket:<uuid>`).
3. The frontend connects to `ws://localhost:8000/ws/organisations/{org_id}/updates/?ticket=<uuid>`.
4. FastAPI atomically retrieves and deletes the ticket using Redis `GETDEL`. If the ticket is invalid or expired, the connection closes with code `4401`.
5. The backend validates tenant access for `org_id` (code `4403` if forbidden) and accepts the connection.

### Live Cache Invalidation

When a project, risk, or CSV import mutation occurs, the backend publishes `{ "type": "data_changed", "organisation_id": org_id, "project_id": project_id }` to Redis channel `fastapi:org:{org_id}`.

All API instances listening on Redis receive the message and route it to local connected WebSockets. The frontend hook `useOrganisationUpdates` invalidates React Query caches (`projects` and `risks`), prompting an immediate background refetch of fresh metrics.

---

## Main API Endpoints

All endpoints support optional `/api` prefixing.

### Authentication & Session

| Method | Endpoint | Description | Auth Required |
| --- | --- | --- | --- |
| `POST` | `/api/auth/login/` | Authenticate user; returns access token, sets HttpOnly refresh cookie | No |
| `POST` | `/api/auth/refresh/` | Obtain fresh access token using HttpOnly refresh cookie | No |
| `POST` | `/api/auth/logout/` | Terminate session and clear refresh cookie | Yes |
| `GET` | `/api/auth/me/` | Get current user profile, role, and accessible organisations | Yes |
| `POST` | `/api/auth/ws-ticket/` | Generate short-lived single-use ticket for WebSocket authentication | Yes |

### Organisations

| Method | Endpoint | Description | Auth Required |
| --- | --- | --- | --- |
| `GET` | `/api/organisations/` | List accessible organisations for current user | Yes |

### Projects

| Method | Endpoint | Description | Auth Required |
| --- | --- | --- | --- |
| `GET` | `/api/organisations/{org_id}/projects/` | List projects and risk scores for an organisation | Yes |
| `POST` | `/api/organisations/{org_id}/projects/` | Create a new project within an organisation (Consultants only) | Yes (Consultant) |
| `GET` | `/api/projects/{project_id}/` | Retrieve project detail by ID | Yes |
| `PATCH`| `/api/projects/{project_id}/` | Update project name (Consultants only) | Yes (Consultant) |

### Risks

| Method | Endpoint | Description | Auth Required |
| --- | --- | --- | --- |
| `GET` | `/api/projects/{project_id}/risks/` | List all risks belonging to a project | Yes |
| `POST` | `/api/projects/{project_id}/risks/` | Create a new project risk (Consultants only) | Yes (Consultant) |
| `GET` | `/api/risks/{risk_id}/` | Retrieve risk detail by ID | Yes |
| `PATCH`| `/api/risks/{risk_id}/` | Update risk fields; recalculates score and broadcasts live update | Yes (Consultant) |
| `DELETE`| `/api/risks/{risk_id}/` | Delete risk; recalculates score and broadcasts live update | Yes (Consultant) |

### CSV Import Jobs

| Method | Endpoint | Description | Auth Required |
| --- | --- | --- | --- |
| `POST` | `/api/projects/{project_id}/csv-jobs/` | Upload CSV for background processing; returns job ID immediately | Yes (Consultant) |
| `GET` | `/api/csv-jobs/{job_id}/` | Retrieve status, row counts, and error details for a CSV import job | Yes |

### WebSockets & System

| Method | Endpoint | Description | Auth Required |
| --- | --- | --- | --- |
| `GET` | `/ws/organisations/{org_id}/updates/` | Live organisation WebSocket event stream (`?ticket=<ticket>`) | Yes (Ticket) |
| `GET` | `/health` | Service health check (`{"status": "ok"}`) | No |

---

## Database Migrations & Seeding

The application manages database schema changes with Alembic.

### Running Migrations

When using Docker Compose, migrations run automatically on startup. To run migrations manually:

```bash
# Inside Docker:
docker compose exec api alembic upgrade head

# In local environment (backend-fastapi virtualenv):
cd backend-fastapi
alembic upgrade head
```

### Seeding Data

To seed development organisations, users, projects, and risks idempotently:

```bash
# Inside Docker:
docker compose exec api python seed.py

# In local environment:
cd backend-fastapi
python seed.py
```

---

## Verification & Testing

### Running Tests Locally

#### 1. Backend Pytest Suite (13 Tests)

```bash
docker compose exec api pytest tests/ -v
```

The 13 backend unit and API tests in `backend-fastapi/tests/` verify:
- `test_auth.py`: Login with valid/invalid credentials, token refresh, logout, `/api/auth/me/`, and WebSocket ticket generation
- `test_csv_jobs.py`: Consultant CSV upload, status polling, and client viewer upload restriction (HTTP 403)
- `test_health.py`: Service health check response
- `test_organisations.py`: Consultant organisation listing, client viewer tenant isolation, and unauthenticated rejection
- `test_projects_and_risks.py`: Project and risk listing, and viewer write restriction (HTTP 403)
- `test_scoring.py`: Persisted scoring weights, score recalculation, and project score capping at 100

#### 2. Frontend Jest Test Suite (37 Tests)

```bash
npm --prefix frontend test -- --watchAll=false --runInBand
```

The 37 frontend tests across 6 test suites verify:
- `api-client.test.ts`: Request authentication, header injection, error parsing, and token refresh
- `auth-protected-routes.test.tsx`: Route guards and login redirection in `AppShell`
- `organisation-selection.test.tsx`: Organisation switcher dropdown and client viewer role locking
- `csv-import.test.tsx`: CSV dialog, file upload mutation, job polling, and error presentation
- `dashboard-risk-updates.test.tsx`: Risk editing and live cache invalidation without infinite re-render loops
- `live-updates.test.tsx`: WebSocket ticket retrieval, connection lifecycle, and event invalidation

#### 3. Frontend Production Build Check

```bash
npm --prefix frontend run build
```

Validates TypeScript compilation, route bundling, and static page generation.

### Continuous Integration (CI)

A GitHub Actions workflow is configured in [`.github/workflows/ci.yml`](.github/workflows/ci.yml). On every push or pull request to `master`, `develop`, or `feature/**` branches, CI runs:

1. **`backend-fastapi-tests`**:
   - Launches PostgreSQL 16 and Redis 7 service containers with health checks.
   - Sets up Python 3.12 and installs dependencies.
   - Applies database migrations (`alembic upgrade head`).
   - Runs database seeding (`python seed.py`).
   - Executes the 13 backend tests with `pytest tests/ -v`.
2. **`frontend-tests`**:
   - Sets up Node.js 20.
   - Performs a clean dependency install (`npm --prefix frontend ci`).
   - Executes all 37 Jest tests (`npm --prefix frontend test -- --watchAll=false --runInBand`).
   - Executes the Next.js production build (`npm --prefix frontend run build`).

---

## Stopping and Resetting the Application

### Stop Containers

To gracefully stop running services while preserving database and volume data:

```bash
docker compose down
```

### Clean Slate Reset

To stop containers, remove persistent volumes (PostgreSQL database, Redis cache, uploaded CSV files), and rebuild:

```bash
docker compose down -v
docker compose up --build -d
```

---

## Alternative Django Backend Reference

The original Django backend implementation is preserved in the `backend/` directory as an alternative reference implementation. It can be started on demand using the `django` Compose profile:

```bash
docker compose --profile django up --build
```
