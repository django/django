# -*- coding: utf-8 -*-
from __future__ import unicode_literals

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

    def run_checks(self, apps=None, tags=None):
        """ Run all registered checks and return list of Errors and Warnings.
        """
        errors = []
        if tags is not None:
            checks = [check for check in self.registered_checks
                      if hasattr(check, 'tag') and check.tag in tags]
        else:
            checks = self.registered_checks

        for f in checks:
            if tags is None or (hasattr(f, 'tag') and f.tag in tags):
                new_errors = f(apps=apps)
                assert is_iterable(new_errors), (
                    "The function %r did not return a list. All functions registered "
                    "in checking framework must return a list." % f)
                errors.extend(new_errors)
        return errors

    def tag_exists(self, tag):
        tags = [check.tag for check in self.registered_checks if hasattr(check, 'tag')]
        return tag in tags


framework = CheckFramework()
register = framework.register
run_checks = framework.run_checks
tag_exists = framework.tag_exists


def tag(tag):
    def outer(f):
        if not hasattr(f, 'tags'):
            f.tag = tag
        else:
            raise Exception('You cannot assign more than one tag to a check function.')
        return f
    return outer
