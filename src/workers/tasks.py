import itertools
import signal
import subprocess
import sys
import time

from celery import task
from django.core.cache import cache
from threading import Thread
from Queue import Queue, Empty

from submissions.models import Submission


##############################################################################
# Helpers
ON_POSIX = 'posix' in sys.builtin_module_names


def enqueue_output(buffer, queue):
    for buffer_string in iter(buffer.readline, b''):
    # for buffer_string in iter(lambda: buffer.read(128), b''):  # just in case we want to read without newlines
        queue.put(buffer_string)
    buffer.close()


class BufferMonitor(object):
    def __init__(self, buffer):
        self.queue = Queue()
        self.thread = Thread(target=enqueue_output, args=(buffer, self.queue))
        self.thread.daemon = True  # thread dies with the program
        self.thread.start()


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

    signal.signal(signal.SIGALRM, alarm_handler)
    signal.alarm(60 * 10)  # require an "alarm" return signal within 10 min or force close

    stdout_buffer = ""
    stderr_buffer = ""

    process_args = ["python", "writes_to_stderr.py"]
    # process_args = ["ping", "google.com"]

    # In python we don't automatically flush the buffers, so if we se a python arg put a -u after it
    for index, arg in enumerate(process_args):
        if arg == "python":
            process_args.insert(index - 1, "-u")  # insert the autoflush flag

    process = subprocess.Popen(
        process_args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=0,
    )
    stdout_monitor = BufferMonitor(process.stdout)
    stderr_monitor = BufferMonitor(process.stderr)
    exit_code = None

    try:
        while exit_code is None:
            try:
                # stdout = stdout_monitor.queue.get_nowait()
                stdout = stdout_monitor.queue.get(timeout=.1)
                # stderr = stderr_monitor.queue.get_nowait()
                stderr = stderr_monitor.queue.get(timeout=.1)
            except Empty:
                pass
            else:
                stdout_buffer += stdout if stdout else ''
                stderr_buffer += stderr if stderr else ''

                # Check if cache is empty, if so we can put something there!
                cached_stdout = cache.get("submission-%s-stdout" % submission_id)
                if cached_stdout is None:
                    cache.set("submission-%s-stdout" % submission_id, stdout_buffer)
                    cache.set("submission-%s-stderr" % submission_id, stderr_buffer)
                    stdout_buffer = stderr_buffer = ""
            exit_code = process.poll()
    except (ValueError, OSError):
        pass  # tried to communicate with dead process
    except ExecutionTimeLimitExceeded:
        cache.set("submission-%s-stderr" % submission_id, "Time limit exceeded!")
        process.kill()
    finally:
        # Reset the alarm, 0 means no "alarm" signal is required to respond
        signal.alarm(0)

    cache.set("submission-%s-stdout" % submission_id, "-%-%-%-%-END BRAIN SEQUENCE-%-%-%-%-")
