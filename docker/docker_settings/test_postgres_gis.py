from .test_sqlite import *  # NOQA

DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'USER': 'django',
        'PASSWORD': 'django',
        'NAME': 'django',
        'HOST': 'postgres-gis-db'
    },
    'other': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'USER': 'django',
        'NAME': 'django2',
        'PASSWORD': 'django',
        'HOST': 'postgres-gis-db'
    }
}
