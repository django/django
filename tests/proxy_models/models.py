"""
By specifying the 'proxy' Meta attribute, model subclasses can specify that
they will take data directly from the table of their base class table rather
than using a new table of their own. This allows them to act as simple proxies,
providing a modified interface to the data from the base class.
"""
from django.db import models
from django.utils.encoding import python_2_unicode_compatible


# A couple of managers for testing managing overriding in proxy model cases.


class PersonManager(models.Manager):
    def get_queryset(self):
        return super(PersonManager, self).get_queryset().exclude(name="fred")


class SubManager(models.Manager):
    def get_queryset(self):
        return super(SubManager, self).get_queryset().exclude(name="wilma")


@python_2_unicode_compatible
class Person(models.Model):
    """
    A simple concrete base class.
    """
    name = models.CharField(max_length=50)

    objects = PersonManager()

    def __str__(self):
        return self.name


class Abstract(models.Model):
    """
    A simple abstract base class, to be used for error checking.
    """
    data = models.CharField(max_length=10)

    class Meta:
        abstract = True


class MyPerson(Person):
    """
    A proxy subclass, this should not get a new table. Overrides the default
    manager.
    """
    class Meta:
        proxy = True
        ordering = ["name"]
        permissions = (
            ("display_users", "May display users information"),
        )

    objects = SubManager()
    other = PersonManager()

    def has_special_name(self):
        return self.name.lower() == "special"


class ManagerMixin(models.Model):
    excluder = SubManager()

    class Meta:
        abstract = True


class OtherPerson(Person, ManagerMixin):
    """
    A class with the default manager from Person, plus an secondary manager.
    """
    class Meta:
        proxy = True
        ordering = ["name"]


class StatusPerson(MyPerson):
    """
    A non-proxy subclass of a proxy, it should get a new table.
    """
    status = models.CharField(max_length=80)

# We can even have proxies of proxies (and subclass of those).


class MyPersonProxy(MyPerson):
    class Meta:
        proxy = True


class LowerStatusPerson(MyPersonProxy):
    status = models.CharField(max_length=80)


@python_2_unicode_compatible
class User(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class UserProxy(User):
    class Meta:
        proxy = True


class UserProxyProxy(UserProxy):
    class Meta:
        proxy = True

# We can still use `select_related()` to include related models in our querysets.


class Country(models.Model):
    name = models.CharField(max_length=50)


@python_2_unicode_compatible
class State(models.Model):
    name = models.CharField(max_length=50)
    country = models.ForeignKey(Country)

    def __str__(self):
        return self.name


class StateProxy(State):
    class Meta:
        proxy = True

# Proxy models still works with filters (on related fields)
# and select_related, even when mixed with model inheritance


@python_2_unicode_compatible
class BaseUser(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return ':'.join((self.__class__.__name__, self.name,))


class TrackerUser(BaseUser):
    status = models.CharField(max_length=50)


class ProxyTrackerUser(TrackerUser):
    class Meta:
        proxy = True


@python_2_unicode_compatible
class Issue(models.Model):
    summary = models.CharField(max_length=255)
    assignee = models.ForeignKey(ProxyTrackerUser)

    def __str__(self):
        return ':'.join((self.__class__.__name__, self.summary,))


class Bug(Issue):
    version = models.CharField(max_length=50)
    reporter = models.ForeignKey(BaseUser)


class ProxyBug(Bug):
    """
    Proxy of an inherited class
    """
    class Meta:
        proxy = True


class ProxyProxyBug(ProxyBug):
    """
    A proxy of proxy model with related field
    """
    class Meta:
        proxy = True


class Improvement(Issue):
    """
    A model that has relation to a proxy model
    or to a proxy of proxy model
    """
    version = models.CharField(max_length=50)
    reporter = models.ForeignKey(ProxyTrackerUser)
    associated_bug = models.ForeignKey(ProxyProxyBug)


class ProxyImprovement(Improvement):
    class Meta:
        proxy = True
