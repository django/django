from django.contrib.auth import models as auth
from django.db import models


# No related name is needed here, since symmetrical relations are not
# explicitly reversible.
class SelfRefer(models.Model):
    name = models.CharField(max_length=10)
    references = models.ManyToManyField("self")
    related = models.ManyToManyField("self")

    def __str__(self):
        return self.name


class Tag(models.Model):
    name = models.CharField(max_length=10)

    def __str__(self):
        return self.name


# Regression for #11956 -- a many to many to the base class
class TagCollection(Tag):
    tags = models.ManyToManyField(Tag, related_name="tag_collections")

    def __str__(self):
        return self.name


# A related_name is required on one of the ManyToManyField entries here because
# they are both addressable as reverse relations from Tag.
class Entry(models.Model):
    name = models.CharField(max_length=10)
    topics = models.ManyToManyField(Tag)
    related = models.ManyToManyField(Tag, related_name="similar")

    def __str__(self):
        return self.name


# Two models both inheriting from a base model with a self-referential m2m field
class SelfReferChild(SelfRefer):
    pass


class SelfReferChildSibling(SelfRefer):
    pass


# Many-to-Many relation between models, where one of the PK's isn't an Autofield
class Line(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Worksheet(models.Model):
    id = models.CharField(primary_key=True, max_length=100)
    lines = models.ManyToManyField(Line, blank=True)


# Regression for #11226 -- A model with the same name that another one to
# which it has a m2m relation. This shouldn't cause a name clash between
# the automatically created m2m intermediary table FK field names when
# running migrate
class User(models.Model):
    name = models.CharField(max_length=30)
    friends = models.ManyToManyField(auth.User)


class BadModelWithSplit(models.Model):
    name = models.CharField(max_length=1)

    class Meta:
        abstract = True

    def split(self):
        raise RuntimeError("split should not be called")


class RegressionModelSplit(BadModelWithSplit):
    """
    Model with a split method should not cause an error in add_lazy_relation
    """

    others = models.ManyToManyField("self")


# Regression for #24505 -- Two ManyToManyFields with the same "to" model
# and related_name set to '+'.
class Post(models.Model):
    primary_lines = models.ManyToManyField(Line, related_name="+")
    secondary_lines = models.ManyToManyField(Line, related_name="+")
