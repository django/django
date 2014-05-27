"""
Regression tests for initial SQL insertion.
"""

from freedom.db import models


class Simple(models.Model):
    name = models.CharField(max_length=50)
