"""
The citext PostgreSQL extension supports indexing of case-insensitive text
strings and thus eliminates the need for operations such as iexact and other
modifiers to enforce use of an index.
"""
from django.db import IntegrityError

from . import PostgreSQLTestCase
from .models import CITextTestModel


class CITextTestCase(PostgreSQLTestCase):

    @classmethod
    def setUpTestData(cls):
        CITextTestModel.objects.create(name='JoHn')

    def test_equal_lowercase(self):
        """
        citext removes the need for iexact as the index is case-insensitive.
        """
        self.assertEqual(CITextTestModel.objects.filter(name='john').count(), 1)

    def test_fail_case(self):
        """
        Creating an entry for a citext-field which clashes with an existing
        value isn't allowed.
        """
        with self.assertRaises(IntegrityError):
            CITextTestModel.objects.create(name='John')
