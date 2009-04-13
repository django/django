from django.db import models

# No related name is needed here, since symmetrical relations are not
# explicitly reversible.
class SelfRefer(models.Model):
    name = models.CharField(max_length=10)
    references = models.ManyToManyField('self')
    related = models.ManyToManyField('self')

    def __unicode__(self):
        return self.name

class Tag(models.Model):
    name = models.CharField(max_length=10)

    def __unicode__(self):
        return self.name

# A related_name is required on one of the ManyToManyField entries here because
# they are both addressable as reverse relations from Tag.
class Entry(models.Model):
    name = models.CharField(max_length=10)
    topics = models.ManyToManyField(Tag)
    related = models.ManyToManyField(Tag, related_name="similar")

    def __unicode__(self):
        return self.name

# Two models both inheriting from a base model with a self-referential m2m field
class SelfReferChild(SelfRefer):
    pass

class SelfReferChildSibling(SelfRefer):
    pass

__test__ = {"regressions": """
# Multiple m2m references to the same model or a different model must be
# distinguished when accessing the relations through an instance attribute.

>>> s1 = SelfRefer.objects.create(name='s1')
>>> s2 = SelfRefer.objects.create(name='s2')
>>> s3 = SelfRefer.objects.create(name='s3')
>>> s1.references.add(s2)
>>> s1.related.add(s3)

>>> e1 = Entry.objects.create(name='e1')
>>> t1 = Tag.objects.create(name='t1')
>>> t2 = Tag.objects.create(name='t2')
>>> e1.topics.add(t1)
>>> e1.related.add(t2)

>>> s1.references.all()
[<SelfRefer: s2>]
>>> s1.related.all()
[<SelfRefer: s3>]

>>> e1.topics.all()
[<Tag: t1>]
>>> e1.related.all()
[<Tag: t2>]

# The secret internal related names for self-referential many-to-many fields
# shouldn't appear in the list when an error is made.
>>> SelfRefer.objects.filter(porcupine='fred')
Traceback (most recent call last):
...
FieldError: Cannot resolve keyword 'porcupine' into field. Choices are: id, name, references, related, selfreferchild, selfreferchildsibling

# Test to ensure that the relationship between two inherited models
# with a self-referential m2m field maintains symmetry
>>> sr_child = SelfReferChild(name="Hanna")
>>> sr_child.save()

>>> sr_sibling = SelfReferChildSibling(name="Beth")
>>> sr_sibling.save()
>>> sr_child.related.add(sr_sibling)
>>> sr_child.related.all()
[<SelfRefer: Beth>]
>>> sr_sibling.related.all()
[<SelfRefer: Hanna>]

"""
}
