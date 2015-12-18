from django.db import models


class Job(models.Model):
    submission = models.ForeignKey("submissions.Submission", related_name="job")
