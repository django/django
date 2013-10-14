from django.db import models


class SourceManager(models.Manager):
    def get_queryset(self):
        return super(SourceManager, self).get_queryset().filter(is_public=True)

class Source(models.Model):
    is_public = models.BooleanField(default=False)
    objects = SourceManager()

class Item(models.Model):
    source = models.ForeignKey(Source)
