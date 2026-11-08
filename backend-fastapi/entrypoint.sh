#!/bin/sh
set -e

echo "Waiting for PostgreSQL service..."
python - << 'EOF'
import sys, time
from urllib.parse import urlparse
from sqlalchemy import create_engine, text
from config import settings

parsed = urlparse(settings.DATABASE_URL.replace("postgresql+psycopg://", "postgresql://"))
target_db = parsed.path.lstrip('/')
maintenance_url = f"postgresql+psycopg://{parsed.username}:{parsed.password}@{parsed.hostname}:{parsed.port or 5432}/postgres"

for attempt in range(45):
    try:
        engine = create_engine(maintenance_url, isolation_level="AUTOCOMMIT")
        with engine.connect() as conn:
            exists = conn.execute(text(f"SELECT 1 FROM pg_database WHERE datname = '{target_db}'")).scalar()
            if not exists:
                conn.execute(text(f"CREATE DATABASE \"{target_db}\""))
                print(f"Created database '{target_db}'.")
            else:
                print(f"Database '{target_db}' verified.")
        sys.exit(0)
    except Exception as exc:
        print(f"PostgreSQL not ready yet ({attempt + 1}/45): {exc}")
        time.sleep(2)
print("Timeout waiting for database connection.")
sys.exit(1)
EOF

echo "Verifying target database connection..."
python - << 'EOF'
import sys, time
from sqlalchemy import create_engine, text
from config import settings

for attempt in range(45):
    try:
        engine = create_engine(settings.DATABASE_URL)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("Database connection successfully established.")
        sys.exit(0)
    except Exception as exc:
        print(f"Target DB not ready yet ({attempt + 1}/45): {exc}")
        time.sleep(2)
print("Timeout connecting to target database.")
sys.exit(1)
EOF

echo "Waiting for Redis connection..."
python - << 'EOF'
import sys, time
import redis
from config import settings

for attempt in range(45):
    try:
        r = redis.Redis.from_url(settings.REDIS_URL)
        r.ping()
        print("Redis connection successfully established.")
        sys.exit(0)
    except Exception as exc:
        print(f"Redis not ready yet ({attempt + 1}/45): {exc}")
        time.sleep(2)
print("Timeout waiting for Redis connection.")
sys.exit(1)
EOF

if [ "$1" = "api" ] || [ "$1" = "uvicorn" ]; then
    echo "Applying Alembic database migrations..."
    alembic upgrade head

    echo "Seeding initial demo data..."
    python seed.py

    echo "Starting Uvicorn ASGI server on port 8000..."
    exec uvicorn main:app --host 0.0.0.0 --port 8000

elif [ "$1" = "worker" ]; then
    echo "Waiting for migrations and seed data to complete..."
    python - << 'EOF'
import sys, time
from sqlalchemy import create_engine, text
from config import settings

for attempt in range(45):
    try:
        engine = create_engine(settings.DATABASE_URL)
        with engine.connect() as conn:
            res = conn.execute(text("SELECT to_regclass('csv_import_jobs');")).scalar()
            if res:
                print("Database schema verified for worker.")
                sys.exit(0)
    except Exception:
        pass
    time.sleep(2)
print("Worker: database schema wait timeout.")
sys.exit(1)
EOF
    echo "Starting Dramatiq background worker on queue fastapi..."
    exec dramatiq tasks -Q fastapi --processes 2 --threads 2

else
    exec "$@"
fi
