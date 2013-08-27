# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from functools import wraps

from django.utils.itercompat import is_iterable


class CheckFramework(object):

    def __init__(self):
        self.registered_checks = []

    def register(self, f):
        """
        Register given function. It will be called during `run_checks`. The
        function should receive **kwargs and return list of Errors and
        Warnings.
        """
        self.registered_checks.append(f)

    def run_checks(self, apps):
        """ Run all registered checks and return list of Errors and Warnings.
        """
        errors = []
        for f in self.registered_checks:
            new_errors = f(apps=apps)
            assert is_iterable(new_errors), (
                "The function %r did not return a list. All functions registered "
                "in checking framework must return a list." % f)
            errors.extend(new_errors)
        return errors


framework = CheckFramework()
register = framework.register
run_checks = framework.run_checks


def tag(tag):
    def outer(f):
        if not hasattr(f, 'tags'):
            f.tags = []
        f.tags.append(tag)
        return f
    return outer
