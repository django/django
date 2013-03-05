"""
40. Empty model tests

These test that things behave sensibly for the rare corner-case of a model with
no fields.
"""

from django.db import models


class Empty(models.Model):
    pass
