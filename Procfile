web: cd src && waitress-serve --port=$PORT app:d
worker: cd src && celery -A workers worker -l INFO
