from unittest import skip

from django.conf import settings
from django.db import DEFAULT_DB_ALIAS


def no_backend(test_func, backend):
    "Use this decorator to disable test on specified backend."
    if settings.DATABASES[DEFAULT_DB_ALIAS]['ENGINE'].rsplit('.')[-1] == backend:
        @skip("This test is skipped on '%s' backend" % backend)
        def inner():
            pass
        return inner
    else:
        return test_func


# Decorators to disable entire test functions for specific
# spatial backends.
def no_oracle(func):
    return no_backend(func, 'oracle')


def no_postgis(func):
    return no_backend(func, 'postgis')


def no_mysql(func):
    return no_backend(func, 'mysql')


def no_spatialite(func):
    return no_backend(func, 'spatialite')

# Shortcut booleans to omit only portions of tests.
_default_db = settings.DATABASES[DEFAULT_DB_ALIAS]['ENGINE'].rsplit('.')[-1]
oracle = _default_db == 'oracle'
postgis = _default_db == 'postgis'
mysql = _default_db == 'mysql'
spatialite = _default_db == 'spatialite'

HAS_SPATIALREFSYS = True
if oracle and 'gis' in settings.DATABASES[DEFAULT_DB_ALIAS]['ENGINE']:
    from django.contrib.gis.db.backends.oracle.models import OracleSpatialRefSys as SpatialRefSys
elif postgis:
    from django.contrib.gis.db.backends.postgis.models import PostGISSpatialRefSys as SpatialRefSys
elif spatialite:
    from django.contrib.gis.db.backends.spatialite.models import SpatialiteSpatialRefSys as SpatialRefSys
else:
    HAS_SPATIALREFSYS = False
    SpatialRefSys = None


def has_spatial_db():
    # All databases must have spatial backends to run GeoDjango tests.
    spatial_dbs = [name for name, db_dict in settings.DATABASES.items()
        if db_dict['ENGINE'].startswith('django.contrib.gis')]
    return len(spatial_dbs) == len(settings.DATABASES)

HAS_SPATIAL_DB = has_spatial_db()
