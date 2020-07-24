from django.db.models import CharField
from django.db.models.functions import Length, Reverse
from django.test import TestCase
from django.test.utils import register_lookup

from ..models import Author


class LengthTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.john = Author.objects.create(name='John Smith', alias='smithj')
        cls.elena = Author.objects.create(name='Élena Jordan', alias='elena')
        cls.python = Author.objects.create(name='パイソン')

    def test_null(self):
        author = Author.objects.annotate(length=Length('alias')).get(pk=self.python.pk)
        self.assertEqual(author.length, None)

    def test_basic(self):
        authors = Author.objects.annotate(
            name_length=Length('name'),
            alias_length=Length('alias'),
        )
        self.assertQuerysetEqual(
            authors,
            [(10, 6), (12, 5), (4, None)],
            lambda a: (a.name_length, a.alias_length),
            ordered=False,
        )
        self.assertEqual(authors.filter(alias_length__lte=Length('name')).count(), 2)

    def test_transform(self):
        with register_lookup(CharField, Length):
            authors = Author.objects.all()
            self.assertCountEqual(authors.filter(name__length__gt=10), [self.elena])
            self.assertCountEqual(authors.exclude(name__length__gt=10), [self.john, self.python])

    def test_expressions(self):
        author = Author.objects.annotate(length=Length(Reverse('name'))).get(pk=self.python.pk)
        self.assertEqual(author.length, 4)
        with register_lookup(CharField, Length), register_lookup(CharField, Reverse):
            authors = Author.objects.all()
            self.assertCountEqual(authors.filter(name__reverse__length__gt=10), [self.elena])
            self.assertCountEqual(authors.exclude(name__reverse__length__gt=10), [self.john, self.python])

    def test_ordering(self):
        authors = Author.objects.order_by(Length('name'))
        self.assertSequenceEqual(authors, [self.python, self.john, self.elena])
