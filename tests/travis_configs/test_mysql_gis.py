DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.mysql',
        'NAME': 'django',
        'USER': 'root',
        'OPTIONS': {
               'init_command': 'SET storage_engine=INNODB',
        },
        'TEST_NAME': 'test_django',
        'TEST_CHARSET': 'utf8',
        'TEST_COLLATION': 'utf8_general_ci',
    },
    'other': {
        'ENGINE': 'django.contrib.gis.db.backends.mysql',
        'NAME': 'django2',
        'USER': 'root',
        'OPTIONS': {
               'init_command': 'SET storage_engine=INNODB',
        },
        'TEST_NAME': 'test_django2',
        'TEST_CHARSET': 'utf8',
        'TEST_COLLATION': 'utf8_general_ci',
    }
}

SECRET_KEY = "django_tests_secret_key"

PASSWORD_HASHERS = ('django.contrib.auth.hashers.MD5PasswordHasher',)
