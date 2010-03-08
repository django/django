from django.test import TestCase

from models import DataModel


class CustomField(TestCase):
    def test_defer(self):
        d = DataModel.objects.create(data=[1, 2, 3])

        self.failUnless(isinstance(d.data, list))

        d = DataModel.objects.get(pk=d.pk)
        self.failUnless(isinstance(d.data, list))
        self.assertEqual(d.data, [1, 2, 3])

        d = DataModel.objects.defer("data").get(pk=d.pk)
        d.save()

        d = DataModel.objects.get(pk=d.pk)
        self.failUnless(isinstance(d.data, list))
        self.assertEqual(d.data, [1, 2, 3])
