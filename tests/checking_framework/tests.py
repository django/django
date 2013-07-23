# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.core.checks.base import CheckingFramework
from django.test import TestCase


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
