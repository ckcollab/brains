import json
import time

from django.core.cache import cache
from django.http import JsonResponse, Http404, HttpResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt

from datasets.models import Dataset
from participants.models import Participant
from submissions.models import Submission
from workers.tasks import run


def _yield_submission_output(submission_id):
    # yield something immediately for the connection to start on the cli for nicer printing
    yield json.dumps({"keepalive": "keep the dream alive"})

    last_message_time = time.time()

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
            last_message_time = time.time()
            yield json.dumps({
                "stdout": stdout,
                "stderr": stderr,
            }) + "\r"  # Note we add carriage return at the very end to signify the end of a message, useful
                       # because we're chunking data and sending it in parts, need to know when it ends!

        # Heroku needs keepalive every 30s, so let's do every 25
        if time.time() - last_message_time > 25:
            print "yielding timeout message"
            last_message_time = time.time()
            yield json.dumps({"keepalive": "keep the dream alive"})

        if stdout is not None and "-%-%-%-%-END BRAIN SEQUENCE-%-%-%-%-" in stdout:
            # We don't check for a timeout here... I think that's OK since it's terminated when user view
            # yielding from this generator???
            return
        time.sleep(0.1)


@csrf_exempt
def create(request):
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
        required_fields = ("name", "description", "languages", "datasets", "wait",)
        if any(field not in request.POST for field in required_fields):
            return JsonResponse({
                "error": "missing one of the required fields: %s" % (required_fields,)
            }, status=400)
        if len(request.FILES) == 0:
            return JsonResponse({
                "error": "no file was uploaded?"
            }, status=400)

        # Get dataset
        datasets = []
        if request.POST["datasets"]:
            dataset_names = request.POST.getlist("datasets")
            for name in dataset_names:
                try:
                    datasets.append(Dataset.objects.get(name=name))
                except Dataset.DoesNotExist:
                    return JsonResponse({
                        "error": 'could not find dataset named "%s"' % name
                    }, status=400)

        # Get participant
        participant, _ = Participant.objects.get_or_create(name=request.POST["name"])

        # Save it
        submission = Submission.objects.create(
            participant=participant,
            zip_file=request.FILES["zip_file"],
        )
        for dataset in datasets:
            submission.datasets.add(dataset)

        # Run it (and then return immediately or stream data back)
        run.delay(submission.pk)
        if request.POST["wait"]:
            return StreamingHttpResponse(_yield_submission_output(submission.pk))
        else:
            return HttpResponse()
    return HttpResponse(status=403)


def submission_list(request):
    submissions = Submission.objects.filter()
    if len(submissions) == 0:
        raise Http404()
    return [submission.json_short for submission in submissions]


# @d("/submissions/detail/<int:pk>")
# def submission_detail(request, pk):
#     submission = get_object_or_404(Submission, pk=pk)
#     return submission.json
