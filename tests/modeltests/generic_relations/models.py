"""
34. Generic relations

Generic relations let an object have a foreign key to any object through a
content-type/object-id field. A ``GenericForeignKey`` field can point to any
object, be it animal, vegetable, or mineral.

The canonical example is tags (although this example implementation is *far*
from complete).
"""

from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic

class TaggedItem(models.Model):
    """A tag on an item."""
    tag = models.SlugField()
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()

    content_object = generic.GenericForeignKey()

    class Meta:
        ordering = ["tag", "-object_id"]

    def __unicode__(self):
        return self.tag

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

__test__ = {'API_TESTS':"""
# Create the world in 7 lines of code...
>>> lion = Animal(common_name="Lion", latin_name="Panthera leo")
>>> platypus = Animal(common_name="Platypus", latin_name="Ornithorhynchus anatinus")
>>> eggplant = Vegetable(name="Eggplant", is_yucky=True)
>>> bacon = Vegetable(name="Bacon", is_yucky=False)
>>> quartz = Mineral(name="Quartz", hardness=7)
>>> for o in (platypus, lion, eggplant, bacon, quartz):
...     o.save()

# Objects with declared GenericRelations can be tagged directly -- the API
# mimics the many-to-many API.
>>> bacon.tags.create(tag="fatty")
<TaggedItem: fatty>
>>> bacon.tags.create(tag="salty")
<TaggedItem: salty>
>>> lion.tags.create(tag="yellow")
<TaggedItem: yellow>
>>> lion.tags.create(tag="hairy")
<TaggedItem: hairy>
>>> platypus.tags.create(tag="fatty")
<TaggedItem: fatty>

>>> lion.tags.all()
[<TaggedItem: hairy>, <TaggedItem: yellow>]
>>> bacon.tags.all()
[<TaggedItem: fatty>, <TaggedItem: salty>]

# You can easily access the content object like a foreign key.
>>> t = TaggedItem.objects.get(tag="salty")
>>> t.content_object
<Vegetable: Bacon>

# Recall that the Mineral class doesn't have an explicit GenericRelation
# defined. That's OK, because you can create TaggedItems explicitly.
>>> tag1 = TaggedItem(content_object=quartz, tag="shiny")
>>> tag2 = TaggedItem(content_object=quartz, tag="clearish")
>>> tag1.save()
>>> tag2.save()

# However, excluding GenericRelations means your lookups have to be a bit more
# explicit.
>>> from django.contrib.contenttypes.models import ContentType
>>> ctype = ContentType.objects.get_for_model(quartz)
>>> TaggedItem.objects.filter(content_type__pk=ctype.id, object_id=quartz.id)
[<TaggedItem: clearish>, <TaggedItem: shiny>]

# You can set a generic foreign key in the way you'd expect.
>>> tag1.content_object = platypus
>>> tag1.save()
>>> platypus.tags.all()
[<TaggedItem: fatty>, <TaggedItem: shiny>]
>>> TaggedItem.objects.filter(content_type__pk=ctype.id, object_id=quartz.id)
[<TaggedItem: clearish>]

# Queries across generic relations respect the content types. Even though there are two TaggedItems with a tag of "fatty", this query only pulls out the one with the content type related to Animals.
>>> Animal.objects.order_by('common_name')
[<Animal: Lion>, <Animal: Platypus>]
>>> Animal.objects.filter(tags__tag='fatty')
[<Animal: Platypus>]
>>> Animal.objects.exclude(tags__tag='fatty')
[<Animal: Lion>]

# If you delete an object with an explicit Generic relation, the related
# objects are deleted when the source object is deleted.
# Original list of tags:
>>> [(t.tag, t.content_type, t.object_id) for t in TaggedItem.objects.all()]
[(u'clearish', <ContentType: mineral>, 1), (u'fatty', <ContentType: vegetable>, 2), (u'fatty', <ContentType: animal>, 1), (u'hairy', <ContentType: animal>, 2), (u'salty', <ContentType: vegetable>, 2), (u'shiny', <ContentType: animal>, 1), (u'yellow', <ContentType: animal>, 2)]

>>> lion.delete()
>>> [(t.tag, t.content_type, t.object_id) for t in TaggedItem.objects.all()]
[(u'clearish', <ContentType: mineral>, 1), (u'fatty', <ContentType: vegetable>, 2), (u'fatty', <ContentType: animal>, 1), (u'salty', <ContentType: vegetable>, 2), (u'shiny', <ContentType: animal>, 1)]

# If Generic Relation is not explicitly defined, any related objects
# remain after deletion of the source object.
>>> quartz.delete()
>>> [(t.tag, t.content_type, t.object_id) for t in TaggedItem.objects.all()]
[(u'clearish', <ContentType: mineral>, 1), (u'fatty', <ContentType: vegetable>, 2), (u'fatty', <ContentType: animal>, 1), (u'salty', <ContentType: vegetable>, 2), (u'shiny', <ContentType: animal>, 1)]

# If you delete a tag, the objects using the tag are unaffected
# (other than losing a tag)
>>> tag = TaggedItem.objects.get(id=1)
>>> tag.delete()
>>> bacon.tags.all()
[<TaggedItem: salty>]
>>> [(t.tag, t.content_type, t.object_id) for t in TaggedItem.objects.all()]
[(u'clearish', <ContentType: mineral>, 1), (u'fatty', <ContentType: animal>, 1), (u'salty', <ContentType: vegetable>, 2), (u'shiny', <ContentType: animal>, 1)]

>>> TaggedItem.objects.filter(tag='fatty').delete()

>>> ctype = ContentType.objects.get_for_model(lion)
>>> Animal.objects.filter(tags__content_type=ctype)
[<Animal: Platypus>]

# Simple tests for multiple GenericForeignKeys
# only uses one model, since the above tests should be sufficient.
>>> tiger, cheetah, bear = Animal(common_name="tiger"), Animal(common_name="cheetah"), Animal(common_name="bear")
>>> for o in [tiger, cheetah, bear]: o.save()

# Create directly
>>> Comparison(first_obj=cheetah, other_obj=tiger, comparative="faster").save()
>>> Comparison(first_obj=tiger, other_obj=cheetah, comparative="cooler").save()

# Create using GenericRelation
>>> tiger.comparisons.create(other_obj=bear, comparative="cooler")
<Comparison: tiger is cooler than bear>
>>> tiger.comparisons.create(other_obj=cheetah, comparative="stronger")
<Comparison: tiger is stronger than cheetah>

>>> cheetah.comparisons.all()
[<Comparison: cheetah is faster than tiger>]

# Filtering works
>>> tiger.comparisons.filter(comparative="cooler")
[<Comparison: tiger is cooler than cheetah>, <Comparison: tiger is cooler than bear>]

# Filtering and deleting works
>>> subjective = ["cooler"]
>>> tiger.comparisons.filter(comparative__in=subjective).delete()
>>> Comparison.objects.all()
[<Comparison: cheetah is faster than tiger>, <Comparison: tiger is stronger than cheetah>]

# If we delete cheetah, Comparisons with cheetah as 'first_obj' will be deleted
# since Animal has an explicit GenericRelation to Comparison through first_obj.
# Comparisons with cheetah as 'other_obj' will not be deleted.
>>> cheetah.delete()
>>> Comparison.objects.all()
[<Comparison: tiger is stronger than None>]


# GenericInlineFormSet tests ##################################################

>>> from django.contrib.contenttypes.generic import generic_inlineformset_factory

>>> GenericFormSet = generic_inlineformset_factory(TaggedItem, extra=1)
>>> formset = GenericFormSet(instance=Animal())
>>> for form in formset.forms:
...     print form.as_p()
<p><label for="id_generic_relations-taggeditem-content_type-object_id-0-tag">Tag:</label> <input id="id_generic_relations-taggeditem-content_type-object_id-0-tag" type="text" name="generic_relations-taggeditem-content_type-object_id-0-tag" maxlength="50" /></p>
<p><label for="id_generic_relations-taggeditem-content_type-object_id-0-DELETE">Delete:</label> <input type="checkbox" name="generic_relations-taggeditem-content_type-object_id-0-DELETE" id="id_generic_relations-taggeditem-content_type-object_id-0-DELETE" /><input type="hidden" name="generic_relations-taggeditem-content_type-object_id-0-id" id="id_generic_relations-taggeditem-content_type-object_id-0-id" /></p>

>>> formset = GenericFormSet(instance=platypus)
>>> for form in formset.forms:
...     print form.as_p()
<p><label for="id_generic_relations-taggeditem-content_type-object_id-0-tag">Tag:</label> <input id="id_generic_relations-taggeditem-content_type-object_id-0-tag" type="text" name="generic_relations-taggeditem-content_type-object_id-0-tag" value="shiny" maxlength="50" /></p>
<p><label for="id_generic_relations-taggeditem-content_type-object_id-0-DELETE">Delete:</label> <input type="checkbox" name="generic_relations-taggeditem-content_type-object_id-0-DELETE" id="id_generic_relations-taggeditem-content_type-object_id-0-DELETE" /><input type="hidden" name="generic_relations-taggeditem-content_type-object_id-0-id" value="..." id="id_generic_relations-taggeditem-content_type-object_id-0-id" /></p>
<p><label for="id_generic_relations-taggeditem-content_type-object_id-1-tag">Tag:</label> <input id="id_generic_relations-taggeditem-content_type-object_id-1-tag" type="text" name="generic_relations-taggeditem-content_type-object_id-1-tag" maxlength="50" /></p>
<p><label for="id_generic_relations-taggeditem-content_type-object_id-1-DELETE">Delete:</label> <input type="checkbox" name="generic_relations-taggeditem-content_type-object_id-1-DELETE" id="id_generic_relations-taggeditem-content_type-object_id-1-DELETE" /><input type="hidden" name="generic_relations-taggeditem-content_type-object_id-1-id" id="id_generic_relations-taggeditem-content_type-object_id-1-id" /></p>

"""}
