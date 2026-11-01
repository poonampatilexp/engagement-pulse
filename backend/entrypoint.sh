#!/bin/sh
set -e

echo "Waiting for PostgreSQL database at ${DB_HOST:-db}:${DB_PORT:-5432}..."
python - << 'EOF'
import os, sys, time
import psycopg

db_name = os.getenv('DB_NAME', 'engagement_pulse')
db_user = os.getenv('DB_USER', 'pulse_user')
db_password = os.getenv('DB_PASSWORD', 'pulse_password')
db_host = os.getenv('DB_HOST', 'db')
db_port = os.getenv('DB_PORT', '5432')

for attempt in range(45):
    try:
        conn = psycopg.connect(
            dbname=db_name,
            user=db_user,
            password=db_password,
            host=db_host,
            port=db_port,
            connect_timeout=3
        )
        conn.close()
        print("Database connection successfully established.")
        sys.exit(0)
    except Exception as exc:
        print(f"PostgreSQL not ready yet ({attempt + 1}/45): {exc}")
        time.sleep(2)
print("Timeout waiting for database connection.")
sys.exit(1)
EOF

if [ "$1" = "daphne" ]; then
    echo "Applying database migrations..."
    python manage.py migrate --noinput

    echo "Seeding initial demo data..."
    python manage.py seed_data

    echo "Starting Daphne ASGI server on port 8000..."
    exec daphne -b 0.0.0.0 -p 8000 config.asgi:application

elif [ "$1" = "worker" ]; then
    echo "Waiting for migrations and seed data to complete..."
    python - << 'EOF'
import os, sys, time
import psycopg

db_name = os.getenv('DB_NAME', 'engagement_pulse')
db_user = os.getenv('DB_USER', 'pulse_user')
db_password = os.getenv('DB_PASSWORD', 'pulse_password')
db_host = os.getenv('DB_HOST', 'db')
db_port = os.getenv('DB_PORT', '5432')

for attempt in range(45):
    try:
        conn = psycopg.connect(
            dbname=db_name,
            user=db_user,
            password=db_password,
            host=db_host,
            port=db_port,
            connect_timeout=3
        )
        cur = conn.cursor()
        # Verify csv_import_jobs table exists
        cur.execute("SELECT to_regclass('csv_import_jobs');")
        res = cur.fetchone()
        conn.close()
        if res and res[0]:
            print("Database schema verified for worker.")
            sys.exit(0)
    except Exception:
        pass
    time.sleep(2)
print("Worker: database schema wait timeout.")
sys.exit(1)
EOF
    echo "Starting Dramatiq background worker..."
    exec python manage.py rundramatiq --processes 2 --threads 2

else
    exec "$@"
fi
