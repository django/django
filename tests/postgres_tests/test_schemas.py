from django.test import modify_settings

from . import PostgreSQLTestCase
from .models import SchemaModel


@modify_settings(INSTALLED_APPS={'append': 'django.contrib.postgres'})
class SchemaTest(PostgreSQLTestCase):

    Model = SchemaModel

    def setUp(self):
        self.Model.objects.bulk_create([
            self.Model(int1=1),
            self.Model(int1=2),
            self.Model(int1=3),
        ])

    def test_values(self):
        index = 1;
        for object in self.Model.objects.all():
            self.assertEqual(object.int1, index)
            index += 1
