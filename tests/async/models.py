from mango.db import models


class SimpleModel(models.Model):
    field = models.IntegerField()
