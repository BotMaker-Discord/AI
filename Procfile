web: gunicorn server:app --bind 0.0.0.0:${PORT:-8080} --workers 2 --threads 2 --timeout 120 --preload --access-logfile - --error-logfile -
