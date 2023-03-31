# amodels.py
from django.db import models
from django.conf import settings

class A(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='objects_a')
