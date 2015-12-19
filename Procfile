web: cd src && waitress-serve --port=$PORT wsgi:application
worker: cd src/apps && celery -A workers worker -l INFO
