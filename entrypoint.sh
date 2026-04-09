#!/bin/sh
set -e

echo "Waiting for database..."

while ! python -c "
import socket
s = socket.socket()
s.connect(('db', 5432))
s.close()
" 2>/dev/null; do
  sleep 1
done

echo "Database is up"

echo "Running migrations..."
alembic upgrade head

echo "Starting app..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000