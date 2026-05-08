web: gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 2 --threads 4
worker: python manage.py qcluster
beat: python manage.py qbeat
