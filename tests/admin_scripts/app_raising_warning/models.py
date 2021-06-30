from mango.core import checks
from mango.db import models


class ModelRaisingMessages(models.Model):
    @classmethod
    def check(self, **kwargs):
        return [checks.Warning('A warning')]
