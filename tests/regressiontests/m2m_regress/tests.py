from __future__ import absolute_import

from django.core.exceptions import FieldError
from django.test import TestCase

from .models import (SelfRefer, Tag, TagCollection, Entry, SelfReferChild,
    SelfReferChildSibling, Worksheet)


class M2MRegressionTests(TestCase):
    def test_multiple_m2m(self):
        # Multiple m2m references to model must be distinguished when
        # accessing the relations through an instance attribute.

        s1 = SelfRefer.objects.create(name='s1')
        s2 = SelfRefer.objects.create(name='s2')
        s3 = SelfRefer.objects.create(name='s3')
        s1.references.add(s2)
        s1.related.add(s3)

        e1 = Entry.objects.create(name='e1')
        t1 = Tag.objects.create(name='t1')
        t2 = Tag.objects.create(name='t2')

        e1.topics.add(t1)
        e1.related.add(t2)

        self.assertQuerysetEqual(s1.references.all(), ["<SelfRefer: s2>"])
        self.assertQuerysetEqual(s1.related.all(), ["<SelfRefer: s3>"])

        self.assertQuerysetEqual(e1.topics.all(), ["<Tag: t1>"])
        self.assertQuerysetEqual(e1.related.all(), ["<Tag: t2>"])

    def test_internal_related_name_not_in_error_msg(self):
        # The secret internal related names for self-referential many-to-many
        # fields shouldn't appear in the list when an error is made.

        self.assertRaisesRegexp(FieldError,
            "Choices are: id, name, references, related, selfreferchild, selfreferchildsibling$",
            lambda: SelfRefer.objects.filter(porcupine='fred')
        )

    def test_m2m_inheritance_symmetry(self):
        # Test to ensure that the relationship between two inherited models
        # with a self-referential m2m field maintains symmetry

        sr_child = SelfReferChild(name="Hanna")
        sr_child.save()

        sr_sibling = SelfReferChildSibling(name="Beth")
        sr_sibling.save()
        sr_child.related.add(sr_sibling)

        self.assertQuerysetEqual(sr_child.related.all(), ["<SelfRefer: Beth>"])
        self.assertQuerysetEqual(sr_sibling.related.all(), ["<SelfRefer: Hanna>"])

    def test_m2m_pk_field_type(self):
        # Regression for #11311 - The primary key for models in a m2m relation
        # doesn't have to be an AutoField

        w = Worksheet(id='abc')
        w.save()
        w.delete()

    def test_add_m2m_with_base_class(self):
        # Regression for #11956 -- You can add an object to a m2m with the
        # base class without causing integrity errors

        t1 = Tag.objects.create(name='t1')
        t2 = Tag.objects.create(name='t2')

        c1 = TagCollection.objects.create(name='c1')
        c1.tags = [t1,t2]
        c1 = TagCollection.objects.get(name='c1')

        self.assertQuerysetEqual(c1.tags.all(), ["<Tag: t1>", "<Tag: t2>"])
        self.assertQuerysetEqual(t1.tag_collections.all(), ["<TagCollection: c1>"])

    def test_manager_class_caching(self):
        e1 = Entry.objects.create()
        e2 = Entry.objects.create()
        t1 = Tag.objects.create()
        t2 = Tag.objects.create()

        # Get same manager twice in a row:
        self.assertTrue(t1.entry_set.__class__ is t1.entry_set.__class__)
        self.assertTrue(e1.topics.__class__ is e1.topics.__class__)

        # Get same manager for different instances
        self.assertTrue(e1.topics.__class__ is e2.topics.__class__)
        self.assertTrue(t1.entry_set.__class__ is t2.entry_set.__class__)
