# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import sys

from django.apps import apps
from django.conf import settings
from django.core import checks
from django.core.checks import Error, Warning
from django.core.checks.compatibility.django_1_7_0 import \
    check_1_7_compatibility
from django.core.checks.registry import CheckRegistry
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import models
from django.test import TestCase
from django.test.utils import override_settings, override_system_checks
from django.utils.encoding import force_text
from django.utils.six import StringIO

from .models import SimpleModel


class DummyObj(object):
    def __repr__(self):
        return "obj"


class SystemCheckFrameworkTests(TestCase):

    def test_register_and_run_checks(self):

        def f(**kwargs):
            calls[0] += 1
            return [1, 2, 3]

        def f2(**kwargs):
            return [4, ]

        def f3(**kwargs):
            return [5, ]

        calls = [0]

        # test register as decorator
        registry = CheckRegistry()
        registry.register()(f)
        registry.register("tag1", "tag2")(f2)
        registry.register("tag2", deploy=True)(f3)

        # test register as function
        registry2 = CheckRegistry()
        registry2.register(f)
        registry2.register(f2, "tag1", "tag2")
        registry2.register(f3, "tag2", deploy=True)

        # check results
        errors = registry.run_checks()
        errors2 = registry2.run_checks()
        self.assertEqual(errors, errors2)
        self.assertEqual(sorted(errors), [1, 2, 3, 4])
        self.assertEqual(calls[0], 2)

        errors = registry.run_checks(tags=["tag1"])
        errors2 = registry2.run_checks(tags=["tag1"])
        self.assertEqual(errors, errors2)
        self.assertEqual(sorted(errors), [4])

        errors = registry.run_checks(tags=["tag1", "tag2"], include_deployment_checks=True)
        errors2 = registry2.run_checks(tags=["tag1", "tag2"], include_deployment_checks=True)
        self.assertEqual(errors, errors2)
        self.assertEqual(sorted(errors), [4, 5])


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


class Django_1_7_0_CompatibilityChecks(TestCase):

    @override_settings(MIDDLEWARE_CLASSES=('django.contrib.sessions.middleware.SessionMiddleware',))
    def test_middleware_classes_overridden(self):
        errors = check_1_7_compatibility()
        self.assertEqual(errors, [])

    def test_middleware_classes_not_set_explicitly(self):
        # If MIDDLEWARE_CLASSES was set explicitly, temporarily pretend it wasn't
        middleware_classes_overridden = False
        if 'MIDDLEWARE_CLASSES' in settings._wrapped._explicit_settings:
            middleware_classes_overridden = True
            settings._wrapped._explicit_settings.remove('MIDDLEWARE_CLASSES')
        try:
            errors = check_1_7_compatibility()
            expected = [
                checks.Warning(
                    "MIDDLEWARE_CLASSES is not set.",
                    hint=("Django 1.7 changed the global defaults for the MIDDLEWARE_CLASSES. "
                          "django.contrib.sessions.middleware.SessionMiddleware, "
                          "django.contrib.auth.middleware.AuthenticationMiddleware, and "
                          "django.contrib.messages.middleware.MessageMiddleware were removed from the defaults. "
                          "If your project needs these middleware then you should configure this setting."),
                    obj=None,
                    id='1_7.W001',
                )
            ]
            self.assertEqual(errors, expected)
        finally:
            # Restore settings value
            if middleware_classes_overridden:
                settings._wrapped._explicit_settings.add('MIDDLEWARE_CLASSES')


def simple_system_check(**kwargs):
    simple_system_check.kwargs = kwargs
    return []


def tagged_system_check(**kwargs):
    tagged_system_check.kwargs = kwargs
    return []
tagged_system_check.tags = ['simpletag']


def deployment_system_check(**kwargs):
    deployment_system_check.kwargs = kwargs
    return [checks.Warning('Deployment Check')]
deployment_system_check.tags = ['deploymenttag']


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

    @override_system_checks([simple_system_check])
    def test_list_tags_empty(self):
        call_command('check', list_tags=True)
        self.assertEqual('\n', sys.stdout.getvalue())

    @override_system_checks([tagged_system_check])
    def test_list_tags(self):
        call_command('check', list_tags=True)
        self.assertEqual('simpletag\n', sys.stdout.getvalue())

    @override_system_checks([tagged_system_check], deployment_checks=[deployment_system_check])
    def test_list_deployment_check_omitted(self):
        call_command('check', list_tags=True)
        self.assertEqual('simpletag\n', sys.stdout.getvalue())

    @override_system_checks([tagged_system_check], deployment_checks=[deployment_system_check])
    def test_list_deployment_check_included(self):
        call_command('check', deploy=True, list_tags=True)
        self.assertEqual('deploymenttag\nsimpletag\n', sys.stdout.getvalue())

    @override_system_checks([tagged_system_check], deployment_checks=[deployment_system_check])
    def test_tags_deployment_check_omitted(self):
        msg = 'There is no system check with the "deploymenttag" tag.'
        with self.assertRaisesMessage(CommandError, msg):
            call_command('check', tags=['deploymenttag'])

    @override_system_checks([tagged_system_check], deployment_checks=[deployment_system_check])
    def test_tags_deployment_check_included(self):
        call_command('check', deploy=True, tags=['deploymenttag'])
        self.assertIn('Deployment Check', sys.stderr.getvalue())


def custom_error_system_check(app_configs, **kwargs):
    return [
        Error(
            'Error',
            hint=None,
            id='myerrorcheck.E001',
        )
    ]


def custom_warning_system_check(app_configs, **kwargs):
    return [
        Warning(
            'Warning',
            hint=None,
            id='mywarningcheck.E001',
        )
    ]


class SilencingCheckTests(TestCase):

    def setUp(self):
        self.old_stdout, self.old_stderr = sys.stdout, sys.stderr
        self.stdout, self.stderr = StringIO(), StringIO()
        sys.stdout, sys.stderr = self.stdout, self.stderr

    def tearDown(self):
        sys.stdout, sys.stderr = self.old_stdout, self.old_stderr

    @override_settings(SILENCED_SYSTEM_CHECKS=['myerrorcheck.E001'])
    @override_system_checks([custom_error_system_check])
    def test_silenced_error(self):
        out = StringIO()
        err = StringIO()
        try:
            call_command('check', stdout=out, stderr=err)
        except CommandError:
            self.fail("The mycheck.E001 check should be silenced.")
        self.assertEqual(out.getvalue(), '')
        self.assertEqual(
            err.getvalue(),
            'System check identified some issues:\n\n'
            'ERRORS:\n'
            '?: (myerrorcheck.E001) Error\n\n'
            'System check identified 1 issue (0 silenced).\n'
        )

    @override_settings(SILENCED_SYSTEM_CHECKS=['mywarningcheck.E001'])
    @override_system_checks([custom_warning_system_check])
    def test_silenced_warning(self):
        out = StringIO()
        err = StringIO()
        try:
            call_command('check', stdout=out, stderr=err)
        except CommandError:
            self.fail("The mycheck.E001 check should be silenced.")

        self.assertEqual(out.getvalue(), 'System check identified no issues (1 silenced).\n')
        self.assertEqual(err.getvalue(), '')


class IsolateModelsMixin(object):
    def setUp(self):
        self.current_models = apps.all_models[__package__]
        self.saved_models = set(self.current_models)

    def tearDown(self):
        for model in (set(self.current_models) - self.saved_models):
            del self.current_models[model]
        apps.clear_cache()


class CheckFrameworkReservedNamesTests(IsolateModelsMixin, TestCase):
    @override_settings(
        SILENCED_SYSTEM_CHECKS=['models.E20', 'fields.W342'],  # ForeignKey(unique=True)
        INSTALLED_APPS=['django.contrib.auth', 'django.contrib.contenttypes', 'check_framework']
    )
    def test_model_check_method_not_shadowed(self):
        class ModelWithAttributeCalledCheck(models.Model):
            check = 42

        class ModelWithFieldCalledCheck(models.Model):
            check = models.IntegerField()

        class ModelWithRelatedManagerCalledCheck(models.Model):
            pass

        class ModelWithDescriptorCalledCheck(models.Model):
            check = models.ForeignKey(ModelWithRelatedManagerCalledCheck)
            article = models.ForeignKey(ModelWithRelatedManagerCalledCheck, related_name='check')

        errors = checks.run_checks()
        expected = [
            Error(
                "The 'ModelWithAttributeCalledCheck.check()' class method is "
                "currently overridden by 42.",
                hint=None,
                obj=ModelWithAttributeCalledCheck,
                id='models.E020'
            ),
            Error(
                "The 'ModelWithRelatedManagerCalledCheck.check()' class method is "
                "currently overridden by %r." % ModelWithRelatedManagerCalledCheck.check,
                hint=None,
                obj=ModelWithRelatedManagerCalledCheck,
                id='models.E020'
            ),
            Error(
                "The 'ModelWithDescriptorCalledCheck.check()' class method is "
                "currently overridden by %r." % ModelWithDescriptorCalledCheck.check,
                hint=None,
                obj=ModelWithDescriptorCalledCheck,
                id='models.E020'
            ),
        ]
        self.assertEqual(errors, expected)
