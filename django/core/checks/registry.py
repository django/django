from itertools import chain

from django.utils.itercompat import is_iterable


class Tags:
    """
    Built-in tags for internal checks.
    """
    admin = 'admin'
    caches = 'caches'
    compatibility = 'compatibility'
    database = 'database'
    models = 'models'
    security = 'security'
    signals = 'signals'
    templates = 'templates'
    urls = 'urls'


class CheckRegistry:

    def __init__(self):
        self.registered_checks = []
        self.deployment_checks = []

    def register(self, check=None, *tags, **kwargs):
        """
        Can be used as a function or a decorator. Register given function
        `f` labeled with given `tags`. The function should receive **kwargs
        and return list of Errors and Warnings.

        Example::

            registry = CheckRegistry()
            @registry.register('mytag', 'anothertag')
            def my_check(apps, **kwargs):
                # ... perform checks and collect `errors` ...
                return errors
            # or
            registry.register(my_check, 'mytag', 'anothertag')
        """
        kwargs.setdefault('deploy', False)

        def inner(check):
            check.tags = tags
            if kwargs['deploy']:
                if check not in self.deployment_checks:
                    self.deployment_checks.append(check)
            elif check not in self.registered_checks:
                self.registered_checks.append(check)
            return check

        if callable(check):
            return inner(check)
        else:
            if check:
                tags += (check, )
            return inner

    def run_checks(self, app_configs=None, tags=None, include_deployment_checks=False):
        """
        Run all registered checks and return list of Errors and Warnings.
        """
        errors = []
        checks = self.get_checks(include_deployment_checks)

        if tags is not None:
            checks = [check for check in checks
                      if hasattr(check, 'tags') and set(check.tags) & set(tags)]
        else:
            # By default, 'database'-tagged checks are not run as they do more
            # than mere static code analysis.
            checks = [check for check in checks
                      if not hasattr(check, 'tags') or Tags.database not in check.tags]

        for check in checks:
            new_errors = check(app_configs=app_configs)
            assert is_iterable(new_errors), (
                "The function %r did not return a list. All functions registered "
                "with the checks registry must return a list." % check)
            errors.extend(new_errors)
        return errors

    def tag_exists(self, tag, include_deployment_checks=False):
        return tag in self.tags_available(include_deployment_checks)

    def tags_available(self, deployment_checks=False):
        return set(chain(*[check.tags for check in self.get_checks(deployment_checks) if hasattr(check, 'tags')]))

    def get_checks(self, include_deployment_checks=False):
        checks = list(self.registered_checks)
        if include_deployment_checks:
            checks.extend(self.deployment_checks)
        return checks


registry = CheckRegistry()
register = registry.register
run_checks = registry.run_checks
tag_exists = registry.tag_exists
