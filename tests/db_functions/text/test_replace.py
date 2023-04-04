from django.db.models import F, Value
from django.db.models.functions import Concat, Replace
from django.test import TestCase

from ..models import Author


class ReplaceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Author.objects.create(name="George R. R. Martin")
        Author.objects.create(name="J. R. R. Tolkien")

    def test_replace_with_empty_string(self):
        qs = Author.objects.annotate(
            without_middlename=Replace(F("name"), Value("R. R. "), Value("")),
        )
        self.assertQuerySetEqual(
            qs,
            [
                ("George R. R. Martin", "George Martin"),
                ("J. R. R. Tolkien", "J. Tolkien"),
            ],
            transform=lambda x: (x.name, x.without_middlename),
            ordered=False,
        )

    def test_case_sensitive(self):
        qs = Author.objects.annotate(
            same_name=Replace(F("name"), Value("r. r."), Value(""))
        )
        self.assertQuerySetEqual(
            qs,
            [
                ("George R. R. Martin", "George R. R. Martin"),
                ("J. R. R. Tolkien", "J. R. R. Tolkien"),
            ],
            transform=lambda x: (x.name, x.same_name),
            ordered=False,
        )

    def test_replace_expression(self):
        qs = Author.objects.annotate(
            same_name=Replace(
                Concat(Value("Author: "), F("name")), Value("Author: "), Value("")
            ),
        )
        self.assertQuerySetEqual(
            qs,
            [
                ("George R. R. Martin", "George R. R. Martin"),
                ("J. R. R. Tolkien", "J. R. R. Tolkien"),
            ],
            transform=lambda x: (x.name, x.same_name),
            ordered=False,
        )

    def test_update(self):
        Author.objects.update(
            name=Replace(F("name"), Value("R. R. "), Value("")),
        )
        self.assertQuerySetEqual(
            Author.objects.all(),
            [
                ("George Martin"),
                ("J. Tolkien"),
            ],
            transform=lambda x: x.name,
            ordered=False,
        )

    def test_replace_with_default_arg(self):
        # The default replacement is an empty string.
        qs = Author.objects.annotate(same_name=Replace(F("name"), Value("R. R. ")))
        self.assertQuerySetEqual(
            qs,
            [
                ("George R. R. Martin", "George Martin"),
                ("J. R. R. Tolkien", "J. Tolkien"),
            ],
            transform=lambda x: (x.name, x.same_name),
            ordered=False,
        )
