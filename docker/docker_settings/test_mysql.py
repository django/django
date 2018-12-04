from .test_sqlite import *  # NOQA

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'USER': 'root',
        'PASSWORD': '',
        'NAME': 'django',
        'HOST': 'mysql-db',
        'TEST': {
            'CHARSET': 'utf8',
        },
    },
    'other': {
        'ENGINE': 'django.db.backends.mysql',
        'USER': 'root',
        'PASSWORD': '',
        'NAME': 'django2',
        'HOST': 'mysql-db',
        'TEST': {
            'CHARSET': 'utf8',
        },
    },
}
