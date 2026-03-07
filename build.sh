#!/usr/bin/env bash
# Build script for Render deployment
set -o errexit

echo "=== Installing dependencies ==="
pip install -r requirements.txt

echo "=== Collecting static files ==="
python manage.py collectstatic --no-input

echo "=== Running migrations ==="
python manage.py migrate --noinput

echo "=== Creating cache table ==="
python manage.py createcachetable 2>/dev/null || true

echo "=== Loading employees fixture (280 real employees) ==="
python manage.py loaddata core/fixtures/empleados.json || true

echo "=== Loading modules fixture (5373 records - all modules) ==="
python manage.py loaddata core/fixtures/modulos_demo.json || true

echo "=== Running initial setup (seeds use get_or_create, won't duplicate) ==="
python manage.py setup_harmoni --no-input || true

echo "=== Creating demo users ==="
python manage.py create_demo_users || true

echo "=== Build complete ==="
