import signal
import subprocess
import sys
import time

from celery import task
from django.core.cache import cache
from threading  import Thread
from Queue import Queue, Empty

from submissions.models import Submission


##############################################################################
# Helpers
ON_POSIX = 'posix' in sys.builtin_module_names


def enqueue_output(out, queue):
    for line in iter(out.readline, b''):
        queue.put(line)
    out.close()


class ExecutionTimeLimitExceeded(Exception):
    pass


def alarm_handler(signum, frame):
    raise ExecutionTimeLimitExceeded


##############################################################################
# The big kahuna, the submission runner
@task
def run(submission_id):
    try:
        submission = Submission.objects.get(pk=submission_id)
    except Submission.DoesNotExist:
        cache.set("submission-%s-stderr" % submission_id, "Could not find a task with this ID (%s)" % submission_id)
        return

    # for i in range(100):
    #     # Check if cache is empty, if so we can put something there!
    #     current_stdout = cache.get("submission-%s-stdout" % submission_id)
    #     if current_stdout is None:
    #         cache.set("submission-%s-stdout" % submission_id, "weeeeeeeeeeeeeeeee!!!\n")
    #     time.sleep(0.1)


    signal.signal(signal.SIGALRM, alarm_handler)
    signal.alarm(60 * 10)  # require an "alarm" return signal within 10 min or force close



    stdout_buffer = ""
    stderr_buffer = ""

    print "here at least"
    # cmd = subprocess.Popen(["ping", "google.com"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    # for stdout, stderr in zip(cmd.stdout, cmd.stderr):
    #     print "Stdout:", stdout
    #
    #     stdout_buffer += stdout
    #     stderr_buffer += stderr
    #
    #     # Check if cache is empty, if so we can put something there!
    #     cached_stdout = cache.get("submission-%s-stdout" % submission_id)
    #     if cached_stdout is None:
    #         cache.set("submission-%s-stdout" % submission_id, stdout)
    #         cache.set("submission-%s-stderr" % submission_id, stderr)
    #         stdout_buffer = stderr_buffer = None
    #
    #     time.sleep(0.1)

    process = subprocess.Popen(["ping", "google.com"], stdout=subprocess.PIPE, bufsize=1, close_fds=ON_POSIX)
    q = Queue()
    t = Thread(target=enqueue_output, args=(process.stdout, q))
    t.daemon = True  # thread dies with the program
    t.start()
    exit_code = None


    #cmd = subprocess.Popen(["ping", "google.com"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    #for stdout, stderr in zip(cmd.stdout, cmd.stderr):

    # print "Stdout:", stdout
    #
    #
    # # Check if cache is empty, if so we can put something there!
    # cached_stdout = cache.get("submission-%s-stdout" % submission_id)
    # if cached_stdout is None:
    #     cache.set("submission-%s-stdout" % submission_id, stdout)
    #     cache.set("submission-%s-stderr" % submission_id, stderr)
    #     stdout_buffer = stderr_buffer = None

    try:
        while exit_code is None:
            try:
                stdout = q.get_nowait() # or q.get(timeout=.1)
            except Empty:
                pass
            else:
                stdout_buffer += stdout

                # Check if cache is empty, if so we can put something there!
                cached_stdout = cache.get("submission-%s-stdout" % submission_id)
                if cached_stdout is None:
                    cache.set("submission-%s-stdout" % submission_id, stdout_buffer)
                    cache.set("submission-%s-stderr" % submission_id, stderr_buffer)
                    stdout_buffer = stderr_buffer = ""
            #stderr_buffer += stderr
            time.sleep(0.1)
            exit_code = process.poll()
    except (ValueError, OSError):
        pass  # tried to communicate with dead process
    except ExecutionTimeLimitExceeded:
        cache.set("submission-%s-stderr" % submission_id, "Time limit exceeded!")
        process.kill()
    finally:
        # Reset the alarm, 0 means no "alarm" signal is required to respond
        signal.alarm(0)

    # get submission dataset
    # does it exist in some cache?
    # fetch if not
    # get script
    # replace $INPUT with proper folder
    # run that WITH DEMOTE! https://github.com/codalab/codalab/blob/master/codalab/codalabtools/compute/worker.py#L345
    # pipe stdout and stderr




    # changes we'll have to make to system
    # create some low user










    cache.set("submission-%s-stdout" % submission_id, "-%-%-%-%-END BRAIN SEQUENCE-%-%-%-%-")


    #call(config["run"].split())