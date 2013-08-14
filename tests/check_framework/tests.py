# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.core import checks
from django.core.checks import Error
from django.core.checks.messages import CheckMessage
from django.core.checks.registration import CheckFramework
from django.core.checks.default_checks import check_1_6_compatibility
from django.db.models.fields import NOT_PROVIDED
from django.test import TestCase
from django.test.utils import override_settings
from django.utils.encoding import force_str

from .models import SimpleModel, Book


class SystemCheckFrameworkTests(TestCase):

    def test_register_and_run_checks(self):
        calls = [0]

        def f(**kwargs):
            calls[0] += 1
            return [1, 2, 3]
        framework = CheckFramework()
        framework.register(f)
        errors = framework.run_checks()
        self.assertEqual(errors, [1, 2, 3])
        self.assertEqual(calls[0], 1)


class DummyObj(object):
    def __repr__(self):
        return "obj"


class MessageTests(TestCase):

    def test_printing(self):
        e = Error("Message", hint="Hint", obj=DummyObj())
        expected = "obj: Message\n\tHINT: Hint"
        self.assertEqual(force_str(e), expected)

    def test_printing_no_hint(self):
        e = Error("Message", hint=None, obj=DummyObj())
        expected = "obj: Message"
        self.assertEqual(force_str(e), expected)

    def test_printing_no_object(self):
        e = Error("Message", hint="Hint", obj=None)
        expected = "?: Message\n\tHINT: Hint"
        self.assertEqual(force_str(e), expected)

    def test_printing_field_error(self):
        field = SimpleModel._meta.get_field('field')
        e = Error("Error", hint=None, obj=field)
        expected = "check_framework.SimpleModel.field: Error"
        self.assertEqual(force_str(e), expected)

    def test_printing_model_error(self):
        e = Error("Error", hint=None, obj=SimpleModel)
        expected = "check_framework.SimpleModel: Error"
        self.assertEqual(force_str(e), expected)

    def test_printing_manager_error(self):
        manager = SimpleModel.manager
        e = Error("Error", hint=None, obj=manager)
        expected = "check_framework.SimpleModel.manager: Error"
        self.assertEqual(force_str(e), expected)

    def test_is_error(self):
        e = CheckMessage(40, "Error", hint=None)
        self.assertTrue(e.is_error())


class Compatibility_1_6_Checks(TestCase):

    @override_settings(TEST_RUNNER='django.test.runner.DiscoverRunner')
    def test_test_runner_new_default(self):
        errors = check_1_6_compatibility()
        self.assertEqual(errors, [])

    @override_settings(TEST_RUNNER='myapp.test.CustomRunner')
    def test_test_runner_overriden(self):
        errors = check_1_6_compatibility()
        self.assertEqual(errors, [])

    def test_test_runner_not_set_explicitly(self):
        # We remove the TEST_RUNNER attribute from custom settings module.
        old_test_runner = settings.RAW_SETTINGS_MODULE.TEST_RUNNER
        del settings.RAW_SETTINGS_MODULE.TEST_RUNNER

        try:
            errors = check_1_6_compatibility()
            expected = [
                checks.Warning(
                   'You have not explicitly set "TEST_RUNNER". In Django 1.6, '
                        'there is a new test runner ("django.test.runner.DiscoverRunner") '
                        'by default. You should ensure your tests are still all '
                        'running & behaving as expected. See '
                        'https://docs.djangoproject.com/en/dev/releases/1.6/#discovery-of-tests-in-any-test-module '
                        'for more information.',
                    hint=None,
                    obj=None,
                )
            ]
            self.assertEqual(errors, expected)
        finally:
            # Restore TEST_RUNNER value
            settings.RAW_SETTINGS_MODULE.TEST_RUNNER = old_test_runner

    def test_boolean_field_default_value(self):
        with self.settings(TEST_RUNNER='myapp.test.CustomRunnner'):
            # We patch the field's default value to trigger the warning
            boolean_field = Book._meta.get_field('is_published')
            old_default = boolean_field.default
            try:
                boolean_field.default = NOT_PROVIDED
                errors = check_1_6_compatibility()
                expected = [
                    checks.Warning(
                        'The field has not set a default value. In Django 1.6 '
                            'the default value of BooleanField was changed from '
                            'False to Null when Field.default is not defined. '
                            'See https://docs.djangoproject.com/en/1.6/ref/models/fields/#booleanfield '
                            'for more information.',
                        hint=None,
                        obj=boolean_field,
                    )
                ]
                self.assertEqual(errors, expected)
            finally:
                # Restore the ``default``
                boolean_field.default = old_default