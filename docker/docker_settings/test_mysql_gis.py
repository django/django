from .test_sqlite import *  # NOQA

DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.mysql',
        'USER': 'root',
        'PASSWORD': '',
        'NAME': 'django',
        'HOST': 'mysql-gis-db',
        'TEST': {
            'CHARSET': 'utf8',
        },
    },
    'other': {
        'ENGINE': 'django.contrib.gis.db.backends.mysql',
        'USER': 'root',
        'PASSWORD': '',
        'NAME': 'django2',
        'HOST': 'mysql-gis-db',
        'TEST': {
            'CHARSET': 'utf8',
        },
    },
}
