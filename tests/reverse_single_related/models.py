from django.db import models


class SourceManager(models.Manager):
    def get_query_set(self):
        return super(SourceManager, self).get_query_set().filter(is_public=True)

class Source(models.Model):
    is_public = models.BooleanField()
    objects = SourceManager()

class Item(models.Model):
    source = models.ForeignKey(Source)
