from thibaud.db import models


class Story(models.Model):
    title = models.CharField(max_length=10)
