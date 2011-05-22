"""
34. Generic relations

Generic relations let an object have a foreign key to any object through a
content-type/object-id field. A ``GenericForeignKey`` field can point to any
object, be it animal, vegetable, or mineral.

The canonical example is tags (although this example implementation is *far*
from complete).
"""

from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.db import models


class TaggedItem(models.Model):
    """A tag on an item."""
    tag = models.SlugField()
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()

    content_object = generic.GenericForeignKey()

    class Meta:
        ordering = ["tag", "content_type__name"]

    def __unicode__(self):
        return self.tag

class ValuableTaggedItem(TaggedItem):
    value = models.PositiveIntegerField()

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

    def __unicode__(self):
        return u"%s is %s than %s" % (self.first_obj, self.comparative, self.other_obj)

class Animal(models.Model):
    common_name = models.CharField(max_length=150)
    latin_name = models.CharField(max_length=150)

    tags = generic.GenericRelation(TaggedItem)
    comparisons = generic.GenericRelation(Comparison,
                                          object_id_field="object_id1",
                                          content_type_field="content_type1")

    def __unicode__(self):
        return self.common_name

class Vegetable(models.Model):
    name = models.CharField(max_length=150)
    is_yucky = models.BooleanField(default=True)

    tags = generic.GenericRelation(TaggedItem)

    def __unicode__(self):
        return self.name

class Mineral(models.Model):
    name = models.CharField(max_length=150)
    hardness = models.PositiveSmallIntegerField()

    # note the lack of an explicit GenericRelation here...

    def __unicode__(self):
        return self.name

class GeckoManager(models.Manager):
    def get_query_set(self):
        return super(GeckoManager, self).get_query_set().filter(has_tail=True)

class Gecko(models.Model):
    has_tail = models.BooleanField()
    objects = GeckoManager()
