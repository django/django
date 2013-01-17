from __future__ import absolute_import, unicode_literals

import itertools
import types

from django.core.management.validation import get_validation_errors
from django.db.models.related import RelatedObject
from django.forms.models import inlineformset_factory
from django.test import TestCase

from .models import Author, Book, Publisher

class RelatedObjectRecreationTestCase(TestCase):
    '''
    Ensure that RelatedObject instances are not unnecessarily recreated.

    Regression for #19399.
    '''

    def setUp(self):
        self.related_objects = [Book._meta.get_field('authors', many_to_many=True).related, Book._meta.get_field('publisher').related]

    def test_relatedobject_cache_does_not_recreate_relatedobject(self):
        # Monkey patch RelatedObject instances to mark them as not replaced.
        for related_object in [Book._meta.get_field('authors', many_to_many=True).related, Book._meta.get_field('publisher').related]:
            related_object.not_replaced = True

        cached_related_objects = itertools.chain(Publisher._meta.get_all_related_objects(), Author._meta.get_all_related_many_to_many_objects())
        for related_object in cached_related_objects:
            self.assertTrue(getattr(related_object, 'not_replaced', False))

    def test_validation_does_not_recreate_relatedobject(self):
        self.assertEquals(get_validation_errors('relatedobject_recreation'), 0)

        # Monkey patch RelatedObject instances to make them know whether get_accessor_name method has been called.
        for related_object in self.related_objects:
            old_get_accessor_name = related_object.get_accessor_name
            def get_accessor_name(self):
                self.get_accessor_name_called = True
                return old_get_accessor_name()
            related_object.get_accessor_name = types.MethodType(get_accessor_name, related_object, RelatedObject)

        get_validation_errors('relatedobject_recreation')
        for related_object in self.related_objects:
            self.assertTrue(hasattr(related_object, 'get_accessor_name_called'))

    def test_inline_formset_does_not_recreate_relatedobject(self):
        book_of_publisher_formset = inlineformset_factory(Publisher, Book)
        old_book_of_publisher_formset_rel_name = book_of_publisher_formset().rel_name
        old_book_of_publisher_formset_default_prefix = book_of_publisher_formset.get_default_prefix()

        # Monkey patch RelatedObject instances to make them return different accessor names.
        for related_object in self.related_objects:
            old_get_accessor_name = related_object.get_accessor_name
            def get_accessor_name(self):
                return old_get_accessor_name() + "custom"
            related_object.get_accessor_name = types.MethodType(get_accessor_name, related_object, RelatedObject)

        self.assertNotEquals(old_book_of_publisher_formset_rel_name, book_of_publisher_formset().rel_name)
        self.assertNotEquals(old_book_of_publisher_formset_default_prefix, book_of_publisher_formset.get_default_prefix())
