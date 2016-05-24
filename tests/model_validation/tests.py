from django.core import management
from django.core.checks import Error
from django.core.checks.model_checks import _check_lazy_references
from django.db import models
from django.db.models.signals import post_init
from django.test import SimpleTestCase
from django.test.utils import isolate_apps, override_settings
from django.utils import six


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

    @isolate_apps('django.contrib.auth', kwarg_name='apps')
    def test_lazy_reference_checks(self, apps):

        class DummyModel(models.Model):
            author = models.ForeignKey('Author', models.CASCADE)

            class Meta:
                app_label = "model_validation"

        class DummyClass(object):
            def __call__(self, **kwargs):
                pass

            def dummy_method(self):
                pass

        def dummy_function(*args, **kwargs):
            pass

        apps.lazy_model_operation(dummy_function, ('auth', 'imaginarymodel'))
        apps.lazy_model_operation(dummy_function, ('fanciful_app', 'imaginarymodel'))

        post_init.connect(dummy_function, sender='missing-app.Model', apps=apps)
        post_init.connect(DummyClass(), sender='missing-app.Model', apps=apps)
        post_init.connect(DummyClass().dummy_method, sender='missing-app.Model', apps=apps)

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
                "An instance of class 'DummyClass' was connected to "
                "the 'post_init' signal with a lazy reference to the sender "
                "'missing-app.model', but app 'missing-app' isn't installed.",
                hint=None,
                obj='model_validation.tests',
                id='signals.E001',
            ),
            Error(
                "Bound method 'DummyClass.dummy_method' was connected to the "
                "'post_init' signal with a lazy reference to the sender "
                "'missing-app.model', but app 'missing-app' isn't installed.",
                hint=None,
                obj='model_validation.tests',
                id='signals.E001',
            ),
            Error(
                "The field model_validation.DummyModel.author was declared "
                "with a lazy reference to 'model_validation.author', but app "
                "'model_validation' isn't installed.",
                hint=None,
                obj=DummyModel.author.field,
                id='fields.E307',
            ),
            Error(
                "The function 'dummy_function' was connected to the 'post_init' "
                "signal with a lazy reference to the sender "
                "'missing-app.model', but app 'missing-app' isn't installed.",
                hint=None,
                obj='model_validation.tests',
                id='signals.E001',
            ),
        ]
        self.assertEqual(errors, expected)
