from base import *


DEBUG = False

ALLOWED_HOSTS = ["*"]

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "afaefawe23af")
assert SECRET_KEY, "Set your DJANGO_SECRET_KEY env var"

# Celery
BROKER_URL = os.environ.get('CLOUDAMQP_URL', None)
# BROKER_URL = os.environ.get("RABBITMQ_BIGWIG_URL", None)

#assert BROKER_URL, "Celery BROKER_URL env var missing!"

# Memcached
CACHES = {
    'default': {
        'BACKEND': 'django_bmemcached.memcached.BMemcached',
        'LOCATION': os.environ.get('MEMCACHEDCLOUD_SERVERS', '').split(','),
        'OPTIONS': {
            'username': os.environ.get('MEMCACHEDCLOUD_USERNAME'),
            'password': os.environ.get('MEMCACHEDCLOUD_PASSWORD')
        }
    }
}
