import datetime

from django.test import TestCase

from models import Book

class LargeDeleteTests(TestCase):
    def test_large_deletes(self):
        "Regression for #13309 -- if the number of objects > chunk size, deletion still occurs"
        for x in range(300):
            track = Book.objects.create(pagecount=x+100)
        Book.objects.all().delete()
        self.assertEquals(Book.objects.count(), 0)
