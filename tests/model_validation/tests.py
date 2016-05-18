from django.core import management
from django.core.checks import Error, run_checks
from django.core.checks.model_checks import _check_lazy_references
from django.db import models
from django.db.models.signals import post_init
from django.test import SimpleTestCase
from django.test.utils import isolate_apps, override_settings
from django.utils import six


class OnPostInit(object):
    def __call__(self, **kwargs):
        pass


def on_post_init(**kwargs):
    pass


def dummy_function(model):
    pass


@override_settings(
    INSTALLED_APPS=['django.contrib.auth', 'django.contrib.contenttypes'],
    SILENCED_SYSTEM_CHECKS=['fields.W342'],  # ForeignKey(unique=True)
)
class ModelValidationTest(SimpleTestCase):
    def test_models_validate(self):
        # All our models should validate properly
        # Validation Tests:
        #   * choices= Iterable of Iterables
        #       See: https://code.djangoproject.com/ticket/20430
        #   * related_name='+' doesn't clash with another '+'
        #       See: https://code.djangoproject.com/ticket/21375
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
                obj='model_validation.tests',
                id='signals.E001',
            ),
            Error(
                "An instance of the 'OnPostInit' class was connected to "
                "the 'post_init' signal with a lazy reference to the "
                "'missing-app.Model' sender, which has not been installed.",
                obj='model_validation.tests',
                id='signals.E001',
            )
        ]
        self.assertEqual(errors, expected)

        post_init.unresolved_references = unresolved_references

    @isolate_apps('django.contrib.auth', kwarg_name='apps')
    def test_lazy_reference_checks(self, apps):

        class DummyModel(models.Model):
            author = models.ForeignKey('Author', models.CASCADE)

            class Meta:
                app_label = "model_validation"

        apps.lazy_model_operation(dummy_function, ('auth', 'imaginarymodel'))
        apps.lazy_model_operation(dummy_function, ('fanciful_app', 'imaginarymodel'))

        errors = _check_lazy_references(apps)

        expected = [
            Error(
                "%r contains a lazy reference to auth.imaginarymodel, "
                "but app 'auth' doesn't provide model 'imaginarymodel'." % dummy_function,
                obj=dummy_function,
                id='models.E022',
            ),
            Error(
                "%r contains a lazy reference to fanciful_app.imaginarymodel, "
                "but app 'fanciful_app' isn't installed." % dummy_function,
                obj=dummy_function,
                id='models.E022',
            ),
            Error(
                "The field model_validation.DummyModel.author was declared "
                "with a lazy reference to 'model_validation.author', but app "
                "'model_validation' isn't installed.",
                hint=None,
                obj=DummyModel.author.field,
                id='fields.E307',
            ),
        ]

        self.assertEqual(errors, expected)
