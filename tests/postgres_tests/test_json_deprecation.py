try:
    from django.contrib.postgres import forms
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
