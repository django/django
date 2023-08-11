from django.db import models

from .fields import ConstraintField


class ModelA(models.Model):
    field = ConstraintField(max_length=10)


class ModelC(models.Model):
    class Meta:
        constraints = []

    field = ConstraintField(max_length=10)
