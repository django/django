from __future__ import unicode_literals


def check_test_runner():
    from django.conf import settings
    new_default = u'django.test.runner.DiscoverRunner'
    test_runner_setting = getattr(settings, u'TEST_RUNNER', new_default)

    if test_runner_setting == new_default:
        message = [
            u"You have not explicitly set 'TEST_RUNNER'. In Django 1.6,",
            u"There is a new test runner ('%s')" % new_default,
            u"by default. You should ensure your tests are still all",
            u"running & behaving as expected. See",
            u"https://docs.djangoproject.com/en/dev/releases/1.6/#discovery-of-tests-in-any-test-module",
            u"for more information.",
        ]
        return u' '.join(message)


def run_checks():
    return [
        check_test_runner()
    ]
