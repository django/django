from .test_sqlite import *  # NOQA

DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.spatialite',
    },
    'other': {
        'ENGINE': 'django.contrib.gis.db.backends.spatialite',
    }
}
