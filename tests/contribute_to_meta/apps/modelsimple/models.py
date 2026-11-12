from django.db import models

from ...fields import ConstraintField


class Model(models.Model):
    field = ConstraintField(max_length=10)
