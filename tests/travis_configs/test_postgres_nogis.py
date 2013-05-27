DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'django',
        'HOST': 'localhost',
        'USER': 'postgres',
    },
    'other': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'django2',
        'HOST': 'localhost',
        'USER': 'postgres',
    }
}

SECRET_KEY = "django_tests_secret_key"

PASSWORD_HASHERS = (
    'django.contrib.auth.hashers.MD5PasswordHasher',
)
