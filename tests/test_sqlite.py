# This is an example test settings file for use with the Freedom test suite.
#
# The 'sqlite3' backend requires only the ENGINE setting (an in-
# memory database will be used). All other backends will require a
# NAME and potentially authentication information. See the
# following section in the docs for more information:
#
# https://docs.freedomproject.com/en/dev/internals/contributing/writing-code/unit-tests/
#
# The different databases that Freedom supports behave differently in certain
# situations, so it is recommended to run the test suite against as many
# database backends as possible.  You may want to create a separate settings
# file for each of the backends you test against.

DATABASES = {
    'default': {
        'ENGINE': 'freedom.db.backends.sqlite3'
    },
    'other': {
        'ENGINE': 'freedom.db.backends.sqlite3',
    }
}

SECRET_KEY = "freedom_tests_secret_key"

# Use a fast hasher to speed up tests.
PASSWORD_HASHERS = (
    'freedom.contrib.auth.hashers.MD5PasswordHasher',
)
