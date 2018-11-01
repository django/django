from django.db import models


class Thing(models.Model):
    num = models.IntegerField()

    def __str__(self):
        return "Thing %d" % self.num
