web: cd src && waitress-serve --port=$PORT --send-bytes=1 wsgi:application
worker: cd src/apps && celery -A workers worker -l INFO --without-gossip --without-mingle --without-heartbeat
