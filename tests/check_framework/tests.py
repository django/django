# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.utils.six import StringIO
import sys

from django.apps import apps
from django.conf import settings
from django.core import checks
from django.core.checks import Error
from django.core.checks.registry import CheckRegistry
from django.core.checks.compatibility.django_1_6_0 import check_1_6_compatibility
from django.core.management.base import CommandError
from django.core.management import call_command
from django.db.models.fields import NOT_PROVIDED
from django.test import TestCase
from django.test.utils import override_settings, override_system_checks
from django.utils.encoding import force_text

from .models import SimpleModel, Book


class DummyObj(object):
    def __repr__(self):
        return "obj"


class SystemCheckFrameworkTests(TestCase):

    def test_register_and_run_checks(self):
        calls = [0]

        registry = CheckRegistry()

        @registry.register()
        def f(**kwargs):
            calls[0] += 1
            return [1, 2, 3]
        errors = registry.run_checks()
        self.assertEqual(errors, [1, 2, 3])
        self.assertEqual(calls[0], 1)


class MessageTests(TestCase):

    def test_printing(self):
        e = Error("Message", hint="Hint", obj=DummyObj())
        expected = "obj: Message\n\tHINT: Hint"
        self.assertEqual(force_text(e), expected)

    def test_printing_no_hint(self):
        e = Error("Message", hint=None, obj=DummyObj())
        expected = "obj: Message"
        self.assertEqual(force_text(e), expected)

    def test_printing_no_object(self):
        e = Error("Message", hint="Hint", obj=None)
        expected = "?: Message\n\tHINT: Hint"
        self.assertEqual(force_text(e), expected)

    def test_printing_with_given_id(self):
        e = Error("Message", hint="Hint", obj=DummyObj(), id="ID")
        expected = "obj: (ID) Message\n\tHINT: Hint"
        self.assertEqual(force_text(e), expected)

    def test_printing_field_error(self):
        field = SimpleModel._meta.get_field('field')
        e = Error("Error", hint=None, obj=field)
        expected = "check_framework.SimpleModel.field: Error"
        self.assertEqual(force_text(e), expected)

    def test_printing_model_error(self):
        e = Error("Error", hint=None, obj=SimpleModel)
        expected = "check_framework.SimpleModel: Error"
        self.assertEqual(force_text(e), expected)

    def test_printing_manager_error(self):
        manager = SimpleModel.manager
        e = Error("Error", hint=None, obj=manager)
        expected = "check_framework.SimpleModel.manager: Error"
        self.assertEqual(force_text(e), expected)


class Django_1_6_0_CompatibilityChecks(TestCase):

    @override_settings(TEST_RUNNER='django.test.runner.DiscoverRunner')
    def test_test_runner_new_default(self):
        errors = check_1_6_compatibility()
        self.assertEqual(errors, [])

    @override_settings(TEST_RUNNER='myapp.test.CustomRunner')
    def test_test_runner_overriden(self):
        errors = check_1_6_compatibility()
        self.assertEqual(errors, [])

    def test_test_runner_not_set_explicitly(self):
        # We remove some settings to make this look like a project generated under Django 1.5.
        old_test_runner = settings._wrapped.TEST_RUNNER
        del settings._wrapped.TEST_RUNNER
        settings._wrapped._explicit_settings.add('MANAGERS')
        settings._wrapped._explicit_settings.add('ADMINS')
        try:
            errors = check_1_6_compatibility()
            expected = [
                checks.Warning(
                    "Some project unittests may not execute as expected.",
                    hint=("Django 1.6 introduced a new default test runner. It looks like "
                          "this project was generated using Django 1.5 or earlier. You should "
                          "ensure your tests are all running & behaving as expected. See "
                          "https://docs.djangoproject.com/en/dev/releases/1.6/#discovery-of-tests-in-any-test-module "
                          "for more information."),
                    obj=None,
                    id='1_6.W001',
                )
            ]
            self.assertEqual(errors, expected)
        finally:
            # Restore settings value
            settings._wrapped.TEST_RUNNER = old_test_runner
            settings._wrapped._explicit_settings.remove('MANAGERS')
            settings._wrapped._explicit_settings.remove('ADMINS')

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
                        'BooleanField does not have a default value. ',
                        hint=('Django 1.6 changed the default value of BooleanField from False to None. '
                              'See https://docs.djangoproject.com/en/1.6/ref/models/fields/#booleanfield '
                              'for more information.'),
                        obj=boolean_field,
                        id='1_6.W002',
                    )
                ]
                self.assertEqual(errors, expected)
            finally:
                # Restore the ``default``
                boolean_field.default = old_default


def simple_system_check(**kwargs):
    simple_system_check.kwargs = kwargs
    return []


def tagged_system_check(**kwargs):
    tagged_system_check.kwargs = kwargs
    return []
tagged_system_check.tags = ['simpletag']


class CheckCommandTests(TestCase):

    def setUp(self):
        simple_system_check.kwargs = None
        tagged_system_check.kwargs = None
        self.old_stdout, self.old_stderr = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = StringIO(), StringIO()

    def tearDown(self):
        sys.stdout, sys.stderr = self.old_stdout, self.old_stderr

    @override_system_checks([simple_system_check, tagged_system_check])
    def test_simple_call(self):
        call_command('check')
        self.assertEqual(simple_system_check.kwargs, {'app_configs': None})
        self.assertEqual(tagged_system_check.kwargs, {'app_configs': None})

    @override_system_checks([simple_system_check, tagged_system_check])
    def test_given_app(self):
        call_command('check', 'auth', 'admin')
        auth_config = apps.get_app_config('auth')
        admin_config = apps.get_app_config('admin')
        self.assertEqual(simple_system_check.kwargs, {'app_configs': [auth_config, admin_config]})
        self.assertEqual(tagged_system_check.kwargs, {'app_configs': [auth_config, admin_config]})

    @override_system_checks([simple_system_check, tagged_system_check])
    def test_given_tag(self):
        call_command('check', tags=['simpletag'])
        self.assertEqual(simple_system_check.kwargs, None)
        self.assertEqual(tagged_system_check.kwargs, {'app_configs': None})

    @override_system_checks([simple_system_check, tagged_system_check])
    def test_invalid_tag(self):
        self.assertRaises(CommandError, call_command, 'check', tags=['missingtag'])


def custom_system_check(app_configs, **kwargs):
    return [
        Error(
            'Error',
            hint=None,
            id='mycheck.E001',
        )
    ]


class SilencingCheckTests(TestCase):

    def setUp(self):
        self.old_stdout, self.old_stderr = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = StringIO(), StringIO()

    def tearDown(self):
        sys.stdout, sys.stderr = self.old_stdout, self.old_stderr

    @override_settings(SILENCED_SYSTEM_CHECKS=['mycheck.E001'])
    @override_system_checks([custom_system_check])
    def test_simple(self):
        try:
            call_command('check')
        except CommandError:
            self.fail("The mycheck.E001 check should be silenced.")
