"""
Generic relations

Generic relations let an object have a foreign key to any object through a
content-type/object-id field. A ``GenericForeignKey`` field can point to any
object, be it animal, vegetable, or mineral.

The canonical example is tags (although this example implementation is *far*
from complete).
"""

from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models


class TaggedItem(models.Model):
    """A tag on an item."""

    tag = models.SlugField()
    content_type = models.ForeignKey(ContentType, models.CASCADE)
    object_id = models.PositiveIntegerField()

    content_object = GenericForeignKey()

    class Meta:
        ordering = ["tag", "content_type__model"]

    def __str__(self):
        return self.tag


class ValuableTaggedItem(TaggedItem):
    value = models.PositiveIntegerField()


class AbstractComparison(models.Model):
    comparative = models.CharField(max_length=50)

    content_type1 = models.ForeignKey(
        ContentType, models.CASCADE, related_name="comparative1_set"
    )
    object_id1 = models.PositiveIntegerField()

    first_obj = GenericForeignKey(ct_field="content_type1", fk_field="object_id1")


class Comparison(AbstractComparison):
    """
    A model that tests having multiple GenericForeignKeys. One is defined
    through an inherited abstract model and one defined directly on this class.
    """

    content_type2 = models.ForeignKey(
        ContentType, models.CASCADE, related_name="comparative2_set"
    )
    object_id2 = models.PositiveIntegerField()

    other_obj = GenericForeignKey(ct_field="content_type2", fk_field="object_id2")

    def __str__(self):
        return "%s is %s than %s" % (self.first_obj, self.comparative, self.other_obj)


class Animal(models.Model):
    common_name = models.CharField(max_length=150)
    latin_name = models.CharField(max_length=150)

    tags = GenericRelation(TaggedItem, related_query_name="animal")
    comparisons = GenericRelation(
        Comparison, object_id_field="object_id1", content_type_field="content_type1"
    )

    def __str__(self):
        return self.common_name


class Vegetable(models.Model):
    name = models.CharField(max_length=150)
    is_yucky = models.BooleanField(default=True)

    tags = GenericRelation(TaggedItem)

    def __str__(self):
        return self.name


class Carrot(Vegetable):
    pass


class Mineral(models.Model):
    name = models.CharField(max_length=150)
    hardness = models.PositiveSmallIntegerField()

    # note the lack of an explicit GenericRelation here...

    def __str__(self):
        return self.name


class GeckoManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(has_tail=True)


class Gecko(models.Model):
    has_tail = models.BooleanField(default=False)
    objects = GeckoManager()


# To test fix for #11263
class Rock(Mineral):
    tags = GenericRelation(TaggedItem)


class ValuableRock(Mineral):
    tags = GenericRelation(ValuableTaggedItem)


class ManualPK(models.Model):
    id = models.IntegerField(primary_key=True)
    tags = GenericRelation(TaggedItem, related_query_name="manualpk")


class ForProxyModelModel(models.Model):
    content_type = models.ForeignKey(ContentType, models.CASCADE)
    object_id = models.PositiveIntegerField()
    obj = GenericForeignKey(for_concrete_model=False)
    title = models.CharField(max_length=255, null=True)


class ForConcreteModelModel(models.Model):
    content_type = models.ForeignKey(ContentType, models.CASCADE)
    object_id = models.PositiveIntegerField()
    obj = GenericForeignKey()


class ConcreteRelatedModel(models.Model):
    bases = GenericRelation(ForProxyModelModel, for_concrete_model=False)


class ProxyRelatedModel(ConcreteRelatedModel):
    class Meta:
        proxy = True


# To test fix for #7551
class AllowsNullGFK(models.Model):
    content_type = models.ForeignKey(ContentType, models.SET_NULL, null=True)
    object_id = models.PositiveIntegerField(null=True)
    content_object = GenericForeignKey()
