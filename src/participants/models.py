import uuid

from django.db import models


class Participant(models.Model):
    name = models.CharField(max_length=64)
    secret = models.UUIDField(default=uuid.uuid4, editable=False)

    def __unicode__(self):
        return self.name
