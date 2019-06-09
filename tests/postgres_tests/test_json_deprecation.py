try:
    from django.contrib.postgres.fields import JSONField as ModelJSONField
    from django.contrib.postgres.forms import JSONField as FormJSONField
except ImportError:
    pass

from django.utils.deprecation import RemovedInDjango40Warning

from . import PostgreSQLSimpleTestCase
from .models import PostgreSQLModel


class DeprecationTests(PostgreSQLSimpleTestCase):
    def test_model_field_deprecation_message(self):
        warning = {
            'msg': (
                'django.contrib.postgres.fields.JSONField is deprecated '
                'and will be removed in Django 4.0.'
            ),
            'hint': 'Use django.db.models.JSONField instead.',
            'id': 'fields.W903',
        }

        class PostgreSQLJSONModel(PostgreSQLModel):
            field = ModelJSONField()
        warnings = PostgreSQLJSONModel().check()
        self.assertEqual(warnings[0].msg, warning['msg'])
        self.assertEqual(warnings[0].hint, warning['hint'])
        self.assertEqual(warnings[0].id, warning['id'])

    def test_form_field_deprecation_message(self):
        msg = (
            'django.contrib.postgres.forms.JSONField is deprecated in favor of '
            'django.forms.JSONField'
        )
        with self.assertWarnsMessage(RemovedInDjango40Warning, msg):
            FormJSONField()
