from django.core import management
from django.test import TestCase
from django.utils import six


class ModelValidationTest(TestCase):

    def test_models_validate(self):
        # All our models should validate properly
        # Validation Tests:
        #   * choices= Iterable of Iterables
        #       See: https://code.djangoproject.com/ticket/20430
        management.call_command("validate", stdout=six.StringIO())
