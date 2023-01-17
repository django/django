import unittest
from datetime import date

from django import db
from django.db.models import Value
from django.db.models.functions.datetime import ToDate
from django.test import TestCase, override_settings

from ..models import Author


@override_settings(USE_TZ=False)
class ToDateFunctionTests(TestCase):
    @unittest.skipIf(db.connection.vendor == "sqlite", "SQLite is not supported")
    def test_to_date_func(self):
        author = Author.objects.create(name="Jacques Derrida", bio="10 Feb 2017")
        self.assertIsNone(author.joined)
        if db.connection.vendor == "mysql":
            date_format = "%d %b %Y"
        elif db.connection.vendor == "oracle":
            date_format = "DD MON YYYY"
        else:
            date_format = "DD Mon YYYY"
        Author.objects.filter(pk=author.pk).update(
            joined=ToDate("bio", Value(date_format))
        )
        author.refresh_from_db()
        self.assertEqual(author.joined, date(2017, 2, 10))
