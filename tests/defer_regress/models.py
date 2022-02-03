"""
Regression tests for defer() / only() behavior.
"""

from django.db import models


class Item(models.Model):
    name = models.CharField(max_length=15)
    text = models.TextField(default="xyzzy")
    value = models.IntegerField()
    other_value = models.IntegerField(default=0)


class RelatedItem(models.Model):
    item = models.ForeignKey(Item, models.CASCADE)


class ProxyRelated(RelatedItem):
    class Meta:
        proxy = True


class Child(models.Model):
    name = models.CharField(max_length=10)
    value = models.IntegerField()


class Leaf(models.Model):
    name = models.CharField(max_length=10)
    child = models.ForeignKey(Child, models.CASCADE)
    second_child = models.ForeignKey(
        Child, models.SET_NULL, related_name="other", null=True
    )
    value = models.IntegerField(default=42)


class ResolveThis(models.Model):
    num = models.FloatField()
    name = models.CharField(max_length=16)


class Proxy(Item):
    class Meta:
        proxy = True


class SimpleItem(models.Model):
    name = models.CharField(max_length=15)
    value = models.IntegerField()


class Feature(models.Model):
    item = models.ForeignKey(SimpleItem, models.CASCADE)


class SpecialFeature(models.Model):
    feature = models.ForeignKey(Feature, models.CASCADE)


class OneToOneItem(models.Model):
    item = models.OneToOneField(Item, models.CASCADE, related_name="one_to_one_item")
    name = models.CharField(max_length=15)


class ItemAndSimpleItem(models.Model):
    item = models.ForeignKey(Item, models.CASCADE)
    simple = models.ForeignKey(SimpleItem, models.CASCADE)


class Profile(models.Model):
    profile1 = models.CharField(max_length=255, default="profile1")


class Location(models.Model):
    location1 = models.CharField(max_length=255, default="location1")


class Request(models.Model):
    profile = models.ForeignKey(Profile, models.SET_NULL, null=True, blank=True)
    location = models.ForeignKey(Location, models.CASCADE)
    items = models.ManyToManyField(Item)

    request1 = models.CharField(default="request1", max_length=255)
    request2 = models.CharField(default="request2", max_length=255)
    request3 = models.CharField(default="request3", max_length=255)
    request4 = models.CharField(default="request4", max_length=255)


class Base(models.Model):
    text = models.TextField()


class Derived(Base):
    other_text = models.TextField()
