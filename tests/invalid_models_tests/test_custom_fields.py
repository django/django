from django.db import models

from .base import IsolatedModelsTestCase


class CustomFieldTest(IsolatedModelsTestCase):

    def test_none_column(self):
        class NoColumnField(models.AutoField):
            def db_type(self, connection):
                # None indicates not to create a column in the database.
                return None

        class Model(models.Model):
            field = NoColumnField(primary_key=True, db_column="other_field")
            other_field = models.IntegerField()

        field = Model._meta.get_field('field')
        errors = field.check()
        self.assertEqual(errors, [])
