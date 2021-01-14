try:
    from django.contrib.postgres import forms
    from django.contrib.postgres.fields.jsonb import (
        KeyTextTransform, KeyTransform,
    )
except ImportError:
    pass

from django.utils.deprecation import RemovedInDjango40Warning

from . import PostgreSQLSimpleTestCase


class DeprecationTests(PostgreSQLSimpleTestCase):
    def test_form_field_deprecation_message(self):
        msg = (
            'django.contrib.postgres.forms.JSONField is deprecated in favor '
            'of django.forms.JSONField.'
        )
        with self.assertWarnsMessage(RemovedInDjango40Warning, msg):
            forms.JSONField()

    def test_key_transform_deprecation_message(self):
        msg = (
            'django.contrib.postgres.fields.jsonb.KeyTransform is deprecated '
            'in favor of django.db.models.fields.json.KeyTransform.'
        )
        with self.assertWarnsMessage(RemovedInDjango40Warning, msg):
            KeyTransform('foo', 'bar')

    def test_key_text_transform_deprecation_message(self):
        msg = (
            'django.contrib.postgres.fields.jsonb.KeyTextTransform is '
            'deprecated in favor of '
            'django.db.models.fields.json.KeyTextTransform.'
        )
        with self.assertWarnsMessage(RemovedInDjango40Warning, msg):
            KeyTextTransform('foo', 'bar')
