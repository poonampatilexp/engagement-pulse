# Engagement Pulse — FastAPI Backend

Minimal initial setup for the FastAPI rebuild of the Engagement Pulse backend.

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

### 3. Run Development Server

```bash
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Or run directly via python:

```bash
python main.py
```

### 4. Verify Endpoints

- **Health Check:** [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health) -> `{"status": "ok"}`
- **Interactive Swagger Docs:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

