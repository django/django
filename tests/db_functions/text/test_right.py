from django.db.models import IntegerField, Value
from django.db.models.functions import Lower, Right
from django.test import TestCase

from ..models import Author


class RightTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Author.objects.create(name='John Smith', alias='smithj')
        Author.objects.create(name='Rhonda')

    def test_basic(self):
        authors = Author.objects.annotate(name_part=Right('name', 5))
        self.assertQuerysetEqual(authors.order_by('name'), ['Smith', 'honda'], lambda a: a.name_part)
        # If alias is null, set it to the first 2 lower characters of the name.
        Author.objects.filter(alias__isnull=True).update(alias=Lower(Right('name', 2)))
        self.assertQuerysetEqual(authors.order_by('name'), ['smithj', 'da'], lambda a: a.alias)

    def test_invalid_length(self):
        with self.assertRaisesMessage(ValueError, "'length' must be greater than 0"):
            Author.objects.annotate(raises=Right('name', 0))

    def test_expressions(self):
        authors = Author.objects.annotate(name_part=Right('name', Value(3, output_field=IntegerField())))
        self.assertQuerysetEqual(authors.order_by('name'), ['ith', 'nda'], lambda a: a.name_part)
