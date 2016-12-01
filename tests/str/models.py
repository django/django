"""
Adding __str__() to models

Although it's not a strict requirement, each model should have a ``_str__()``
method to return a "human-readable" representation of the object. Do this not
only for your own sanity when dealing with the interactive prompt, but also
because objects' representations are used throughout Django's
automatically-generated admin.
"""

from django.db import models


class InternationalArticle(models.Model):
    headline = models.CharField(max_length=100)
    pub_date = models.DateTimeField()

    def __str__(self):
        return self.headline
