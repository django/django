# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models


class SillyModel(models.Model):
    silly_field = models.BooleanField(default=False)
    silly_tribble = models.ForeignKey("migrations.Tribble", models.CASCADE)
    is_trouble = models.BooleanField(default=True)
