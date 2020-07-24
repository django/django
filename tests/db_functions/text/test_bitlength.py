import unittest

from django.db import NotSupportedError, connection
from django.db.models import CharField
from django.db.models.functions import BitLength, Reverse
from django.test import TestCase
from django.test.utils import register_lookup

from ..models import Author


class BitLengthTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.john = Author.objects.create(name='John Smith', alias='smithj')
        cls.elena = Author.objects.create(name='Élena Jordan', alias='elena')
        cls.python = Author.objects.create(name='パイソン')

    @unittest.skipIf(connection.vendor == 'oracle', "Oracle doesn't support BitLength.")
    def test_null(self):
        author = Author.objects.annotate(bit_length=BitLength('alias')).get(pk=self.python.pk)
        self.assertEqual(author.bit_length, None)

    @unittest.skipIf(connection.vendor == 'oracle', "Oracle doesn't support BitLength.")
    def test_basic(self):
        authors = Author.objects.annotate(
            name_bit_length=BitLength('name'),
            alias_bit_length=BitLength('alias'),
        )
        self.assertQuerysetEqual(
            authors,
            [(80, 48), (104, 40), (96, None)],
            lambda a: (a.name_bit_length, a.alias_bit_length),
            ordered=False,
        )
        self.assertEqual(authors.filter(alias_bit_length__lte=BitLength('name')).count(), 2)

    @unittest.skipIf(connection.vendor == 'oracle', "Oracle doesn't support BitLength.")
    def test_transform(self):
        with register_lookup(CharField, BitLength):
            authors = Author.objects.all()
            self.assertCountEqual(authors.filter(name__bit_length__gt=100), [self.elena])
            self.assertCountEqual(authors.exclude(name__bit_length__gt=100), [self.john, self.python])

    @unittest.skipIf(connection.vendor == 'oracle', "Oracle doesn't support BitLength.")
    def test_expressions(self):
        author = Author.objects.annotate(bit_length=BitLength(Reverse('name'))).get(pk=self.python.pk)
        self.assertEqual(author.bit_length, 96)
        with register_lookup(CharField, BitLength), register_lookup(CharField, Reverse):
            authors = Author.objects.all()
            self.assertCountEqual(authors.filter(name__reverse__bit_length__gt=100), [self.elena])
            self.assertCountEqual(authors.exclude(name__reverse__bit_length__gt=100), [self.john, self.python])

    @unittest.skipIf(connection.vendor == 'oracle', "Oracle doesn't support BitLength.")
    def test_ordering(self):
        authors = Author.objects.order_by(BitLength('name'))
        self.assertSequenceEqual(authors, [self.john, self.python, self.elena])

    @unittest.skipUnless(connection.vendor == 'oracle', "Oracle doesn't support BitLength.")
    def test_unsupported(self):
        msg = 'BitLength is not supported on Oracle.'
        with self.assertRaisesMessage(NotSupportedError, msg):
            Author.objects.annotate(name_bit_length=BitLength('name')).first()
