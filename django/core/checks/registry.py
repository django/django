# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from itertools import chain

from django.utils.itercompat import is_iterable


class Tags(object):
    """
    Built-in tags for internal checks.
    """
    admin = 'admin'
    compatibility = 'compatibility'
    models = 'models'
    signals = 'signals'


class CheckRegistry(object):

    def __init__(self):
        self.registered_checks = []

    def register(self, *tags):
        """
        Decorator. Register given function `f` labeled with given `tags`. The
        function should receive **kwargs and return list of Errors and
        Warnings.

        Example::

            registry = CheckRegistry()
            @registry.register('mytag', 'anothertag')
            def my_check(apps, **kwargs):
                # ... perform checks and collect `errors` ...
                return errors

        """

        def inner(check):
            check.tags = tags
            if check not in self.registered_checks:
                self.registered_checks.append(check)
            return check

        return inner

    def run_checks(self, app_configs=None, tags=None):
        """ Run all registered checks and return list of Errors and Warnings.
        """
        errors = []
        if tags is not None:
            checks = [check for check in self.registered_checks
                      if hasattr(check, 'tags') and set(check.tags) & set(tags)]
        else:
            checks = self.registered_checks

        for check in checks:
            new_errors = check(app_configs=app_configs)
            assert is_iterable(new_errors), (
                "The function %r did not return a list. All functions registered "
                "with the checks registry must return a list." % check)
            errors.extend(new_errors)
        return errors

    def tag_exists(self, tag):
        return tag in self.tags_available()

    def tags_available(self):
        return set(chain(*[check.tags for check in self.registered_checks if hasattr(check, 'tags')]))


registry = CheckRegistry()
register = registry.register
run_checks = registry.run_checks
tag_exists = registry.tag_exists
