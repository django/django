from thibaud.core import checks
from thibaud.db import models


class ModelRaisingMessages(models.Model):
    @classmethod
    def check(self, **kwargs):
        return [checks.Warning("A warning")]
