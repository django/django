# This is an example test settings file for use with the Django test suite.
#
# The 'sqlite3' backend requires only the ENGINE setting (an in-
# memory database will be used). All other backends will require a
# NAME and potentially authentication information. See the
# following section in the docs for more information:
#
# https://docs.djangoproject.com/en/dev/internals/contributing/writing-code/unit-tests/
#
# The different databases that Django supports behave differently in certain
# situations, so it is recommended to run the test suite against as many
# database backends as possible.  You may want to create a separate settings
# file for each of the backends you test against.
import dj_database_url

DATABASES = {
    'default': dj_database_url.config(
        env="DEFAULT_DB_URL", default="sqlite:///"),
    'other': dj_database_url.config(
        env="OTHER_DB_URL", default="sqlite:///")
}

# Optionally, use memcache during testing - if URL is defined
from os import environ
if 'MEMCACHE' in environ:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
            'LOCATION': environ['MEMCACHE'],
        }
    }


SECRET_KEY = "django_tests_secret_key"
# To speed up tests under SQLite we use the MD5 hasher as the default one.
# This should not be needed under other databases, as the relative speedup
# is only marginal there.
PASSWORD_HASHERS = (
    'django.contrib.auth.hashers.MD5PasswordHasher',
)
