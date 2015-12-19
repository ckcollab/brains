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

DATABASE_URL = os.environ.get("DATABASE_URL", None)
ON_HEROKU = DATABASE_URL
if DATABASE_URL:
    import dj_database_url
    settings.DATABASES = {'default': dj_database_url.parse(DATABASE_URL)}
if ON_HEROKU:
    settings.DEBUG = False
    settings.LOGGING = {
        'version': 1,
        'disable_existing_loggers': True,
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
            },
        },
        'loggers': {
            'django': {
                'handlers': ['console'],
                'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
            },
        },
    }

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


##############################################################################
# Helpers
def _yield_submission_output(submission_id):
    yield ""  # yield something immediately for the connection to start on the cli for nicer printing

    while True:
        stdout = cache.get("submission-%s-stdout" % submission_id)
        stderr = cache.get("submission-%s-stderr" % submission_id)
        # After reading let's clear the cache and that lets the runner know to fill the buffer again
        cache.delete_many(
            ("submission-%s-stdout" % submission_id, "submission-%s-stderr" % submission_id)
        )

        # Don't want someone accidentally breaking our format where each message ends with \r, so get rid of them
        # The \r signifies the end of a message (so messages aren't merged together as they're streamed/chunked)
        if stdout:
            stdout = stdout.replace("\r", "")
        if stderr:
            stderr = stderr.replace("\r", "")

        if stdout or stderr:
            yield json.dumps({
                "stdout": stdout,
                "stderr": stderr,
            }) + "\r"  # Note we add carriage return at the very end to signify the end of a message, useful
                       # because we're chunking data and sending it in parts, need to know when it ends!

        #print "Reading!!!!!", stdout

        if stdout is not None and "-%-%-%-%-END BRAIN SEQUENCE-%-%-%-%-" in stdout:
            # We don't check for a timeout here... I think that's OK since it's terminated when user view
            # yielding from this generator???
            return
        time.sleep(0.1)


##############################################################################
# Views
#
# Have to do model imports here AFTER d settings
from datasets.models import Dataset
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
    dataset - Name of dataset to use
    submission - Zip file containing submission contents
    wait -
    """
    if request.method == "POST":
        # Validate
        required_fields = ("name", "description", "languages", "dataset", "wait",)
        if any(field not in request.POST for field in required_fields):
            return JsonResponse({
                "error": "missing one of the required fields: %s" % (required_fields,)
            }, status=400)
        if len(request.FILES) == 0:
            return JsonResponse({
                "error": "no file was uploaded?"
            }, status=400)

        # Get dataset
        print "got dataset", request.POST["dataset"]

        dataset = None
        if request.POST["dataset"]:
            try:
                dataset = Dataset.objects.get(name=request.POST["dataset"])
            except Dataset.DoesNotExist:
                return JsonResponse({
                    "error": 'could not find dataset named "%s"' % request.POST["dataset"]
                }, status=400)

        # Get participant
        participant, _ = Participant.objects.get_or_create(name=request.POST["name"])

        # Save it
        submission = Submission.objects.create(
            participant=participant,
            zip_file=request.FILES["zip_file"],
            dataset=dataset,
        )

        # Run it (and then return immediately or stream data back)
        run.delay(submission.pk, submission.dataset.pk if submission.dataset else None)
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
