# Engagement Pulse — FastAPI Backend

FastAPI rebuild of the Engagement Pulse backend using SQLAlchemy 2.x, PostgreSQL (psycopg 3), and Pydantic Settings.

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

### 3. Environment Configuration

Copy the example environment file:

```bash
cp .env.example .env
```

Default PostgreSQL connection string:
```env
DATABASE_URL=postgresql+psycopg://pulse_user:pulse_password@localhost:5432/engagement_pulse
```

### 4. Run Development Server

```bash
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Or run directly via python:

```bash
python main.py
```

### 5. Verify Endpoints

- **Health Check:** [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health) -> `{"status": "ok"}`
- **Interactive Swagger Docs:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
