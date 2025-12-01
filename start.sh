#!/bin/bash
set -e

echo "🔵 Ejecutando migraciones..."
python manage.py migrate --noinput

echo "📦 Recolectando archivos estáticos..."
python manage.py collectstatic --noinput

echo "🚀 Iniciando servidor..."
exec python -m gunicorn alloffers_project.wsgi:application --bind 0.0.0.0:$PORT

