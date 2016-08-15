DATABASES = {

'default': {

'ENGINE': 'django.db.backends.postgresql_psycopg2',

'NAME': 'postgres',

'USER': 'postgres',

'PASSWORD': 'postgres',

'HOST': 'localhost',

'PORT': '',

},

'other': {

'ENGINE': 'django.db.backends.postgresql_psycopg2',

'NAME': 'test',

'USER': 'postgres',

'PASSWORD': 'postgres',

'HOST': 'localhost',

'PORT': '',

}

}

SECRET_KEY = "django_tests_secret_key"

# Use a fast hasher to speed up tests.
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]
