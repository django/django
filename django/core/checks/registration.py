# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from itertools import chain

from django.utils.itercompat import is_iterable


class CheckFramework(object):

    def __init__(self):
        self.registered_checks = []

    def register(self, *tags):
        """
        Decorator. Register given function `f` labeled with given `tags`. The
        function should receive **kwargs and return list of Errors and
        Warnings.

        Example::

            framework = CheckFramework()
            @framework.register('mytag', 'anothertag')
            def my_check(apps, **kwargs):
                # ... perform checks and collect `errors` ...
                return errors

        """

        def inner(f):
            f.tags = tags
            self.registered_checks.append(f)
            return f

        return inner

    def run_checks(self, apps=None, tags=None):
        """ Run all registered checks and return list of Errors and Warnings.
        """
        errors = []
        if tags is not None:
            checks = [check for check in self.registered_checks
                      if hasattr(check, 'tags') and set(check.tags) & set(tags)]
        else:
            checks = self.registered_checks

        for f in checks:
            new_errors = f(apps=apps)
            assert is_iterable(new_errors), (
                "The function %r did not return a list. All functions registered "
                "in checking framework must return a list." % f)
            errors.extend(new_errors)
        return errors

    def tag_exists(self, tag):
        tags = chain(*[check.tags for check in self.registered_checks if hasattr(check, 'tags')])
        return tag in tags


framework = CheckFramework()
register = framework.register
run_checks = framework.run_checks
tag_exists = framework.tag_exists
