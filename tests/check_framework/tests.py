import sys

from django.apps import apps
from django.core import checks
from django.core.checks import Error, Warning
from django.core.checks.registry import CheckRegistry
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import models
from django.test import SimpleTestCase
from django.test.utils import (
    isolate_apps, override_settings, override_system_checks,
)
from django.utils.encoding import force_text
from django.utils.six import StringIO

from .models import SimpleModel, my_check


class DummyObj(object):
    def __repr__(self):
        return "obj"


class SystemCheckFrameworkTests(SimpleTestCase):

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


class MessageTests(SimpleTestCase):

    def test_printing(self):
        e = Error("Message", hint="Hint", obj=DummyObj())
        expected = "obj: Message\n\tHINT: Hint"
        self.assertEqual(force_text(e), expected)

    def test_printing_no_hint(self):
        e = Error("Message", obj=DummyObj())
        expected = "obj: Message"
        self.assertEqual(force_text(e), expected)

    def test_printing_no_object(self):
        e = Error("Message", hint="Hint")
        expected = "?: Message\n\tHINT: Hint"
        self.assertEqual(force_text(e), expected)

    def test_printing_with_given_id(self):
        e = Error("Message", hint="Hint", obj=DummyObj(), id="ID")
        expected = "obj: (ID) Message\n\tHINT: Hint"
        self.assertEqual(force_text(e), expected)

    def test_printing_field_error(self):
        field = SimpleModel._meta.get_field('field')
        e = Error("Error", obj=field)
        expected = "check_framework.SimpleModel.field: Error"
        self.assertEqual(force_text(e), expected)

    def test_printing_model_error(self):
        e = Error("Error", obj=SimpleModel)
        expected = "check_framework.SimpleModel: Error"
        self.assertEqual(force_text(e), expected)

    def test_printing_manager_error(self):
        manager = SimpleModel.manager
        e = Error("Error", obj=manager)
        expected = "check_framework.SimpleModel.manager: Error"
        self.assertEqual(force_text(e), expected)

    def test_equal_to_self(self):
        e = Error("Error", obj=SimpleModel)
        self.assertEqual(e, e)

    def test_equal_to_same_constructed_check(self):
        e1 = Error("Error", obj=SimpleModel)
        e2 = Error("Error", obj=SimpleModel)
        self.assertEqual(e1, e2)

    def test_not_equal_to_different_constructed_check(self):
        e1 = Error("Error", obj=SimpleModel)
        e2 = Error("Error2", obj=SimpleModel)
        self.assertNotEqual(e1, e2)

    def test_not_equal_to_non_check(self):
        e = Error("Error", obj=DummyObj())
        self.assertNotEqual(e, 'a string')


def simple_system_check(**kwargs):
    simple_system_check.kwargs = kwargs
    return []


def tagged_system_check(**kwargs):
    tagged_system_check.kwargs = kwargs
    return [checks.Warning('System Check')]


tagged_system_check.tags = ['simpletag']


def deployment_system_check(**kwargs):
    deployment_system_check.kwargs = kwargs
    return [checks.Warning('Deployment Check')]


deployment_system_check.tags = ['deploymenttag']


class CheckCommandTests(SimpleTestCase):

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
        self.assertIsNone(simple_system_check.kwargs)
        self.assertEqual(tagged_system_check.kwargs, {'app_configs': None})

    @override_system_checks([simple_system_check, tagged_system_check])
    def test_invalid_tag(self):
        with self.assertRaises(CommandError):
            call_command('check', tags=['missingtag'])

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

    @override_system_checks([tagged_system_check])
    def test_fail_level(self):
        with self.assertRaises(CommandError):
            call_command('check', fail_level='WARNING')


def custom_error_system_check(app_configs, **kwargs):
    return [Error('Error', id='myerrorcheck.E001')]


def custom_warning_system_check(app_configs, **kwargs):
    return [Warning('Warning', id='mywarningcheck.E001')]


class SilencingCheckTests(SimpleTestCase):

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
        call_command('check', stdout=out, stderr=err)
        self.assertEqual(out.getvalue(), 'System check identified no issues (1 silenced).\n')
        self.assertEqual(err.getvalue(), '')

    @override_settings(SILENCED_SYSTEM_CHECKS=['mywarningcheck.E001'])
    @override_system_checks([custom_warning_system_check])
    def test_silenced_warning(self):
        out = StringIO()
        err = StringIO()
        call_command('check', stdout=out, stderr=err)
        self.assertEqual(out.getvalue(), 'System check identified no issues (1 silenced).\n')
        self.assertEqual(err.getvalue(), '')


class CheckFrameworkReservedNamesTests(SimpleTestCase):
    @isolate_apps('check_framework', kwarg_name='apps')
    @override_system_checks([checks.model_checks.check_all_models])
    def test_model_check_method_not_shadowed(self, apps):
        class ModelWithAttributeCalledCheck(models.Model):
            check = 42

        class ModelWithFieldCalledCheck(models.Model):
            check = models.IntegerField()

        class ModelWithRelatedManagerCalledCheck(models.Model):
            pass

        class ModelWithDescriptorCalledCheck(models.Model):
            check = models.ForeignKey(ModelWithRelatedManagerCalledCheck, models.CASCADE)
            article = models.ForeignKey(
                ModelWithRelatedManagerCalledCheck,
                models.CASCADE,
                related_name='check',
            )

        errors = checks.run_checks(app_configs=apps.get_app_configs())
        expected = [
            Error(
                "The 'ModelWithAttributeCalledCheck.check()' class method is "
                "currently overridden by 42.",
                obj=ModelWithAttributeCalledCheck,
                id='models.E020'
            ),
            Error(
                "The 'ModelWithRelatedManagerCalledCheck.check()' class method is "
                "currently overridden by %r." % ModelWithRelatedManagerCalledCheck.check,
                obj=ModelWithRelatedManagerCalledCheck,
                id='models.E020'
            ),
            Error(
                "The 'ModelWithDescriptorCalledCheck.check()' class method is "
                "currently overridden by %r." % ModelWithDescriptorCalledCheck.check,
                obj=ModelWithDescriptorCalledCheck,
                id='models.E020'
            ),
        ]
        self.assertEqual(errors, expected)


class ChecksRunDuringTests(SimpleTestCase):
    def test_registered_check_did_run(self):
        self.assertTrue(my_check.did_run)
