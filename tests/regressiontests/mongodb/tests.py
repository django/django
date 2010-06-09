from django.test import TestCase

from models import Artist


class MongoTestCase(TestCase):
    def test_create(self):
        b = Artist.objects.create(name="Bruce Springsteen", good=True)
        self.assertTrue(b.pk is not None)
        self.assertEqual(b.name, "Bruce Springsteen")
        self.assertTrue(b.good)
