from django.db import models


class Submission(models.Model):
    zip = models.FileField()
    participant = models.ForeignKey('participants.Participant')


class SubmissionFile(models.Model):
    content = models.TextField()
    name = models.TextField()
