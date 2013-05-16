from __future__ import unicode_literals

from django.db import models
from django.utils import six


# The models definitions below used to crash. Generating models dynamically
# at runtime is a bad idea because it pollutes the app cache. This doesn't
# integrate well with the test suite but at least it prevents regressions.


class CustomBaseModel(models.base.ModelBase):
    pass


class MyModel(six.with_metaclass(CustomBaseModel, models.Model)):
        """Model subclass with a custom base using six.with_metaclass."""


if not six.PY3:
    class MyModel(models.Model):
        """Model subclass with a custom base using __metaclass__."""
        __metaclass__ = CustomBaseModel
