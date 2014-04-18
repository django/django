from __future__ import unicode_literals

from django.db import models

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
            "Django 1.6 introduced a new default test runner ('%s')" % new_default,
            "You should ensure your tests are all running & behaving as expected. See",
            "https://docs.djangoproject.com/en/dev/releases/1.6/#new-test-runner",
            "for more information.",
        ]
        return ' '.join(message)

def check_boolean_field_default_value():
    """
    Checks if there are any BooleanFields without a default value, &
    warns the user that the default has changed from False to Null.
    """
    fields = []
    for cls in models.get_models():
        opts = cls._meta
        for f in opts.local_fields:
            if isinstance(f, models.BooleanField) and not f.has_default():
                fields.append(
                    '%s.%s: "%s"' % (opts.app_label, opts.object_name, f.name)
                )
    if fields:
        fieldnames = ", ".join(fields)
        message = [
            "You have not set a default value for one or more BooleanFields:",
            "%s." % fieldnames,
            "In Django 1.6 the default value of BooleanField was changed from",
            "False to Null when Field.default isn't defined. See",
            "https://docs.djangoproject.com/en/1.6/ref/models/fields/#booleanfield"
            "for more information."
        ]
        return ' '.join(message)


def run_checks():
    """
    Required by the ``check`` management command, this returns a list of
    messages from all the relevant check functions for this version of Django.
    """
    checks = [
        check_test_runner(),
        check_boolean_field_default_value(),
    ]
    # Filter out the ``None`` or empty strings.
    return [output for output in checks if output]
