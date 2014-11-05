from django.db import connection, models

from .base import IsolatedModelsTestCase
from .fields import NoColumnField


class CustomFieldTest(IsolatedModelsTestCase):

    def test_none_column(self):
        class Model(models.Model):
            field = NoColumnField(primary_key=True, db_column="other_field")
            other_field = models.IntegerField()

        field = Model._meta.get_field('field')
        errors = field.check()
        expected = []
        self.assertEqual(errors, expected)
