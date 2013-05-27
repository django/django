DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3'
    },
    'other': {
        'ENGINE': 'django.db.backends.sqlite3',
    }
}

SECRET_KEY = "django_tests_secret_key"

PASSWORD_HASHERS = ('django.contrib.auth.hashers.MD5PasswordHasher',)
