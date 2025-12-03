#!/bin/bash
set -e

echo "🔵 Ejecutando migraciones..."
python manage.py migrate --noinput

echo "📦 Recolectando archivos estáticos..."
# Recolectar archivos estáticos con limpieza previa y mostrar información
# Deshabilitar set -e temporalmente para collectstatic
set +e
python manage.py collectstatic --noinput --clear --verbosity 2
COLLECTSTATIC_EXIT=$?
set -e
if [ $COLLECTSTATIC_EXIT -ne 0 ]; then
    echo "⚠️ Advertencia: collectstatic tuvo problemas (código: $COLLECTSTATIC_EXIT), pero continuando..."
fi

echo "🚀 Iniciando servidor..."
exec python -m gunicorn alloffers_project.wsgi:application --bind 0.0.0.0:$PORT

