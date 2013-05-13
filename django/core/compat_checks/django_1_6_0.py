import warnings


def check_test_runner():
    from django.conf import settings
    new_default = u'django.test.runner.DiscoverRunner'
    test_runner_setting = getattr(settings, u'TEST_RUNNER', new_default)

    if test_runner_setting != new_default:
        warnings.warn(
            u"There is a new test runner available in Django 1.6, but you " +
            u"are specifying a different setting for 'TEST_RUNNER'."
        )


def run_checks():
    check_test_runner()
