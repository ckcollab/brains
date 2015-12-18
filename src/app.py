import json
import os
import time

from django.core.cache import cache
from django.http import StreamingHttpResponse, JsonResponse
from importd import d


##############################################################################
# Settings
d(
    INSTALLED_APPS=[
        # 3rd party
        "storages",
        #"djcelery",

        # Our apps
        "participants",
        "submissions",
        "datasets",
        "workers",
    ],
    MIDDLEWARE_CLASSES=[
        'django.contrib.sessions.middleware.SessionMiddleware',
        "django.contrib.messages.middleware.MessageMiddleware"
    ],
    DEFAULT_FILE_STORAGE='storages.backends.s3boto.S3BotoStorage',
    AWS_ACCESS_KEY_ID=os.environ.get("AWS_ACCESS_KEY_ID"),
    AWS_SECRET_ACCESS_KEY=os.environ.get("AWS_SECRET_ACCESS_KEY"),
    AWS_STORAGE_BUCKET_NAME=os.environ.get("AWS_STORAGE_BUCKET_NAME"),
    BROKER_URL=os.environ.get('CLOUDAMQP_URL', None),
    #CELERY_RESULT_BACKEND = 'djcelery.backends.database.DatabaseBackend'
    # mounts={
    #     "my_reusable_blog": "/blog/", # or /myblog/
    # }
)

from django.conf import settings


MEMCACHEDCLOUD_SERVERS = os.environ.get('MEMCACHEDCLOUD_SERVERS')

if MEMCACHEDCLOUD_SERVERS:
    # With caching
    settings.CACHES = {
        'default': {
            'BACKEND': 'django_bmemcached.memcached.BMemcached',
            'LOCATION': MEMCACHEDCLOUD_SERVERS.split(','),
            'OPTIONS': {
                'username': os.environ.get('MEMCACHEDCLOUD_USERNAME'),
                'password': os.environ.get('MEMCACHEDCLOUD_PASSWORD')
            }
        }
    }
else:
    settings.CACHES = {
        'default': {
            'BACKEND': 'django_bmemcached.memcached.BMemcached',
            'LOCATION': '127.0.0.1:11211',
        }
    }

#settings.CELERY_RESULT_BACKEND = 'djcelery.backends.cache:CacheBackend'


##############################################################################
# Helpers
def _yield_submission_output(submission_id):
    while True:
        stdout = cache.get("submission-%s-stdout" % submission_id)
        stderr = cache.get("submission-%s-stderr" % submission_id)
        # After reading let's clear the cache and that lets the runner know to fill the buffer again
        cache.delete_many(
            ("submission-%s-stdout" % submission_id, "submission-%s-stderr" % submission_id)
        )

        # Don't want someone accidentally breaking our format where each messag ends with \r, so get rid of them
        if stdout:
            stdout = stdout.replace("\r", "")
        if stderr:
            stderr = stderr.replace("\r", "")

        if stdout or stderr:
            yield json.dumps({
                "stdout": stdout,
                "stderr": stderr,
            }) + "\r"
        if stdout is not None and "-%-%-%-%-END BRAIN SEQUENCE-%-%-%-%-" in stdout:
            # We don't check for a timeout here... I think that's OK since it's terminated when user view
            # yielding from this generator???
            return
        time.sleep(0.1)


##############################################################################
# Views
#
# Have to do model imports here AFTER d settings
from participants.models import Participant
from submissions.models import Submission
from workers.tasks import run


@d("/")
def index(request):
    return d.HttpResponse("Hello, I process submissions!")


# @d("/participant/create")
# def register(request):
#     """POST
#
#     name - Your participation name
#     """
#     pass


@d("/submissions/create")
def submit(request):
    """Post data like

    name - Name of submitter
    description -
    languages -
    dataset -
    submission - Zip file containing submission contents
    wait -
    """
    if request.method == "POST":
        required_fields = ("name", "description", "languages", "dataset", "wait",)
        if any(field not in request.POST for field in required_fields):
            return JsonResponse({
                "error": "Missing one of the required fields: %s" % (required_fields,)
            }, status=400)
        if len(request.FILES) == 0:
            return JsonResponse({
                "error": "No file was uploaded?"
            }, status=400)

        participant, _ = Participant.objects.get_or_create(name=request.POST["name"])
        submission = Submission.objects.create(
            participant=participant,
            zip_file=request.FILES["zip_file"],
        )

        run.delay(submission.pk)
        if request.POST["wait"]:
            return StreamingHttpResponse(_yield_submission_output(submission.pk))
        else:
            return d.HttpResponse()
    return d.HttpResponse(status=403)


@d("/submissions/list/")
def submission_list(request):
    submissions = Submission.objects.filter()
    if len(submissions) == 0:
        raise d.Http404()
    return [submission.json_short for submission in submissions]


@d("/submissions/detail/<int:pk>")
def submission_detail(request, pk):
    submission = d.get_object_or_404(Submission, pk=pk)
    return submission.json


if __name__ == "__main__":

    d.main()
