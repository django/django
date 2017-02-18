from django.test import TestCase

from .models import Empty


class EmptyModelTests(TestCase):
    def test_empty(self):
        m = Empty()
        self.assertIsNone(m.id)
        m.save()
        Empty.objects.create()
        self.assertEqual(len(Empty.objects.all()), 2)
        self.assertIsNotNone(m.id)
        existing = Empty(m.id)
        existing.save()
