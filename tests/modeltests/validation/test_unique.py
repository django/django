import datetime

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import connection
from django.test import TestCase
from django.utils import unittest

from models import (CustomPKModel, UniqueTogetherModel, UniqueFieldsModel,
    UniqueForDateModel, ModelToValidate, Post, FlexibleDatePost)


class GetUniqueCheckTests(unittest.TestCase):
    def test_unique_fields_get_collected(self):
        m = UniqueFieldsModel()
        self.assertEqual(
            ([(UniqueFieldsModel, ('id',)),
              (UniqueFieldsModel, ('unique_charfield',)),
              (UniqueFieldsModel, ('unique_integerfield',))],
             []),
            m._get_unique_checks()
        )

    def test_unique_together_gets_picked_up_and_converted_to_tuple(self):
        m = UniqueTogetherModel()
        self.assertEqual(
            ([(UniqueTogetherModel, ('ifield', 'cfield',)),
              (UniqueTogetherModel, ('ifield', 'efield')),
              (UniqueTogetherModel, ('id',)), ],
             []),
            m._get_unique_checks()
        )

    def test_primary_key_is_considered_unique(self):
        m = CustomPKModel()
        self.assertEqual(([(CustomPKModel, ('my_pk_field',))], []), m._get_unique_checks())

    def test_unique_for_date_gets_picked_up(self):
        m = UniqueForDateModel()
        self.assertEqual((
            [(UniqueForDateModel, ('id',))],
            [(UniqueForDateModel, 'date', 'count', 'start_date'),
             (UniqueForDateModel, 'year', 'count', 'end_date'),
             (UniqueForDateModel, 'month', 'order', 'end_date')]
            ), m._get_unique_checks()
        )

    def test_unique_for_date_exclusion(self):
        m = UniqueForDateModel()
        self.assertEqual((
            [(UniqueForDateModel, ('id',))],
            [(UniqueForDateModel, 'year', 'count', 'end_date'),
             (UniqueForDateModel, 'month', 'order', 'end_date')]
            ), m._get_unique_checks(exclude='start_date')
        )

class PerformUniqueChecksTest(TestCase):
    def test_primary_key_unique_check_not_performed_when_adding_and_pk_not_specified(self):
        # Regression test for #12560
        def test():
            mtv = ModelToValidate(number=10, name='Some Name')
            setattr(mtv, '_adding', True)
            mtv.full_clean()
        self.assertNumQueries(0, test)

    def test_primary_key_unique_check_performed_when_adding_and_pk_specified(self):
        # Regression test for #12560
        def test():
            mtv = ModelToValidate(number=10, name='Some Name', id=123)
            setattr(mtv, '_adding', True)
            mtv.full_clean()
        self.assertNumQueries(1, test)

    def test_primary_key_unique_check_not_performed_when_not_adding(self):
        # Regression test for #12132
        def test():
            mtv = ModelToValidate(number=10, name='Some Name')
            mtv.full_clean()
        self.assertNumQueries(0, test)

    def test_unique_for_date(self):
        p1 = Post.objects.create(title="Django 1.0 is released",
            slug="Django 1.0", subtitle="Finally", posted=datetime.date(2008, 9, 3))

        p = Post(title="Django 1.0 is released", posted=datetime.date(2008, 9, 3))
        try:
            p.full_clean()
        except ValidationError, e:
            self.assertEqual(e.message_dict, {'title': [u'Title must be unique for Posted date.']})
        else:
            self.fail('unique_for_date checks should catch this.')

        # Should work without errors
        p = Post(title="Work on Django 1.1 begins", posted=datetime.date(2008, 9, 3))
        p.full_clean()

        # Should work without errors
        p = Post(title="Django 1.0 is released", posted=datetime.datetime(2008, 9,4))
        p.full_clean()

        p = Post(slug="Django 1.0", posted=datetime.datetime(2008, 1, 1))
        try:
            p.full_clean()
        except ValidationError, e:
            self.assertEqual(e.message_dict, {'slug': [u'Slug must be unique for Posted year.']})
        else:
            self.fail('unique_for_year checks should catch this.')

        p = Post(subtitle="Finally", posted=datetime.datetime(2008, 9, 30))
        try:
            p.full_clean()
        except ValidationError, e:
            self.assertEqual(e.message_dict, {'subtitle': [u'Subtitle must be unique for Posted month.']})
        else:
            self.fail('unique_for_month checks should catch this.')

        p = Post(title="Django 1.0 is released")
        try:
            p.full_clean()
        except ValidationError, e:
            self.assertEqual(e.message_dict, {'posted': [u'This field cannot be null.']})
        else:
            self.fail("Model validation shouldn't allow an absent value for a DateField without null=True.")

    def test_unique_for_date_with_nullable_date(self):
        p1 = FlexibleDatePost.objects.create(title="Django 1.0 is released",
            slug="Django 1.0", subtitle="Finally", posted=datetime.date(2008, 9, 3))

        p = FlexibleDatePost(title="Django 1.0 is released")
        try:
            p.full_clean()
        except ValidationError, e:
            self.fail("unique_for_date checks shouldn't trigger when the associated DateField is None.")
        except:
            self.fail("unique_for_date checks shouldn't explode when the associated DateField is None.")

        p = FlexibleDatePost(slug="Django 1.0")
        try:
            p.full_clean()
        except ValidationError, e:
            self.fail("unique_for_year checks shouldn't trigger when the associated DateField is None.")
        except:
            self.fail("unique_for_year checks shouldn't explode when the associated DateField is None.")

        p = FlexibleDatePost(subtitle="Finally")
        try:
            p.full_clean()
        except ValidationError, e:
            self.fail("unique_for_month checks shouldn't trigger when the associated DateField is None.")
        except:
            self.fail("unique_for_month checks shouldn't explode when the associated DateField is None.")
