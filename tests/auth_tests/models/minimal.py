from django.contrib.auth.models import User
from django.db import models


class MinimalUser(models.Model):
    REQUIRED_FIELDS = ()
    USERNAME_FIELD = 'id'


class CustomModel(models.Model):
    # Used by with_perm() tests.
    user = models.ForeignKey(User, on_delete=models.CASCADE)
