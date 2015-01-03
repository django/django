from django.db import models
from django.utils import six
from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class Site(models.Model):
    domain = models.CharField(max_length=100)

    def __str__(self):
        return self.domain


class Article(models.Model):
    """
    A simple Article model for testing
    """
    site = models.ForeignKey(Site, related_name="admin_articles")
    title = models.CharField(max_length=100)
    title2 = models.CharField(max_length=100, verbose_name="another name")
    created = models.DateTimeField()

    def test_from_model(self):
        return "nothing"

    def test_from_model_with_override(self):
        return "nothing"
    test_from_model_with_override.short_description = "not What you Expect"


@python_2_unicode_compatible
class Count(models.Model):
    num = models.PositiveSmallIntegerField()
    parent = models.ForeignKey('self', null=True)

    def __str__(self):
        return six.text_type(self.num)


class Event(models.Model):
    date = models.DateTimeField(auto_now_add=True)


class Location(models.Model):
    event = models.OneToOneField(Event, verbose_name='awesome event')


class Guest(models.Model):
    event = models.OneToOneField(Event)
    name = models.CharField(max_length=255)

    class Meta:
        verbose_name = "awesome guest"


class EventGuide(models.Model):
    event = models.ForeignKey(Event, on_delete=models.DO_NOTHING)


class Vehicle(models.Model):
    pass


class VehicleMixin(Vehicle):
    vehicle = models.OneToOneField(Vehicle, parent_link=True, related_name='vehicle_%(app_label)s_%(class)s')

    class Meta:
        abstract = True


class Car(VehicleMixin):
    pass
