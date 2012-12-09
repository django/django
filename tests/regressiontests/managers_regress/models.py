"""
Various edge-cases for model managers.
"""

from django.db import models
from django.utils.encoding import python_2_unicode_compatible


class OnlyFred(models.Manager):
    def get_query_set(self):
        return super(OnlyFred, self).get_query_set().filter(name='fred')


class OnlyBarney(models.Manager):
    def get_query_set(self):
        return super(OnlyBarney, self).get_query_set().filter(name='barney')


class Value42(models.Manager):
    def get_query_set(self):
        return super(Value42, self).get_query_set().filter(value=42)


class AbstractBase1(models.Model):
    name = models.CharField(max_length=50)

    class Meta:
        abstract = True

    # Custom managers
    manager1 = OnlyFred()
    manager2 = OnlyBarney()
    objects = models.Manager()


class AbstractBase2(models.Model):
    value = models.IntegerField()

    class Meta:
        abstract = True

    # Custom manager
    restricted = Value42()


# No custom manager on this class to make sure the default case doesn't break.
class AbstractBase3(models.Model):
    comment = models.CharField(max_length=50)

    class Meta:
        abstract = True


@python_2_unicode_compatible
class Parent(models.Model):
    name = models.CharField(max_length=50)

    manager = OnlyFred()

    def __str__(self):
        return self.name


# Managers from base classes are inherited and, if no manager is specified
# *and* the parent has a manager specified, the first one (in the MRO) will
# become the default.
@python_2_unicode_compatible
class Child1(AbstractBase1):
    data = models.CharField(max_length=25)

    def __str__(self):
        return self.data


@python_2_unicode_compatible
class Child2(AbstractBase1, AbstractBase2):
    data = models.CharField(max_length=25)

    def __str__(self):
        return self.data


@python_2_unicode_compatible
class Child3(AbstractBase1, AbstractBase3):
    data = models.CharField(max_length=25)

    def __str__(self):
        return self.data


@python_2_unicode_compatible
class Child4(AbstractBase1):
    data = models.CharField(max_length=25)

    # Should be the default manager, although the parent managers are
    # inherited.
    default = models.Manager()

    def __str__(self):
        return self.data


@python_2_unicode_compatible
class Child5(AbstractBase3):
    name = models.CharField(max_length=25)

    default = OnlyFred()
    objects = models.Manager()

    def __str__(self):
        return self.name


# Will inherit managers from AbstractBase1, but not Child4.
class Child6(Child4):
    value = models.IntegerField()


# Will not inherit default manager from parent.
class Child7(Parent):
    pass
