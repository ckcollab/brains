import os
import shutil
import signal
import subprocess
import sys
import time
import traceback
import yaml

from celery import task
from django.core.cache import cache
from threading import Thread
from Queue import Queue, Empty
from zipfile import ZipFile

from datasets.models import Dataset
from submissions.models import Submission


##############################################################################
# Helpers
ON_POSIX = 'posix' in sys.builtin_module_names
CONFIG_FILE = "brains.yaml"
DATASET_CACHE_DIR = '/tmp/brains_temp_dataset_cache_storage/'
SUBMISSION_TEMP_STORAGE_DIR = '/tmp/brains_temp_submission_storage/'


def _enqueue_output(buffer, queue):
    for buffer_string in iter(buffer.readline, b''):
    #for buffer_string in iter(lambda: buffer.read(128), b''):  # just in case we want to read without newlines
        queue.put(buffer_string)
    buffer.close()


class BufferMonitor(object):
    """Keeps track of stdout/stderr for running tasks, puts the data in a cache until it's removed, then replaces
    it with new data from the buffer"""
    def __init__(self, buffer, cache_key):
        self.queue = Queue()
        self.thread = Thread(target=_enqueue_output, args=(buffer, self.queue))
        self.thread.daemon = True  # thread dies with the program
        self.thread.start()
        self.buffer = ''
        self.cache_key = cache_key

    def set_cache_if_cache_clear(self):
        # Check if cache is empty, if so we can put something there!
        cached_stdout = cache.get(self.cache_key)
        if cached_stdout is None:
            cache.set(self.cache_key, self.buffer)
            self.buffer = ''

    def check_queue_then_cache(self):
        try:
            # We want to use the short timeouts here to check each buffer. if it was only one buffer a
            # higher timeout would be fine
            self.buffer += self.queue.get(timeout=.1)
        except Empty:
            pass
        else:
            self.set_cache_if_cache_clear()

    def wait_until_cache_clear(self):
        # timeout is 10 seconds to wait for cache to clear after program has exited
        timeout = 10
        start = time.time()

        # clear queue
        while self.queue.qsize() > 0:
            self.check_queue_then_cache()
            if (time.time() - start) > timeout:
                raise Exception("Timed out clearing queue???")

        # clear buffer
        while self.buffer:
            self.set_cache_if_cache_clear()
            time.sleep(1)  # long sleeps since the other side is prob dead not worth thrashing
            if (time.time() - start) > timeout:
                # No one is reading from this buffer, they left?!
                return


class ExecutionTimeLimitExceeded(Exception):
    pass


def _alarm_handler(signum, frame):
    raise ExecutionTimeLimitExceeded


def _extract_submission_return_config(submission, dataset):
    """returns the configuration for the submission"""
    if os.path.exists(SUBMISSION_TEMP_STORAGE_DIR):
        # Remove temp storage so we don't run out of space on the server or something
        shutil.rmtree(SUBMISSION_TEMP_STORAGE_DIR)
    os.mkdir(SUBMISSION_TEMP_STORAGE_DIR)
    zip_file = ZipFile(submission.zip_file)
    zip_file.extractall(SUBMISSION_TEMP_STORAGE_DIR)

    if dataset:
        print "submission dataset: ", dataset.name
        dataset_path = os.path.join(DATASET_CACHE_DIR, str(dataset.uuid))
        if not os.path.exists(dataset_path):
            zip_file = ZipFile(dataset.file)
            zip_file.extractall(dataset_path)

    config_path = os.path.join(SUBMISSION_TEMP_STORAGE_DIR, CONFIG_FILE)
    return yaml.load(open(config_path).read(), Loader=yaml.loader.BaseLoader)


#def


##############################################################################
# The big kahuna, the submission runner
@task
def run(submission_id, dataset_id):
    try:
        submission = Submission.objects.get(pk=submission_id)
    except Submission.DoesNotExist:
        cache.set("submission-%s-stderr" % submission_id, "Could not find a submission with this ID (%s)" % submission_id)
        return

    try:
        if dataset_id:
            dataset = Dataset.objects.get(pk=dataset_id)
        else:
            dataset = None
    except Submission.DoesNotExist:
        cache.set("submission-%s-stderr" % submission_id, "Could not find a dataset with this ID (%s)" % dataset_id)
        return

    config = _extract_submission_return_config(submission, dataset)
    process_args = config["run"]

    # Make python not buffer output otherwise user may think nothing is happening
    os.environ.setdefault('PYTHONUNBUFFERED', '1')

    # Replace dataset path
    if submission.dataset:
        dataset_path = os.path.join(DATASET_CACHE_DIR, str(submission.dataset.uuid))
        process_args = process_args.replace("$INPUT", dataset_path)
        submission_name_centered = (" dataset: %s " % submission.dataset.name).center(80, "=")
        cache.set("submission-%s-stdout" % submission_id, "\n%s\n\n\r" % submission_name_centered)
    else:
        no_dataset_msg_centered = " no dataset used ".center(80, "=")
        cache.set("submission-%s-stdout" % submission_id, "\n%s\n\n\r" % no_dataset_msg_centered)

    print "Running submission (%s) with args %s" % (submission_id, process_args)

    signal.signal(signal.SIGALRM, _alarm_handler)
    signal.alarm(60 * 10)  # require an "alarm" return signal within 10 min or force close

    try:
        process = subprocess.Popen(
            process_args.split(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0,
            cwd=SUBMISSION_TEMP_STORAGE_DIR
        )
        stdout_monitor = BufferMonitor(process.stdout, "submission-%s-stdout" % submission_id)
        stderr_monitor = BufferMonitor(process.stderr, "submission-%s-stderr" % submission_id)

        exit_code = None
        while exit_code is None:
            stdout_monitor.check_queue_then_cache()
            stderr_monitor.check_queue_then_cache()
            exit_code = process.poll()

    except (ValueError, OSError):
        pass  # tried to communicate with dead process

    except ExecutionTimeLimitExceeded:
        cache.set("submission-%s-stderr" % submission_id, "Time limit exceeded!")
        process.kill()

    except Exception:
        # Catch any other exceptions and pass them back home
        exception_details = traceback.format_exc()
        cache.set("submission-%s-stderr" % submission_id, exception_details)

    finally:
        # Reset the alarm, 0 means no "alarm" signal is required to respond
        signal.alarm(0)

    # Sometimes app doesn't finish clearing output so let's clean up the buffers
    stderr_monitor.wait_until_cache_clear()  # stderr first so stdout end message arrives last!
    # Put our EOF message at the end of the queue so it will for sure send last
    stdout_monitor.queue.put("-%-%-%-%-END BRAIN SEQUENCE-%-%-%-%-")
    stdout_monitor.wait_until_cache_clear()
