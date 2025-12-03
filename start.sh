#!/bin/bash
set -e

echo "🔵 Ejecutando migraciones..."
python manage.py migrate --noinput

echo "📦 Recolectando archivos estáticos..."
# Recolectar archivos estáticos con limpieza previa y mostrar información
python manage.py collectstatic --noinput --clear --verbosity 2 || echo "⚠️ Advertencia en collectstatic, continuando..."

echo "🚀 Iniciando servidor..."
exec python -m gunicorn alloffers_project.wsgi:application --bind 0.0.0.0:$PORT

