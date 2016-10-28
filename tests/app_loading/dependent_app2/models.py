from django.apps import apps
from django.db import models

base_model = apps.get_model('dependent_app1', 'BaseModel')


class DependentModel(models.Model):
    # At some point, this model will need base_model at import time
    pass
