DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
    },
    'other': {
        'ENGINE': 'django.db.backends.sqlite3',
    }
}

SECRET_KEY = "django_tests_secret_key"

# Use a fast hasher to speed up tests.
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]


CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    },
    'memcached': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': 'memcached:11211',
        'KEY_PREFIX': '1:'
    },
    'memcached_2': {
        'BACKEND': 'django.core.cache.backends.memcached.PyLibMCCache',
        'LOCATION': 'memcached2:11211',
        'KEY_PREFIX': '2:'
    }
}

GEOIP_PATH = '/geolite2/'
