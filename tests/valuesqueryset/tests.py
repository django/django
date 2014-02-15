from __future__ import unicode_literals

from django.test import TestCase

from .models import ValuesTestModel


class ValuesQuerySetTestCase(TestCase):

    def setUp(self):
        obj = ValuesTestModel(
            field_a = 'A',
            field_b = 1,
            field_c = 'A1',
            )
        obj.save()

    def test_values(self):
        """
        test ValuesQuerySet values
        """

        self.assertEqual(list(ValuesTestModel.objects.values()),
            [{'field_a':'A', 'field_b':1, 'field_c':'A1', 'id':1},])

        self.assertEqual(list(ValuesTestModel.objects.values().only('field_b')),
            [{'field_b':1}])

        self.assertEqual(list(ValuesTestModel.objects.only('field_b').values()),
            [{'field_a': u'A', 'field_b': 1, 'field_c': u'A1', u'id': 1}])


        self.assertEqual(list(ValuesTestModel.objects.values().defer('field_b')),
            [{'field_a':'A', 'field_c':'A1', 'id':1}])

        self.assertEqual(list(ValuesTestModel.objects.values('field_a').only('field_b')),
            [{'field_b':1}])

        self.assertEqual(list(ValuesTestModel.objects.values().defer('field_a').defer('field_b')),
            [{'field_c': 'A1', 'id':1}])
