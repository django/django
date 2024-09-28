from django.db import connection
from django.db.models import CharField, Value
from django.db.models.functions import Length, Reverse, Trim
from django.test import TestCase
from django.test.utils import register_lookup

from ..models import Author


class ReverseTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.john = Author.objects.create(name="John Smith", alias="smithj")
        cls.elena = Author.objects.create(name="Élena Jordan", alias="elena")
        cls.python = Author.objects.create(name="パイソン")

    def test_null(self):
        author = Author.objects.annotate(backward=Reverse("alias")).get(
            pk=self.python.pk
        )
        self.assertEqual(
            author.backward,
            "" if connection.features.interprets_empty_strings_as_nulls else None,
        )

    def test_basic(self):
        authors = Author.objects.annotate(
            backward=Reverse("name"),
            constant=Reverse(Value("static string")),
        )
        self.assertQuerySetEqual(
            authors,
            [
                ("John Smith", "htimS nhoJ", "gnirts citats"),
                ("Élena Jordan", "nadroJ anelÉ", "gnirts citats"),
                ("パイソン", "ンソイパ", "gnirts citats"),
            ],
            lambda a: (a.name, a.backward, a.constant),
            ordered=False,
        )

    def test_transform(self):
        with register_lookup(CharField, Reverse):
            authors = Author.objects.all()
            self.assertCountEqual(
                authors.filter(name__reverse=self.john.name[::-1]), [self.john]
            )
            self.assertCountEqual(
                authors.exclude(name__reverse=self.john.name[::-1]),
                [self.elena, self.python],
            )

    def test_expressions(self):
        author = Author.objects.annotate(backward=Reverse(Trim("name"))).get(
            pk=self.john.pk
        )
        self.assertEqual(author.backward, self.john.name[::-1])
        with register_lookup(CharField, Reverse), register_lookup(CharField, Length):
            authors = Author.objects.all()
            self.assertCountEqual(
                authors.filter(name__reverse__length__gt=7), [self.john, self.elena]
            )
            self.assertCountEqual(
                authors.exclude(name__reverse__length__gt=7), [self.python]
            )
