DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': 'django',
        'HOST': 'localhost',
        'USER': 'postgres',
    },
    'other': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': 'django2',
        'HOST': 'localhost',
        'USER': 'postgres',
    }
}

SECRET_KEY = "django_tests_secret_key"

PASSWORD_HASHERS = (
    'django.contrib.auth.hashers.MD5PasswordHasher',
)
