from __future__ import unicode_literals


def check_test_runner():
    """
    Checks if the user has *not* overridden the ``TEST_RUNNER`` setting &
    warns them about the default behavior changes.

    If the user has overridden that setting, we presume they know what they're
    doing & avoid generating a message.
    """
    from django.conf import settings
    new_default = 'django.test.runner.DiscoverRunner'
    test_runner_setting = getattr(settings, 'TEST_RUNNER', new_default)

    if test_runner_setting == new_default:
        message = [
            "You have not explicitly set 'TEST_RUNNER'. In Django 1.6,",
            "there is a new test runner ('%s')" % new_default,
            "by default. You should ensure your tests are still all",
            "running & behaving as expected. See",
            "https://docs.djangoproject.com/en/dev/releases/1.6/#discovery-of-tests-in-any-test-module",
            "for more information.",
        ]
        return ' '.join(message)


def run_checks():
    """
    Required by the ``check`` management command, this returns a list of
    messages from all the relevant check functions for this version of Django.
    """
    checks = [
        check_test_runner()
    ]
    # Filter out the ``None`` or empty strings.
    return [output for output in checks if output]
