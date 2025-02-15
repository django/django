from thibaud.db import models


class SomeObject(models.Model):
    name = models.CharField(max_length=255)
