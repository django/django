# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from unittest import skipIf

from django.db import connection, models
from django.test import TestCase

from .models import Post


class TextFieldTests(TestCase):

    def test_max_length_passed_to_formfield(self):
        """
        TextField passes its max_length attribute to form fields created using
        their formfield() method.
        """
        tf1 = models.TextField()
        tf2 = models.TextField(max_length=2345)
        self.assertIsNone(tf1.formfield().max_length)
        self.assertEqual(2345, tf2.formfield().max_length)

    def test_to_python(self):
        """TextField.to_python() should return a string."""
        f = models.TextField()
        self.assertEqual(f.to_python(1), '1')

    def test_lookup_integer_in_textfield(self):
        self.assertEqual(Post.objects.filter(body=24).count(), 0)

    @skipIf(connection.vendor == 'mysql', 'Running on MySQL requires utf8mb4 encoding (#18392)')
    def test_emoji(self):
        p = Post.objects.create(title='Whatever', body='Smile 😀.')
        p.refresh_from_db()
        self.assertEqual(p.body, 'Smile 😀.')
