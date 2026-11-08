# Engagement Pulse — FastAPI Backend

FastAPI rebuild of the Engagement Pulse backend using SQLAlchemy 2.x, PostgreSQL (psycopg 3), Pydantic Settings, and Alembic database migrations.

## Local Setup

### 1. Create and Activate Virtual Environment

```bash
cd backend-fastapi
python -m venv .venv
```

Activate the virtual environment:
- **Windows (PowerShell):** `.\.venv\Scripts\Activate.ps1`
- **Linux / macOS:** `source .venv/bin/activate`

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Dedicated Database Setup

To avoid conflicting with the existing Django database (`engagement_pulse`), FastAPI uses a dedicated database named `engagement_pulse_fastapi`.

Create the dedicated database in PostgreSQL:

```bash
# Using psql or docker exec on the db container:
docker compose exec db psql -U pulse_user -d postgres -c "CREATE DATABASE engagement_pulse_fastapi OWNER pulse_user;"
```

### 4. Environment Configuration

Copy the example environment file:

```bash
cp .env.example .env
```

Default PostgreSQL connection string:
```env
DATABASE_URL=postgresql+psycopg://pulse_user:pulse_password@localhost:5432/engagement_pulse_fastapi
```

### 5. Database Migrations (Alembic)

Once `engagement_pulse_fastapi` exists, run migrations:

```bash
# Apply migrations to the latest revision
alembic upgrade head

# Check current revision status
alembic current

# View migration history
alembic history --verbose

# Roll back the most recent migration (if needed)
alembic downgrade -1

# Generate a new migration after changing models
alembic revision --autogenerate -m "describe changes"
```

### 6. Run Development Server

```bash
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Or run directly via python:

```bash
python main.py
```

### 7. Verify Endpoints

- **Health Check:** [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health) -> `{"status": "ok"}`
- **Interactive Swagger Docs:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
