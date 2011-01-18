"""
Regression tests for initial SQL insertion.
"""

from django.db import models

class Simple(models.Model):
    name = models.CharField(max_length = 50)

