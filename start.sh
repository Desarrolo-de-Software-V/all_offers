#!/bin/bash
set -e

echo "🔵 Ejecutando migraciones..."
python manage.py migrate --noinput

echo "📦 Recolectando archivos estáticos..."
python manage.py collectstatic --noinput --clear || echo "⚠️ Advertencia: Algunos archivos estáticos no se pudieron procesar, continuando..."

echo "🚀 Iniciando servidor..."
exec python -m gunicorn alloffers_project.wsgi:application --bind 0.0.0.0:$PORT

