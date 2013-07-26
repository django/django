# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.core.checks import Error
from django.core.checks.registration import CheckingFramework
from django.test import TestCase
from django.utils.encoding import force_str

from .models import SimpleModel


class CheckingFrameworkTests(TestCase):

    def test_register_and_run_checks(self):
        calls = [0]

        def f(**kwargs):
            calls[0] += 1
            return [1, 2, 3]
        framework = CheckingFramework()
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
        expected = "obj: Message HINT: Hint"
        self.assertEqual(force_str(e), expected)

    def test_printing_no_hint(self):
        e = Error("Message", hint=None, obj=DummyObj())
        expected = "obj: Message"
        self.assertEqual(force_str(e), expected)

    def test_printing_no_object(self):
        e = Error("Message", hint="Hint", obj=None)
        expected = "?: Message HINT: Hint"
        self.assertEqual(force_str(e), expected)

    def test_printing_field_error(self):
        field = SimpleModel._meta.get_field('field')
        e = Error("Error", hint=None, obj=field)
        expected = "checking_framework.SimpleModel.field: Error"
        self.assertEqual(force_str(e), expected)

    def test_printing_model_error(self):
        e = Error("Error", hint=None, obj=SimpleModel)
        expected = "checking_framework.SimpleModel: Error"
        self.assertEqual(force_str(e), expected)

    def test_printing_manager_error(self):
        manager = SimpleModel.manager
        e = Error("Error", hint=None, obj=manager)
        expected = "checking_framework.SimpleModel.manager: Error"
        self.assertEqual(force_str(e), expected)
