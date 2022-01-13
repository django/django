from django.core import checks
from django.db import models


class ModelRaisingMessages(models.Model):
    @classmethod
    def check(self, **kwargs):
        return [
            checks.Warning('First warning', hint='Hint', obj=ModelRaisingMessages),
            checks.Warning('Second warning', obj=ModelRaisingMessages),
            checks.Error('An error', hint='Error hint'),
        ]
