import warnings


def check_test_runner():
    from django.conf import settings
    new_default = u'django.test.runner.DiscoverRunner'
    test_runner_setting = getattr(settings, u'TEST_RUNNER', new_default)

    if test_runner_setting == new_default:
        warnings.warn(
            u"You have not explicitly set 'TEST_RUNNER'. In Django 1.6, " +
            u"There is a new test runner ('%s') by default. You should " +
            u"ensure your tests are still all running & behaving as expected."
        )


def run_checks():
    check_test_runner()
