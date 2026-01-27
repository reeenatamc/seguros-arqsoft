web: python manage.py migrate --noinput && python manage.py collectstatic --noinput && gunicorn seguros.wsgi --bind 0.0.0.0:$PORT --workers 2 --threads 4 --worker-class gthread --log-file -
