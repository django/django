from django.db import connection, models
from django.test import SimpleTestCase


class CustomFieldTests(SimpleTestCase):

    def test_get_prep_value_count(self):
        """
        Field values are not prepared twice in get_db_prep_lookup() (#14786).
        """
        class NoopField(models.TextField):
            def __init__(self, *args, **kwargs):
                self.prep_value_count = 0
                super(NoopField, self).__init__(*args, **kwargs)

            def get_prep_value(self, value):
                self.prep_value_count += 1
                return super(NoopField, self).get_prep_value(value)

        field = NoopField()
        field.get_db_prep_lookup('exact', 'TEST', connection=connection, prepared=False)
        self.assertEqual(field.prep_value_count, 1)
