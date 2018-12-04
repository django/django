from .test_sqlite import *  # NOQA

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'USER': 'django',
        'PASSWORD': 'django',
        'NAME': 'django',
        'HOST': 'postgres-db'
    },
    'other': {
        'ENGINE': 'django.db.backends.postgresql',
        'USER': 'django',
        'NAME': 'django2',
        'PASSWORD': 'django',
        'HOST': 'postgres-db'
    }
}
