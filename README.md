# Engagement Pulse

**A multi-tenant project risk dashboard with asynchronous imports and live client updates.**

Engagement Pulse helps consultants track project risks across client organisations while giving stakeholders a read-only, continuously updated view of delivery health. It is designed around three practical requirements: **strict tenant isolation**, **non-blocking bulk processing**, and **real-time updates across application instances**.

## Highlights

- **Organisation-scoped access:** Consultants work across assigned organisations; client viewers can only read data belonging to their organisation. Permissions are enforced by Django APIs, not just the UI.
- **Asynchronous CSV imports:** Uploads run through Dramatiq and Redis, with persisted job status and automatic risk-score recalculation.
- **Live dashboards:** Django Channels broadcasts organisation-specific change signals through Redis. Connected clients invalidate React Query caches and fetch fresh data without a page reload.
- **Reproducible setup:** Docker Compose starts the complete stack, applies migrations and seeds demo data.

## Architecture

```text
                 Next.js / React dashboard
                  |                 ^
            REST / JWT         WebSocket updates
                  |                 |
                  v                 |
              Django / DRF / Channels (Daphne)
                 |             |
             PostgreSQL      Redis
                 ^          /    \
                 |     Channels  Dramatiq queue
                 |                    |
                 +------ Dramatiq worker
                       (CSV processing)
```

**Technology:** Next.js 14, React 18, TypeScript, Material UI, React Query · Django 5, Django REST Framework, Django Channels, Daphne · PostgreSQL 16 · Redis · Dramatiq · Docker Compose.

### Key engineering decisions

| Concern                  | Approach                                                                                                                                     |
| ------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------- |
| Tenant security          | API-level organisation scoping and role-based write permissions; cross-tenant resources are not exposed.                                     |
| Background processing    | CSV imports are queued and tracked in PostgreSQL; workers process uploads independently of HTTP requests.                                    |
| Cross-instance updates   | Redis-backed Channels groups broadcast lightweight `data_changed` signals after database commits; the frontend refetches authoritative data. |
| WebSocket authentication | Authenticated clients request 30-second, single-use connection tickets, consumed atomically in Redis.                                        |
| Session management       | Short-lived access tokens in memory; refresh tokens managed through HttpOnly cookies in Next.js route handlers.                              |
| Risk consistency         | Configurable weights are persisted in PostgreSQL; project scores are recalculated transactionally with row-level locking.                    |

## Quick start

**Prerequisite:** Docker Desktop or Docker Engine with Docker Compose v2.

From the repository root:

```bash
docker compose up --build
```

Open **http://localhost:3000**. The API runs at **http://localhost:8000**. Migrations and demo-data seeding run automatically; no separate worker or database setup is required.

### Demo accounts

All demo accounts use the password **`Password123!`** (local development only).

| Role          | Email                            | Access                           |
| ------------- | -------------------------------- | -------------------------------- |
| Consultant    | `consultant@engagementpulse.com` | Acme Corp and Globex Corporation |
| Client Viewer | `viewer.acme@example.com`        | Acme Corp, read-only             |
| Client Viewer | `viewer.globex@example.com`      | Globex Corporation, read-only    |

Stop services with `docker compose down`. To reset the local database and reseed, run `docker compose down -v` followed by `docker compose up --build` (**this deletes local Docker volumes**).

## Explore the application

1. **Consultant:** Sign in, switch between organisations, edit a project risk or upload a CSV file, and follow the import job status.
2. **Client Viewer:** Sign in separately to view the assigned organisation's projects, risks and recalculated scores. Write operations and cross-organisation access are denied by the API.
3. **Live updates:** Keep both sessions open. When the consultant updates a risk, the viewer receives a change signal and the dashboard refreshes without a page reload.

### Risk scoring

Risk contributions are calculated as **severity weight × status weight**, summed per project and capped at 100. Severity weights are low = 1, medium = 2, high = 3, critical = 4; status weights are open = 3, mitigating = 2, closed = 0. A project with no risks scores 0.

## Verification

The implementation has been exercised with **75 passing backend tests** and **30 passing frontend tests**, covering authentication, organisation isolation, risk operations and scoring, CSV processing, and WebSocket behaviour. A Docker-based smoke test verified logins, tenant boundaries, WebSocket handshake and background CSV completion. Cross-instance Redis delivery was also verified manually using two separate Django instances.

```bash
docker compose exec backend pytest
npm --prefix frontend test -- --watchAll=false
```

**Scope and next steps:** Browser-level E2E automation and a CI workflow were intentionally deferred for this time-boxed exercise. Other potential improvements include audit history, risk trends, frontend project creation and richer filtering/pagination. These are not represented as implemented features.

## Development approach

Built with AI-assisted coding using Google Antigravity, with architecture choices, implementation boundaries and verification guided by project instructions in `AGENTS.md`.

## Documents

Find the Architecture and Azure documentation under the docs folder
