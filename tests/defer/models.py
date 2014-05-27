"""
Tests for defer() and only().
"""

from freedom.db import models
from freedom.utils.encoding import python_2_unicode_compatible


class Secondary(models.Model):
    first = models.CharField(max_length=50)
    second = models.CharField(max_length=50)


@python_2_unicode_compatible
class Primary(models.Model):
    name = models.CharField(max_length=50)
    value = models.CharField(max_length=50)
    related = models.ForeignKey(Secondary)

    def __str__(self):
        return self.name


class Child(Primary):
    pass


class BigChild(Primary):
    other = models.CharField(max_length=50)


class ChildProxy(Child):
    class Meta:
        proxy = True
