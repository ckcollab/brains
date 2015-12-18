from django.db import models
from django.utils import timezone


class Submission(models.Model):
    description = models.TextField(null=True, blank=True)
    zip_file = models.FileField()
    participant = models.ForeignKey('participants.Participant')
    submitted = models.DateTimeField(default=timezone.now)
    started = models.DateTimeField(null=True, blank=True)
    duration = models.DurationField(null=True, blank=True)
    time_limit_exceeded = models.BooleanField(default=False)
    stdout = models.TextField(null=True, blank=True)
    stderr = models.TextField(null=True, blank=True)
    languages = models.CharField(max_length=64, default='')
    dataset = models.CharField(max_length=64, null=True, blank=True)

    @property
    def json_short(self):
        return {
            "id": self.id,
            "description": self.description,
            "submitter": self.participant.name,
            "dataset": self.dataset,
            "languages": self.languages,
        }

    @property
    def json(self):
        return {

        }


class SubmissionFile(models.Model):
    submission = models.ForeignKey(Submission, related_name="files")
    content = models.TextField()
    name = models.TextField()
