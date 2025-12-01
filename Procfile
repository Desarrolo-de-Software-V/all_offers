release: python manage.py migrate
web: python manage.py collectstatic --noinput && python -m gunicorn alloffers_project.wsgi:application --bind 0.0.0.0:$PORT

