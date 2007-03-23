"""
34. Generic relations

Generic relations let an object have a foreign key to any object through a
content-type/object-id field. A generic foreign key can point to any object,
be it animal, vegetable, or mineral.

The canonical example is tags (although this example implementation is *far*
from complete).
"""

from django.db import models
from django.contrib.contenttypes.models import ContentType

class TaggedItem(models.Model):
    """A tag on an item."""
    tag = models.SlugField()
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    
    content_object = models.GenericForeignKey()
    
    class Meta:
        ordering = ["tag"]
    
    def __str__(self):
        return self.tag

class Animal(models.Model):
    common_name = models.CharField(maxlength=150)
    latin_name = models.CharField(maxlength=150)
    
    tags = models.GenericRelation(TaggedItem)

    def __str__(self):
        return self.common_name
        
class Vegetable(models.Model):
    name = models.CharField(maxlength=150)
    is_yucky = models.BooleanField(default=True)
    
    tags = models.GenericRelation(TaggedItem)
    
    def __str__(self):
        return self.name
    
class Mineral(models.Model):
    name = models.CharField(maxlength=150)
    hardness = models.PositiveSmallIntegerField()
    
    # note the lack of an explicit GenericRelation here...
    
    def __str__(self):
        return self.name
        
__test__ = {'API_TESTS':"""
# Create the world in 7 lines of code...
>>> lion = Animal(common_name="Lion", latin_name="Panthera leo")
>>> platypus = Animal(common_name="Platypus", latin_name="Ornithorhynchus anatinus")
>>> eggplant = Vegetable(name="Eggplant", is_yucky=True)
>>> bacon = Vegetable(name="Bacon", is_yucky=False)
>>> quartz = Mineral(name="Quartz", hardness=7)
>>> for o in (lion, platypus, eggplant, bacon, quartz):
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
[<TaggedItem: shiny>]
>>> TaggedItem.objects.filter(content_type__pk=ctype.id, object_id=quartz.id)
[<TaggedItem: clearish>]

# If you delete an object with an explicit Generic relation, the related
# objects are deleted when the source object is deleted.
# Original list of tags:
>>> [(t.tag, t.content_type, t.object_id) for t in TaggedItem.objects.all()]
[('clearish', <ContentType: mineral>, 1), ('fatty', <ContentType: vegetable>, 2), ('hairy', <ContentType: animal>, 1), ('salty', <ContentType: vegetable>, 2), ('shiny', <ContentType: animal>, 2), ('yellow', <ContentType: animal>, 1)]

>>> lion.delete()
>>> [(t.tag, t.content_type, t.object_id) for t in TaggedItem.objects.all()]
[('clearish', <ContentType: mineral>, 1), ('fatty', <ContentType: vegetable>, 2), ('salty', <ContentType: vegetable>, 2), ('shiny', <ContentType: animal>, 2)]

# If Generic Relation is not explicitly defined, any related objects 
# remain after deletion of the source object.
>>> quartz.delete()
>>> [(t.tag, t.content_type, t.object_id) for t in TaggedItem.objects.all()]
[('clearish', <ContentType: mineral>, 1), ('fatty', <ContentType: vegetable>, 2), ('salty', <ContentType: vegetable>, 2), ('shiny', <ContentType: animal>, 2)]

# If you delete a tag, the objects using the tag are unaffected 
# (other than losing a tag)
>>> tag = TaggedItem.objects.get(id=1)
>>> tag.delete()
>>> bacon.tags.all()
[<TaggedItem: salty>]
>>> [(t.tag, t.content_type, t.object_id) for t in TaggedItem.objects.all()]
[('clearish', <ContentType: mineral>, 1), ('salty', <ContentType: vegetable>, 2), ('shiny', <ContentType: animal>, 2)]

"""}
