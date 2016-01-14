import uuid

from django.contrib.auth.models import AbstractUser
from django.contrib.auth.tests.custom_user import RemoveGroupsAndPermissions
from django.db import models

with RemoveGroupsAndPermissions():
    class UUIDUser(AbstractUser):
        """A user with a UUID as primary key"""
        id = models.UUIDField(default=uuid.uuid4, primary_key=True)
