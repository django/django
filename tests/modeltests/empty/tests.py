from django.test import TestCase

from models import Empty


class EmptyModelTests(TestCase):
    def test_empty(self):
        m = Empty()
        self.assertEqual(m.id, None)
        m.save()
        m2 = Empty.objects.create()
        self.assertEqual(len(Empty.objects.all()), 2)
        self.assertTrue(m.id is not None)
        existing = Empty(m.id)
        existing.save()
