# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from unittest import skipIf

from django.core.exceptions import ValidationError
from django.db import connection, models
from django.test import SimpleTestCase, TestCase
from django.utils.functional import lazy

from .models import Post


class TestCharField(TestCase):

    def test_max_length_passed_to_formfield(self):
        """
        CharField passes its max_length attribute to form fields created using
        the formfield() method.
        """
        cf1 = models.CharField()
        cf2 = models.CharField(max_length=1234)
        self.assertIsNone(cf1.formfield().max_length)
        self.assertEqual(1234, cf2.formfield().max_length)

    def test_lookup_integer_in_charfield(self):
        self.assertEqual(Post.objects.filter(title=9).count(), 0)

    @skipIf(connection.vendor == 'mysql', 'Running on MySQL requires utf8mb4 encoding (#18392)')
    def test_emoji(self):
        p = Post.objects.create(title='Smile 😀', body='Whatever.')
        p.refresh_from_db()
        self.assertEqual(p.title, 'Smile 😀')


class ValidationTests(SimpleTestCase):

    def test_charfield_raises_error_on_empty_string(self):
        f = models.CharField()
        with self.assertRaises(ValidationError):
            f.clean('', None)

    def test_charfield_cleans_empty_string_when_blank_true(self):
        f = models.CharField(blank=True)
        self.assertEqual('', f.clean('', None))

    def test_charfield_with_choices_cleans_valid_choice(self):
        f = models.CharField(max_length=1, choices=[('a', 'A'), ('b', 'B')])
        self.assertEqual('a', f.clean('a', None))

    def test_charfield_with_choices_raises_error_on_invalid_choice(self):
        f = models.CharField(choices=[('a', 'A'), ('b', 'B')])
        with self.assertRaises(ValidationError):
            f.clean('not a', None)

    def test_charfield_get_choices_with_blank_defined(self):
        f = models.CharField(choices=[('', '<><>'), ('a', 'A')])
        self.assertEqual(f.get_choices(True), [('', '<><>'), ('a', 'A')])

    def test_charfield_get_choices_doesnt_evaluate_lazy_strings(self):
        # Regression test for #23098
        # Will raise ZeroDivisionError if lazy is evaluated
        lazy_func = lazy(lambda x: 0 / 0, int)
        f = models.CharField(choices=[(lazy_func('group'), (('a', 'A'), ('b', 'B')))])
        self.assertEqual(f.get_choices(True)[0], ('', '---------'))

    def test_charfield_raises_error_on_empty_input(self):
        f = models.CharField(null=False)
        with self.assertRaises(ValidationError):
            f.clean(None, None)
