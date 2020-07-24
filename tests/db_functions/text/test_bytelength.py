import unittest

from django.db import NotSupportedError, connection
from django.db.models import CharField
from django.db.models.functions import ByteLength, Reverse
from django.test import TestCase
from django.test.utils import register_lookup

from ..models import Author


class ByteLengthTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.john = Author.objects.create(name='John Smith', alias='smithj')
        cls.elena = Author.objects.create(name='Élena Jordan', alias='elena')
        cls.python = Author.objects.create(name='パイソン')

    @unittest.skipIf(connection.vendor == 'oracle', "Oracle doesn't support ByteLength.")
    def test_null(self):
        author = Author.objects.annotate(byte_length=ByteLength('alias')).get(pk=self.python.pk)
        self.assertEqual(author.byte_length, None)

    @unittest.skipIf(connection.vendor == 'oracle', "Oracle doesn't support ByteLength.")
    def test_basic(self):
        authors = Author.objects.annotate(
            name_byte_length=ByteLength('name'),
            alias_byte_length=ByteLength('alias'),
        )
        self.assertQuerysetEqual(
            authors,
            [(10, 6), (13, 5), (12, None)],
            lambda a: (a.name_byte_length, a.alias_byte_length),
            ordered=False,
        )
        self.assertEqual(authors.filter(alias_byte_length__lte=ByteLength('name')).count(), 2)

    @unittest.skipIf(connection.vendor == 'oracle', "Oracle doesn't support ByteLength.")
    def test_transform(self):
        with register_lookup(CharField, ByteLength):
            authors = Author.objects.all()
            self.assertCountEqual(authors.filter(name__byte_length__gt=10), [self.elena, self.python])
            self.assertCountEqual(authors.exclude(name__byte_length__gt=10), [self.john])

    @unittest.skipIf(connection.vendor == 'oracle', "Oracle doesn't support ByteLength.")
    def test_expressions(self):
        author = Author.objects.annotate(byte_length=ByteLength(Reverse('name'))).get(pk=self.python.pk)
        self.assertEqual(author.byte_length, 12)
        with register_lookup(CharField, ByteLength), register_lookup(CharField, Reverse):
            authors = Author.objects.all()
            self.assertCountEqual(authors.filter(name__reverse__byte_length__gt=10), [self.elena, self.python])
            self.assertCountEqual(authors.exclude(name__reverse__byte_length__gt=10), [self.john])

    @unittest.skipIf(connection.vendor == 'oracle', "Oracle doesn't support ByteLength.")
    def test_ordering(self):
        authors = Author.objects.order_by(ByteLength('name'))
        self.assertSequenceEqual(authors, [self.john, self.python, self.elena])

    @unittest.skipUnless(connection.vendor == 'oracle', "Oracle doesn't support ByteLength.")
    def test_unsupported(self):
        msg = 'ByteLength is not supported on Oracle.'
        with self.assertRaisesMessage(NotSupportedError, msg):
            Author.objects.annotate(name_byte_length=ByteLength('name')).first()
