# Engagement Pulse

**A multi-tenant project risk dashboard with asynchronous imports and live client updates.**

Engagement Pulse helps consultants track project risks across client organisations while giving stakeholders a read-only, continuously updated view of delivery health. It is designed around three practical requirements: **strict tenant isolation**, **non-blocking bulk processing**, and **real-time updates across application instances**.

## Highlights

- **Organisation-scoped access:** Consultants work across assigned organisations; client viewers can only read data belonging to their organisation. Permissions are enforced by backend APIs, not just the UI.
- **Asynchronous CSV imports:** Uploads run through Dramatiq and Redis, with persisted job status, worker queue isolation, and automatic risk-score recalculation.
- **Live dashboards:** FastAPI WebSockets and Redis Pub/Sub broadcast organisation-specific change signals. Connected clients invalidate React Query caches and fetch fresh data without a page reload.
- **Reproducible setup:** Docker Compose starts the complete stack, applies Alembic migrations, and seeds demo data automatically with health checks.
- **Continuous Integration:** GitHub Actions CI workflow validates backend unit/API tests, frontend Jest suites, and Next.js production builds.

## Architecture

```text
                 Next.js / React dashboard
                  |                 ^
            REST / JWT         WebSocket updates
                  |                 |
                  v                 |
            FastAPI ASGI API (Uvicorn)
                  |             |
              PostgreSQL      Redis
                  ^          /    \
                  |     Pub/Sub  Dramatiq (fastapi queue)
                  |                    |
                  +------ Dramatiq worker
                        (CSV processing)
```

**Technology:** Next.js 14, React 18, TypeScript, Material UI, React Query · FastAPI, SQLAlchemy 2, Alembic, Uvicorn · PostgreSQL 16 · Redis 7 · Dramatiq · Docker Compose · GitHub Actions.

### Key engineering decisions

| Concern                  | Approach                                                                                                                                     |
| ------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------- |
| Tenant security          | API-level organisation scoping and role-based write permissions; cross-tenant resources return 404/403 and are never exposed.                |
| Background processing    | CSV imports are queued and tracked in PostgreSQL; Dramatiq workers consume from a dedicated `fastapi` queue independently of HTTP requests.   |
| Cross-instance updates   | Redis Pub/Sub broadcasts lightweight `data_changed` signals after mutations; the frontend refetches authoritative data automatically.       |
| WebSocket authentication | Authenticated clients request 30-second, single-use connection tickets, consumed atomically in Redis via `GETDEL`.                           |
| Session management       | Short-lived access tokens in memory; refresh tokens stored in HttpOnly cookies with automatic silent rotation on 401.                         |
| Risk consistency         | Configurable weights are persisted in PostgreSQL; project scores are recalculated transactionally with row-level locking (`FOR UPDATE`).      |
| Automated startup        | Container health checks, startup dependencies, and automatic migrations/seeding eliminate manual setup commands.                             |

## Quick start

**Prerequisite:** Docker Desktop or Docker Engine with Docker Compose v2.

From the repository root:

```bash
docker compose up --build -d
```

Open **http://localhost:3000** in your browser. The API runs at **http://localhost:8000**.
Database migrations and demo-data seeding run automatically; no separate worker or database setup is required.

### Demo accounts

| Role          | Email                            | Password                | Access                                                                  |
| ------------- | -------------------------------- | ----------------------- | ----------------------------------------------------------------------- |
| Consultant    | `consultant@engagementpulse.com` | `ConsultantDevPass#2026`| Acme Health, Beta Care, Acme Corp, Globex Corporation                   |
| Client Viewer | `viewer.acme@example.com`        | `ViewerDevPass#2026`    | Acme Health (read-only)                                                 |
| Client Viewer | `viewer.beta@example.com`        | `ViewerDevPass#2026`    | Beta Care (read-only)                                                   |
| Client Viewer | `viewer.globex@example.com`      | `ViewerDevPass#2026`    | Globex Corporation (read-only)                                          |

> [!NOTE]
> Custom passwords can be supplied via environment variables (`SEED_CONSULTANT_PASSWORD` and `SEED_CLIENT_VIEWER_PASSWORD`).

### Service Health Checks

All critical services are configured with health checks and dependency conditions in `docker-compose.yml`:

| Service    | Health Check Command                                      | Success Criteria                                    |
| ---------- | --------------------------------------------------------- | --------------------------------------------------- |
| `db`       | `pg_isready -U pulse_user -d postgres`                    | PostgreSQL is accepting client connections          |
| `redis`    | `redis-cli ping`                                          | Redis responds with PONG                            |
| `api`      | `curl -f http://localhost:8000/health`                    | FastAPI returns HTTP 200 `{"status": "ok"}`         |
| `worker`   | Waits for `api` health check (`service_healthy`)          | Starts only after migrations and schema are ready   |
| `frontend` | Waits for `api` health check (`service_healthy`)          | Starts serving after backend is fully operational   |

To verify service health:

```bash
docker compose ps
```

### Shutdown and Volume Management

- **Stop containers:**
  ```bash
  docker compose down
  ```
- **Reset database and volumes (clean slate):**
  ```bash
  docker compose down -v
  docker compose up --build -d
  ```

## Environment Variables

| Variable                       | Default Value                                                                       | Description                                                    |
| ------------------------------ | ----------------------------------------------------------------------------------- | -------------------------------------------------------------- |
| `FASTAPI_DB_NAME`              | `engagement_pulse_fastapi`                                                          | Dedicated database name for FastAPI backend                     |
| `DB_USER`                      | `pulse_user`                                                                        | PostgreSQL username                                            |
| `DB_PASSWORD`                  | `pulse_password`                                                                    | PostgreSQL password                                            |
| `DATABASE_URL`                 | `postgresql+psycopg://pulse_user:pulse_password@db:5432/engagement_pulse_fastapi`   | SQLAlchemy PostgreSQL connection string                        |
| `REDIS_URL`                    | `redis://redis:6379/0`                                                              | Redis connection string for Pub/Sub and Dramatiq               |
| `DRAMATIQ_QUEUE_NAME`          | `fastapi`                                                                           | Dedicated worker queue name for task isolation                 |
| `CSV_UPLOAD_DIR`               | `media/csv_imports`                                                                 | Upload destination on shared volume `media_data`               |
| `JWT_SECRET_KEY`               | Development key (override in production)                                           | Secret used to sign access and refresh tokens                  |
| `SEED_CONSULTANT_PASSWORD`     | `ConsultantDevPass#2026`                                                            | Password for seeded consultant user                            |
| `SEED_CLIENT_VIEWER_PASSWORD`  | `ViewerDevPass#2026`                                                                | Password for seeded client viewer users                        |
| `DJANGO_INTERNAL_URL`          | `http://backend:8000`                                                               | Next.js internal server-side proxy URL for API calls           |
| `INTERNAL_API_URL`             | `http://backend:8000`                                                               | Fallback internal proxy URL for Next.js                        |
| `NEXT_PUBLIC_WS_URL`           | `ws://localhost:8000`                                                               | Browser WebSocket URL for live updates                         |

## Verification & Testing

### Running Tests Locally

- **Backend API & Unit Tests (inside Docker):**
  ```bash
  docker compose exec api pytest tests/ -v
  ```
- **Frontend Jest Tests (React Testing Library):**
  ```bash
  npm --prefix frontend test -- --watchAll=false --runInBand
  ```
- **Frontend Production Build Check:**
  ```bash
  npm --prefix frontend run build
  ```

### Continuous Integration (CI)

A GitHub Actions workflow is defined in [`.github/workflows/ci.yml`](file:///.github/workflows/ci.yml). On every push and pull request, CI executes:
1. **`backend-fastapi-tests`**: Sets up Python 3.12 with PostgreSQL and Redis service containers, runs Alembic migrations (`alembic upgrade head`), applies idempotent seeding, and executes all unit and API tests with `pytest`.
2. **`frontend-tests`**: Sets up Node.js 20, installs dependencies with `npm ci`, runs Jest test suites sequentially (`--runInBand`), and validates the Next.js production build (`npm run build`).

## Alternative Django Backend

The original Django backend implementation is completely preserved in `backend/` and can be run on demand using the `django` Compose profile:

```bash
docker compose --profile django up --build
```

## Explore the Application

1. **Consultant Workflow:** Sign in as `consultant@engagementpulse.com`, switch between organisations using the header chip dropdown, edit a project risk, or import CSV risks and observe the progress.
2. **Client Viewer Workflow:** Sign in as `viewer.acme@example.com` to inspect assigned organisation projects, risks, and calculated scores in read-only mode.
3. **Real-Time Live Updates:** Open both sessions side-by-side. When the consultant mutates a risk or completes a CSV import, the viewer dashboard automatically receives a `data_changed` event and refreshes metrics without reloading the page.
