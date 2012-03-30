from __future__ import absolute_import

import datetime

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import unittest

from .models import (CustomPKModel, UniqueTogetherModel, UniqueFieldsModel,
    UniqueForDateModel, ModelToValidate, Post, FlexibleDatePost,
    UniqueErrorsModel)


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
        with self.assertNumQueries(0):
            mtv = ModelToValidate(number=10, name='Some Name')
            setattr(mtv, '_adding', True)
            mtv.full_clean()

    def test_primary_key_unique_check_performed_when_adding_and_pk_specified(self):
        # Regression test for #12560
        with self.assertNumQueries(1):
            mtv = ModelToValidate(number=10, name='Some Name', id=123)
            setattr(mtv, '_adding', True)
            mtv.full_clean()

    def test_primary_key_unique_check_not_performed_when_not_adding(self):
        # Regression test for #12132
        with self.assertNumQueries(0):
            mtv = ModelToValidate(number=10, name='Some Name')
            mtv.full_clean()

    def test_unique_for_date(self):
        p1 = Post.objects.create(title="Django 1.0 is released",
            slug="Django 1.0", subtitle="Finally", posted=datetime.date(2008, 9, 3))

        p = Post(title="Django 1.0 is released", posted=datetime.date(2008, 9, 3))
        with self.assertRaises(ValidationError) as cm:
            p.full_clean()
        self.assertEqual(cm.exception.message_dict, {'title': [u'Title must be unique for Posted date.']})

        # Should work without errors
        p = Post(title="Work on Django 1.1 begins", posted=datetime.date(2008, 9, 3))
        p.full_clean()

        # Should work without errors
        p = Post(title="Django 1.0 is released", posted=datetime.datetime(2008, 9,4))
        p.full_clean()

        p = Post(slug="Django 1.0", posted=datetime.datetime(2008, 1, 1))
        with self.assertRaises(ValidationError) as cm:
            p.full_clean()
        self.assertEqual(cm.exception.message_dict, {'slug': [u'Slug must be unique for Posted year.']})

        p = Post(subtitle="Finally", posted=datetime.datetime(2008, 9, 30))
        with self.assertRaises(ValidationError) as cm:
            p.full_clean()
        self.assertEqual(cm.exception.message_dict, {'subtitle': [u'Subtitle must be unique for Posted month.']})

        p = Post(title="Django 1.0 is released")
        with self.assertRaises(ValidationError) as cm:
            p.full_clean()
        self.assertEqual(cm.exception.message_dict, {'posted': [u'This field cannot be null.']})

    def test_unique_for_date_with_nullable_date(self):
        p1 = FlexibleDatePost.objects.create(title="Django 1.0 is released",
            slug="Django 1.0", subtitle="Finally", posted=datetime.date(2008, 9, 3))

        p = FlexibleDatePost(title="Django 1.0 is released")
        try:
            p.full_clean()
        except ValidationError, e:
            self.fail("unique_for_date checks shouldn't trigger when the associated DateField is None.")

        p = FlexibleDatePost(slug="Django 1.0")
        try:
            p.full_clean()
        except ValidationError, e:
            self.fail("unique_for_year checks shouldn't trigger when the associated DateField is None.")

        p = FlexibleDatePost(subtitle="Finally")
        try:
            p.full_clean()
        except ValidationError, e:
            self.fail("unique_for_month checks shouldn't trigger when the associated DateField is None.")

    def test_unique_errors(self):
        m1 = UniqueErrorsModel.objects.create(name='Some Name', no=10)
        m = UniqueErrorsModel(name='Some Name', no=11)
        with self.assertRaises(ValidationError) as cm:
            m.full_clean()
        self.assertEqual(cm.exception.message_dict, {'name': [u'Custom unique name message.']})

        m = UniqueErrorsModel(name='Some Other Name', no=10)
        with self.assertRaises(ValidationError) as cm:
            m.full_clean()
        self.assertEqual(cm.exception.message_dict, {'no': [u'Custom unique number message.']})

