from django.db import models


class Guitarist(models.Model):
    name = models.CharField(max_length=50)
    slug = models.CharField(max_length=50)

    @models.permalink
    def url(self):
        "Returns the URL for this guitarist."
        return ('guitarist_detail', [self.slug])
