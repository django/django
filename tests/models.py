from uuid import uuid4

from django.db import models


class TestUUIDModel(models.Model):
    """
    Simple model with UUIDField as primary key for tests.
    """

    id = models.UUIDField(primary_key=True, default=uuid4)
    name = models.CharField(max_length=255)
