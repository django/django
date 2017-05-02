from __future__ import unicode_literals

from django.db import models


class Movie(models.Model):
    genre = models.CharField(max_length=10,
        choices=(
            (1, 'Action'),
            (2, 'Comedy'),
            (3, 'Drama'),
        )
    )
