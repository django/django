import datetime

from django.db import DJANGO_VERSION_PICKLE_KEY, models
from django.utils import six
from django.utils.translation import ugettext_lazy as _


def standalone_number():
    return 1


class Numbers(object):
    @staticmethod
    def get_static_number():
        return 2


class PreviousDjangoVersionQuerySet(models.QuerySet):
    def __getstate__(self):
        state = super(PreviousDjangoVersionQuerySet, self).__getstate__()
        state[DJANGO_VERSION_PICKLE_KEY] = '1.0'
        return state


class MissingDjangoVersionQuerySet(models.QuerySet):
    def __getstate__(self):
        state = super(MissingDjangoVersionQuerySet, self).__getstate__()
        del state[DJANGO_VERSION_PICKLE_KEY]
        return state


class Group(models.Model):
    name = models.CharField(_('name'), max_length=100)
    objects = models.Manager()
    previous_django_version_objects = PreviousDjangoVersionQuerySet.as_manager()
    missing_django_version_objects = MissingDjangoVersionQuerySet.as_manager()


class Event(models.Model):
    title = models.CharField(max_length=100)
    group = models.ForeignKey(Group, models.CASCADE)


class Happening(models.Model):
    when = models.DateTimeField(blank=True, default=datetime.datetime.now)
    name = models.CharField(blank=True, max_length=100, default="test")
    number1 = models.IntegerField(blank=True, default=standalone_number)
    if six.PY3:
        # default serializable on Python 3 only
        number2 = models.IntegerField(blank=True, default=Numbers.get_static_number)


class Container(object):
    # To test pickling we need a class that isn't defined on module, but
    # is still available from app-cache. So, the Container class moves
    # SomeModel outside of module level
    class SomeModel(models.Model):
        somefield = models.IntegerField()


class M2MModel(models.Model):
    groups = models.ManyToManyField(Group)
