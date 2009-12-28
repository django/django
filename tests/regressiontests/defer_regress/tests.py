from django.test import TestCase
from models import ResolveThis

class DeferRegressionTest(TestCase):
    def test_resolve_columns(self):
        rt = ResolveThis.objects.create(num=5.0, name='Foobar')
        qs = ResolveThis.objects.defer('num')
        self.assertEqual(1, qs.count())
        self.assertEqual('Foobar', qs[0].name)
