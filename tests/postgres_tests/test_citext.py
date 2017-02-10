"""
The citext PostgreSQL extension supports indexing of case-insensitive text
strings and thus eliminates the need for operations such as iexact and other
modifiers to enforce use of an index.
"""
from django.db import IntegrityError

from . import PostgreSQLTestCase
from .models import CITestModel


class CITextTestCase(PostgreSQLTestCase):

    @classmethod
    def setUpTestData(cls):
        cls.john = CITestModel.objects.create(
            name='JoHn',
            email='joHn@johN.com',
            description='Average Joe named JoHn',
        )

    def test_equal_lowercase(self):
        """
        citext removes the need for iexact as the index is case-insensitive.
        """
        self.assertEqual(CITestModel.objects.filter(name=self.john.name.lower()).count(), 1)
        self.assertEqual(CITestModel.objects.filter(email=self.john.email.lower()).count(), 1)
        self.assertEqual(CITestModel.objects.filter(description=self.john.description.lower()).count(), 1)

    def test_fail_citext_primary_key(self):
        """
        Creating an entry for a citext field used as a primary key which
        clashes with an existing value isn't allowed.
        """
        with self.assertRaises(IntegrityError):
            CITestModel.objects.create(name='John')
