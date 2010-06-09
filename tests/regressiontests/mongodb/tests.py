from django.test import TestCase

from models import Artist


class MongoTestCase(TestCase):
    def test_create(self):
        b = Artist.objects.create(name="Bruce Springsteen", good=True)
        self.assertTrue(b.pk is not None)
        self.assertEqual(b.name, "Bruce Springsteen")
        self.assertTrue(b.good)
    
    def test_update(self):
        l = Artist.objects.create(name="Lady Gaga", good=True)
        self.assertTrue(l.pk is not None)
        pk = l.pk
        # Whoops, we screwed up.
        l.good = False
        l.save()
        self.assertEqual(l.pk, pk)
