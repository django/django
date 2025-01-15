from django.conf import settings

from . import Tags, Warning, register

REMOVED_SETTINGS = {
    # Django 1.0
    # https://docs.djangoproject.com/en/stable/releases/1.0/
    # Django 1.1
    # https://docs.djangoproject.com/en/stable/releases/1.1/#features-deprecated-in-1-1
    # Django 1.2
    # https://docs.djangoproject.com/en/stable/releases/1.2/#features-deprecated-in-1-2
    "DATABASE_ENGINE",
    "DATABASE_HOST",
    "DATABASE_NAME",
    "DATABASE_OPTIONS",
    "DATABASE_PASSWORD",
    "DATABASE_PORT",
    "DATABASE_USER",
    "TEST_DATABASE_CHARSET",
    "TEST_DATABASE_COLLATION",
    "TEST_DATABASE_NAME",
    # Django 1.3
    # https://docs.djangoproject.com/en/stable/releases/1.3/#features-deprecated-in-1-3
    # Django 1.4
    # https://docs.djangoproject.com/en/stable/releases/1.4/#features-deprecated-in-1-4
    "TRANSACTIONS_MANAGED",
    # Django 1.5
    # https://docs.djangoproject.com/en/stable/releases/1.5/#features-deprecated-in-1-5
    "AUTH_PROFILE_MODULE",
    # Django 1.7
    # https://docs.djangoproject.com/en/stable/releases/1.7/#features-removed-in-1-7
    "SOUTH_DATABASE_ADAPTER",
    "SOUTH_DATABASE_ADAPTERS",
    "SOUTH_AUTO_FREEZE_APP",
    "SOUTH_TESTS_MIGRATE",
    "SOUTH_LOGGING_ON",
    "SOUTH_LOGGING_FILE",
    "SOUTH_MIGRATION_MODULES",
    "SOUTH_USE_PYC",
    "TEST_CREATE",
    "TEST_USER_CREATE",
    "TEST_PASSWD",
    "TEST_DATABASE_ENGINE",
    "TEST_DATABASE_HOST",
    "TEST_DATABASE_NAME",
    "TEST_DATABASE_OPTIONS",
    "TEST_DATABASE_PASSWORD",
    "TEST_DATABASE_PORT",
    "TEST_DATABASE_USER",
    # Django 1.8
    # https://docs.djangoproject.com/en/stable/releases/1.8/#features-removed-in-1-8
    "SEND_BROKEN_LINK_EMAILS",
    "CACHE_MIDDLEWARE_ANONYMOUS_ONLY",
    # Django 1.9
    # https://docs.djangoproject.com/en/stable/releases/1.9/#features-removed-in-1-9
    # Django 1.10
    # https://docs.djangoproject.com/en/stable/releases/1.10/#features-removed-in-1-10
    "ALLOWED_INCLUDE_ROOTS",
    "LOGOUT_URL",
    "TEMPLATE_CONTEXT_PROCESSORS",
    "TEMPLATE_DEBUG",
    "TEMPLATE_DIRS",
    "TEMPLATE_LOADERS",
    "TEMPLATE_STRING_IF_INVALID",
    # Django 2.0
    # https://docs.djangoproject.com/en/stable/releases/2.0/#features-removed-in-2-0
    "MIDDLEWARE_CLASSES",
    # Django 2.1
    # https://docs.djangoproject.com/en/stable/releases/2.1/#features-removed-in-2-1
    "USE_ETAGS",
    "SECURE_BROWSER_XSS_FILTER",
    # Django 3.0
    # https://docs.djangoproject.com/en/stable/releases/3.0/#features-removed-in-3-0
    "DEFAULT_CONTENT_TYPE",
    "PASSWORD_RESET_TIMEOUT_DAYS",
    # Django 3.1
    # https://docs.djangoproject.com/en/stable/releases/3.1/#features-removed-in-3-1
    "DEFAULT_FILE_STORAGE",
    "FILE_CHARSET",
    # Django 4.0
    # https://docs.djangoproject.com/en/stable/releases/4.0/#features-removed-in-4-0
    "DEFAULT_HASHING_ALGORITHM",
    "PASSWORD_RESET_TIMEOUT_DAYS",
    "SECURE_BROWSER_XSS_FILTER",
    # Django 4.1
    # https://docs.djangoproject.com/en/stable/releases/4.1/#features-removed-in-4-1
    # Django 5.0
    # https://docs.djangoproject.com/en/stable/releases/5.0/#features-removed-in-5-0
    "USE_L10N",
    "USE_DEPRECATED_PYTZ",
    "CSRF_COOKIE_MASKED",
    "DATABASE_OPTIONS",
    # Django 5.1
    # https://docs.djangoproject.com/en/stable/releases/5.1/#features-removed-in-5-1
    "DEFAULT_FILE_STORAGE",
    "STATICFILES_STORAGE",
    # Django 6.0
    # RemovedInDjango60Warning: when the deprecation ends, replace with:
    # "FORMS_URLFIELD_ASSUME_HTTPS",
}


@register(Tags.settings)
def check_removed_settings(**kwargs):
    """
    This check warns users who still use deprecated settings variables.
    """

    warnings = []
    for setting_name in dir(settings):
        if setting_name.isupper() and setting_name in REMOVED_SETTINGS:
            warnings.append(
                Warning(
                    f"The {setting_name!r} setting was removed and its use is "
                    f"not recommended.",
                    hint="Please refer to the documentation and remove/replace "
                    "this setting.",
                    obj=setting_name,
                    id="settings.W001",
                )
            )

    return warnings
