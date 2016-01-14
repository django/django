from django.db import models
from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class Thing(models.Model):
    num = models.IntegerField()

    def __str__(self):
        return "Thing %d" % self.num
