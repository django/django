from freedom.core import management
from freedom.core.checks import run_checks, Error
from freedom.db.models.signals import post_init
from freedom.test import TestCase
from freedom.utils import six


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
        #       See: https://code.freedomproject.com/ticket/20430
        #   * related_name='+' doesn't clash with another '+'
        #       See: https://code.freedomproject.com/ticket/21375
        management.call_command("check", stdout=six.StringIO())

    def test_model_signal(self):
        unresolved_references = post_init.unresolved_references.copy()
        post_init.connect(on_post_init, sender='missing-app.Model')
        post_init.connect(OnPostInit(), sender='missing-app.Model')

        errors = run_checks()
        expected = [
            Error(
                "The 'on_post_init' function was connected to the 'post_init' "
                "signal with a lazy reference to the 'missing-app.Model' "
                "sender, which has not been installed.",
                hint=None,
                obj='model_validation.tests',
                id='signals.E001',
            ),
            Error(
                "An instance of the 'OnPostInit' class was connected to "
                "the 'post_init' signal with a lazy reference to the "
                "'missing-app.Model' sender, which has not been installed.",
                hint=None,
                obj='model_validation.tests',
                id='signals.E001',
            )
        ]
        self.assertEqual(errors, expected)

        post_init.unresolved_references = unresolved_references
