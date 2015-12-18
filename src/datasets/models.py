from django.db import models


class Dataset(models.Model):
    name = models.CharField(max_length=64, unique=True)
    file = models.FileField(upload_to="datasets")

    def __unicode__(self):
        return self.name
