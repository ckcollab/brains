import uuid

from django.db import models
from s3direct.fields import S3DirectField


class Dataset(models.Model):
    name = models.CharField(max_length=64, unique=True)
    file = S3DirectField(dest="datasets")
    uuid = models.UUIDField(default=uuid.uuid4)

    def __unicode__(self):
        return self.name
