from django.core import management
from django.core.management.validation import (
    ModelErrorCollection, validate_model_signals
)
from django.db.models.signals import post_init
from django.test import TestCase
from django.utils import six


class OnPostInit(object):
    def __call__(self, **kwargs):
        pass


def on_post_init(**kwargs):
    pass


class ModelValidationTest(TestCase):
    def test_models_validate(self):
        # All our models should validate properly
        # Validation Tests:
        #   * choices= Iterable of Iterables
        #       See: https://code.djangoproject.com/ticket/20430
        #   * related_name='+' doesn't clash with another '+'
        #       See: https://code.djangoproject.com/ticket/21375
        management.call_command("validate", stdout=six.StringIO())

    def test_model_signal(self):
        unresolved_references = post_init.unresolved_references.copy()
        post_init.connect(on_post_init, sender='missing-app.Model')
        post_init.connect(OnPostInit(), sender='missing-app.Model')
        e = ModelErrorCollection(six.StringIO())
        validate_model_signals(e)
        self.assertSetEqual(set(e.errors), {
            ('model_validation.tests',
                "The `on_post_init` function was connected to the `post_init` "
                "signal with a lazy reference to the 'missing-app.Model' "
                "sender, which has not been installed."
            ),
            ('model_validation.tests',
                "An instance of the `OnPostInit` class was connected to "
                "the `post_init` signal with a lazy reference to the "
                "'missing-app.Model' sender, which has not been installed."
            )
        })
        post_init.unresolved_references = unresolved_references
