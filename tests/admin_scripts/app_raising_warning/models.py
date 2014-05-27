# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from freedom.core import checks
from freedom.db import models


class ModelRaisingMessages(models.Model):
    @classmethod
    def check(self, **kwargs):
        return [
            checks.Warning(
                'A warning',
                hint=None,
            ),
        ]
