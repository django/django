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

    def test_str(self):
        m = Empty.objects.create()
        result = str(m)
        self.assertIsInstance(result, str)

    def test_repr(self):
        m = Empty.objects.create()
        result = repr(m)
        self.assertIn("Empty", result)

    def test_delete(self):
        m = Empty.objects.create()
        pk = m.pk
        m.delete()
        self.assertFalse(Empty.objects.filter(pk=pk).exists())

    def test_refresh_from_db(self):
        m = Empty.objects.create()
        m.refresh_from_db()
        self.assertIsNotNone(m.pk)

    def test_bulk_create(self):
        objs = Empty.objects.bulk_create([Empty(), Empty(), Empty()])
        self.assertEqual(len(objs), 3)
        self.assertEqual(Empty.objects.count(), 3)

    def test_queryset_count(self):
        Empty.objects.create()
        Empty.objects.create()
        self.assertEqual(Empty.objects.count(), 2)
