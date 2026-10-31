# Engagement Pulse

A secure, multi-tenant engagement risk management application.

Consultants manage projects and risks for assigned client organisations. Client viewers have read-only access to their own organisation's data.

---

## Approved Technology Stack

- **Backend:** Python 3.12, Django 5, Django REST Framework
- **Database:** PostgreSQL 16 (Django ORM & migrations)
- **Authentication:** JWT via `djangorestframework-simplejwt`
- **Background Processing:** Dramatiq with Redis *(Upcoming)*
- **Real-Time Updates:** Django Channels with `channels_redis` *(Upcoming)*
- **Frontend:** React 18, Next.js 14 App Router, TypeScript, Material UI (MUI), TanStack React Query
- **Testing:** pytest, pytest-django, React Testing Library, Playwright
- **Infrastructure:** Docker Compose

---

## Local Setup Instructions

### 1. Prerequisites

- Python 3.12+
- Docker and Docker Compose

### 2. Environment Configuration

Copy the example environment configuration:

```bash
cp .env.example .env
```

Default local `.env` values:

```env
DEBUG=True
SECRET_KEY=django-insecure-engagement-pulse-dev-secret-key-change-in-prod-12345
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0
DB_ENGINE=django.db.backends.postgresql
DB_NAME=engagement_pulse
DB_USER=pulse_user
DB_PASSWORD=pulse_password
DB_HOST=localhost
DB_PORT=5432
```

### 3. Start PostgreSQL Database

Launch PostgreSQL in the background via Docker Compose:

```bash
docker-compose up -d db
```

### 4. Install Backend Dependencies

Create a virtual environment and install the requirements:

```bash
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

pip install -r backend/requirements.txt
```

### 5. Run Database Migrations

Apply Django migrations to set up the User, Organisation, Project, and Risk schema:

```bash
python backend/manage.py migrate
```

### 6. Seed Demo Data

Run the repeatable seed command:

```bash
python backend/manage.py seed_data
```

This command idempotently:
1. Seeds default risk scoring weights in PostgreSQL.
2. Creates two client organisations: **Acme Corp** and **Globex Corporation**.
3. Creates one consultant (`consultant@engagementpulse.com`) assigned to both organisations.
4. Creates client viewers for Acme and Globex.
5. Seeds demo projects and risks, calculating initial project risk scores.

### 7. Run the Backend API Server

Start the Django development server on port 8000:

```bash
python backend/manage.py runserver 8000
```

### 8. Frontend Setup & Run

In a separate terminal, install Node.js dependencies and start the Next.js development server:

```bash
cd frontend
npm install
npm run dev -- -p 3000
```

Open [http://localhost:3000/login](http://localhost:3000/login) in your browser. All `/api/*` requests are proxied automatically to `http://127.0.0.1:8000`.

To build the production bundle:

```bash
cd frontend
npm run build
```

To run frontend unit and integration tests (Jest & React Testing Library):

```bash
cd frontend
npm test
```

---

## Seeded Demo Accounts

| Role | Email | Password | Assigned Organisation(s) |
| :--- | :--- | :--- | :--- |
| **Consultant** | `consultant@engagementpulse.com` | `Password123!` | Acme Corp, Globex Corporation |
| **Client Viewer** | `viewer.acme@example.com` | `Password123!` | Acme Corp |
| **Client Viewer** | `viewer.globex@example.com` | `Password123!` | Globex Corporation |

---

## Risk Scoring Formula and Weights

Risk severity and status choices are defined in application code, while their weights are persisted in PostgreSQL:

### Severity Weights

| Severity | Weight |
| :--- | :---: |
| `low` | 1 |
| `medium` | 2 |
| `high` | 3 |
| `critical` | 4 |

### Status Weights

| Status | Weight |
| :--- | :---: |
| `open` | 3 |
| `mitigating` | 2 |
| `closed` | 0 |

### Mathematical Formula

$$\text{Individual Risk Contribution} = \text{SeverityWeight} \times \text{StatusWeight}$$

$$\text{Project Risk Score} = \min\left(100, \sum \text{Risk Contributions}\right)$$

A project without risks has a score of `0`.

### Example Calculation
- High severity (3) and Open status (3) contributes: $3 \times 3 = 9$
- Medium severity (2) and Mitigating status (2) contributes: $2 \times 2 = 4$
- **Total Project Risk Score** = $\min(100, 9 + 4) = 13$

### Concurrency and Persistence
- Calculated scores are saved directly on `Project.risk_score`.
- Recalculation occurs inside database transactions with PostgreSQL row-level locking (`select_for_update()`) on the `Project` record.
- Direct client manipulation of `risk_score` is disallowed by serializers.

---

## Implemented API Endpoints

### 1. Authentication

- `POST /api/auth/login/`: Accepts `{"email": "...", "password": "..."}`. Returns access token, refresh token, and user profile with assigned organisation scope.
- `POST /api/auth/refresh/`: Accepts `{"refresh": "..."}`. Returns fresh access token.
- `GET /api/auth/me/`: Returns current authenticated user details and assigned organisation(s). Requires `Authorization: Bearer <token>`.

### 2. Organisations

- `GET /api/organisations/`: Returns list of organisations accessible to the authenticated user.
  - **Consultants** receive all organisations assigned via `ConsultantOrganisationAccess`.
  - **Client Viewers** receive only their single organisation.
  - **Unauthenticated requests** receive `401 Unauthorized`.
- `GET /api/organisations/<id>/`: Retrieves a single organisation.
  - Returns `200 OK` if the user is authorized.
  - Returns `404 Not Found` if the organisation does not exist or belongs to another tenant.

### 3. Projects

- `GET /api/organisations/<organisation_id>/projects/`: Lists all projects for an organisation.
- `POST /api/organisations/<organisation_id>/projects/`: Creates a project within an organisation (Consultants only; Client Viewers receive `403 Forbidden`).
- `GET /api/projects/<project_id>/`: Retrieves project details, including current `risk_score`.
- `PATCH /api/projects/<project_id>/`: Updates project name (Consultants only).
- `DELETE /api/projects/<project_id>/`: Deletes project and associated risks (Consultants only).

### 4. Risks

- `GET /api/projects/<project_id>/risks/`: Lists all risks associated with a project.
- `POST /api/projects/<project_id>/risks/`: Adds a risk to a project. Triggers automatic project score recalculation (Consultants only).
- `GET /api/risks/<risk_id>/`: Retrieves details of a specific risk.
- `PATCH /api/risks/<risk_id>/`: Updates risk title, description, severity, status, or owner. Automatically recalculates project score (Consultants only). Reassigning `project` is disallowed.
- `DELETE /api/risks/<risk_id>/`: Deletes a risk. Automatically recalculates project score (Consultants only).

---

## Sample Workflows

### Consultant Workflow
1. **Login:** Send `POST /api/auth/login/` with consultant credentials.
2. **Select Organisation:** Call `GET /api/organisations/` to retrieve assigned organisations (e.g., Acme Corp ID `1`).
3. **Create Project:** Call `POST /api/organisations/1/projects/` with `{"name": "Supply Chain Overhaul"}`. Initial `risk_score` is `0`.
4. **Add Risk:** Call `POST /api/projects/<project_id>/risks/` with `{"title": "Vendor SLA Breaches", "severity": "high", "status": "open"}`. Project `risk_score` automatically updates to `9`.
5. **Mitigate Risk:** Call `PATCH /api/risks/<risk_id>/` with `{"status": "mitigating"}`. Project `risk_score` automatically updates to `6`.
6. **Close Risk:** Call `PATCH /api/risks/<risk_id>/` with `{"status": "closed"}`. Project `risk_score` drops to `0`.

### Client Viewer Workflow
1. **Login:** Send `POST /api/auth/login/` with client viewer credentials (`viewer.acme@example.com`).
2. **View Accessible Projects:** Call `GET /api/organisations/1/projects/` to inspect project progress and risk scores.
3. **View Project Risks:** Call `GET /api/projects/1/risks/` to inspect all identified risks.
4. **Attempted Modification:** Calling `POST /api/projects/1/risks/` or `PATCH /api/projects/1/` is blocked with `403 Forbidden`.
5. **Attempted Cross-Tenant Access:** Calling `GET /api/organisations/2/projects/` (Globex) is blocked with `404 Not Found`.

---

## Future Scoring Enhancements

1. **Project-Size Normalisation:** Add normalisation to prevent projects with many low-impact risks from scoring artificially higher than small projects with single critical vulnerabilities.
2. **Historical Score Trends:** Implement daily snapshots and audit logs to chart risk trends over time on dashboards.
3. **Configurable Organisation Thresholds:** Support tenant-specific RAG (Red/Amber/Green) risk thresholds (e.g., Green: 0-25, Amber: 26-60, Red: 61-100).
4. **Dynamic Weight Change Recalculation:** When administrators update severity or status weights, trigger asynchronous background recalculation jobs across all projects via Dramatiq.

---

## Authentication & JWT Session Management

Engagement Pulse employs an in-memory access token architecture with an `HttpOnly` cookie-backed refresh strategy:
- **Access Tokens:** Maintained strictly in-memory (`AuthContext` and `apiClient`). Tokens are never persisted to `localStorage` or `sessionStorage`, mitigating XSS credential theft.
- **Refresh Tokens:** Issued as `HttpOnly`, `SameSite=Lax`, `Path=/api/auth/` cookies by Next.js Backend-For-Frontend (BFF) route handlers (`/api/auth/login`, `/api/auth/refresh`, `/api/auth/logout`), forwarding to Django Simple JWT.
- **Deduplicated Refresh & Retry:** The API client intercepts `401 Unauthorized` responses and triggers a single in-flight token refresh promise. Concurrent requests awaiting refresh are queued and retried together with the fresh access token, preventing duplicate refresh operations.
- **Protected Routes & Flashing Prevention:** `AppShell` guards protected routes (`/`) by verifying session state. While verifying, a branded loading spinner is rendered; unauthenticated visitors are redirected to `/login` without exposing protected DOM content. Authenticated visitors visiting `/login` are automatically redirected to `/`.
- **Cache-Clearing Logout:** The logout action calls `/api/auth/logout/` (purging the cookie), wipes the in-memory access token, clears the entire TanStack React Query cache (`queryClient.clear()`), and navigates to `/login`.

---

## Verification & Testing

### Frontend Test Suite (Jest & React Testing Library)

Execute the frontend tests:

```bash
npm --prefix frontend test
```

The frontend test suite validates:
1. In-memory access token storage and header attachment on API requests.
2. Transparent token refresh on 401 with immediate single-retry.
3. Concurrent request deduplication ensuring only one refresh request fires across simultaneous failures.
4. Refresh failure handling with token clearance and authentication failure callback.
5. Protected route redirection to `/login` for unauthenticated visitors.
6. Redirection away from `/login` to `/` for authenticated visitors.
7. Branded loading indicator during authentication check preventing protected content exposure.
8. Role rendering and organization details for Consultants and Client Viewers.
9. Complete cache clearance (`queryClient.clear()`) and in-memory wipe upon logout.

---

### Backend Test Suite (Pytest)

Execute the complete backend test suite:

```bash
pytest backend/tests
```

The test suite validates:
1. Consultant login, token generation, and multi-organisation visibility.
2. Client viewer login, token generation, and single-organisation isolation.
3. Denial of unauthenticated requests (`401 Unauthorized`).
4. Rejection of cross-organisation access (`404 Not Found`).
5. Database-level unique constraint enforcement on `(user, organisation)` in `ConsultantOrganisationAccess`.
6. Idempotency and repeatability of the `seed_data` command.
7. Project and risk CRUD lifecycles.
8. Client viewer read-only permission enforcement (`403 Forbidden` on mutation).
9. Accurate risk scoring formula calculation across multiple risks and edge cases (empty project, capping at 100).
10. Automatic score recalculation on risk creation, status modification, reopening, and deletion.
11. Prevention of client-supplied `risk_score` tampering.
12. Validation of severity and status choices.

---

## AI-Assisted Development Disclosure

In accordance with project standards, this milestone was developed with AI assistance from Google Antigravity (Advanced Agentic Coding). Architecture, domain modeling, and test suites adhere strictly to the engineering rules defined in `AGENTS.md`.
