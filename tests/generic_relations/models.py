"""
34. Generic relations

Generic relations let an object have a foreign key to any object through a
content-type/object-id field. A ``GenericForeignKey`` field can point to any
object, be it animal, vegetable, or mineral.

The canonical example is tags (although this example implementation is *far*
from complete).
"""

from __future__ import unicode_literals

from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class TaggedItem(models.Model):
    """A tag on an item."""
    tag = models.SlugField()
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()

    content_object = generic.GenericForeignKey()

    class Meta:
        ordering = ["tag", "content_type__name"]

    def __str__(self):
        return self.tag

class ValuableTaggedItem(TaggedItem):
    value = models.PositiveIntegerField()

@python_2_unicode_compatible
class Comparison(models.Model):
    """
    A model that tests having multiple GenericForeignKeys
    """
    comparative = models.CharField(max_length=50)

    content_type1 = models.ForeignKey(ContentType, related_name="comparative1_set")
    object_id1 = models.PositiveIntegerField()

    content_type2 = models.ForeignKey(ContentType,  related_name="comparative2_set")
    object_id2 = models.PositiveIntegerField()

    first_obj = generic.GenericForeignKey(ct_field="content_type1", fk_field="object_id1")
    other_obj = generic.GenericForeignKey(ct_field="content_type2", fk_field="object_id2")

    def __str__(self):
        return "%s is %s than %s" % (self.first_obj, self.comparative, self.other_obj)

@python_2_unicode_compatible
class Animal(models.Model):
    common_name = models.CharField(max_length=150)
    latin_name = models.CharField(max_length=150)

    tags = generic.GenericRelation(TaggedItem)
    comparisons = generic.GenericRelation(Comparison,
                                          object_id_field="object_id1",
                                          content_type_field="content_type1")

    def __str__(self):
        return self.common_name

@python_2_unicode_compatible
class Vegetable(models.Model):
    name = models.CharField(max_length=150)
    is_yucky = models.BooleanField(default=True)

    tags = generic.GenericRelation(TaggedItem)

    def __str__(self):
        return self.name

@python_2_unicode_compatible
class Mineral(models.Model):
    name = models.CharField(max_length=150)
    hardness = models.PositiveSmallIntegerField()

    # note the lack of an explicit GenericRelation here...

    def __str__(self):
        return self.name

class GeckoManager(models.Manager):
    def get_queryset(self):
        return super(GeckoManager, self).get_queryset().filter(has_tail=True)

class Gecko(models.Model):
    has_tail = models.BooleanField(default=False)
    objects = GeckoManager()

# To test fix for #11263
class Rock(Mineral):
    tags = generic.GenericRelation(TaggedItem)

class ManualPK(models.Model):
    id = models.IntegerField(primary_key=True)
    tags = generic.GenericRelation(TaggedItem)


class ForProxyModelModel(models.Model):
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    obj = generic.GenericForeignKey(for_concrete_model=False)
    title = models.CharField(max_length=255, null=True)

class ForConcreteModelModel(models.Model):
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    obj = generic.GenericForeignKey()

class ConcreteRelatedModel(models.Model):
    bases = generic.GenericRelation(ForProxyModelModel, for_concrete_model=False)

class ProxyRelatedModel(ConcreteRelatedModel):
    class Meta:
        proxy = True
