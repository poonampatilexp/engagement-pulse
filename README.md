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
- **Frontend:** React, Next.js App Router, TypeScript, React Query *(Upcoming)*
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

Apply Django migrations to set up the custom User and Organisation schema:

```bash
python backend/manage.py migrate
```

### 6. Seed Demo Data

Run the repeatable seed command:

```bash
python backend/manage.py seed_data
```

This command idempotently creates two client organisations, one consultant assigned to both, and one client viewer per organisation.

---

## Seeded Demo Accounts

| Role | Email | Password | Assigned Organisation(s) |
| :--- | :--- | :--- | :--- |
| **Consultant** | `consultant@engagementpulse.com` | `Password123!` | Acme Corp, Globex Corporation |
| **Client Viewer** | `viewer.acme@example.com` | `Password123!` | Acme Corp |
| **Client Viewer** | `viewer.globex@example.com` | `Password123!` | Globex Corporation |

---

## Implemented API Endpoints

### Authentication

- `POST /api/auth/login/`: Accepts `{"email": "...", "password": "..."}`. Returns access token, refresh token, and user profile with assigned organisation scope.
- `POST /api/auth/refresh/`: Accepts `{"refresh": "..."}`. Returns fresh access token.
- `GET /api/auth/me/`: Returns current authenticated user details and assigned organisation(s). Requires `Authorization: Bearer <token>`.

### Organisations

- `GET /api/organisations/`: Returns list of organisations accessible to the authenticated user.
  - **Consultants** receive all organisations assigned via `ConsultantOrganisationAccess`.
  - **Client Viewers** receive only their single organisation.
  - **Unauthenticated requests** receive `401 Unauthorized`.
- `GET /api/organisations/<id>/`: Retrieves a single organisation.
  - Returns `200 OK` if the user is authorized.
  - Returns `404 Not Found` if the organisation does not exist or belongs to another tenant.

---

## Verification & Testing

Execute the backend test suite:

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

---

## AI-Assisted Development Disclosure

In accordance with project standards, this milestone was developed with AI assistance from Google Antigravity (Advanced Agentic Coding). Architecture, domain modeling, and test suites adhere strictly to the engineering rules defined in `AGENTS.md`.

