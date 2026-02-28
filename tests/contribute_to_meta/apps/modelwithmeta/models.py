from django.db import models

from ...fields import ConstraintField


class Model(models.Model):
    class Meta:
        constraints = []

    field = ConstraintField(max_length=10)
