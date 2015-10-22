import unittest
from functools import wraps

from django.conf import settings
from django.db import DEFAULT_DB_ALIAS, connection


def skipUnlessGISLookup(*gis_lookups):
    """
    Skip a test unless a database supports all of gis_lookups.
    """
    def decorator(test_func):
        @wraps(test_func)
        def skip_wrapper(*args, **kwargs):
            if any(key not in connection.ops.gis_operators for key in gis_lookups):
                raise unittest.SkipTest(
                    "Database doesn't support all the lookups: %s" % ", ".join(gis_lookups)
                )
            return test_func(*args, **kwargs)
        return skip_wrapper
    return decorator


def no_backend(test_func, backend):
    "Use this decorator to disable test on specified backend."
    if settings.DATABASES[DEFAULT_DB_ALIAS]['ENGINE'].rsplit('.')[-1] == backend:
        @unittest.skip("This test is skipped on '%s' backend" % backend)
        def inner():
            pass
        return inner
    else:
        return test_func


# Decorators to disable entire test functions for specific
# spatial backends.
def no_oracle(func):
    return no_backend(func, 'oracle')


# Shortcut booleans to omit only portions of tests.
_default_db = settings.DATABASES[DEFAULT_DB_ALIAS]['ENGINE'].rsplit('.')[-1]
oracle = _default_db == 'oracle'
postgis = _default_db == 'postgis'
mysql = _default_db == 'mysql'
spatialite = _default_db == 'spatialite'

# MySQL spatial indices can't handle NULL geometries.
gisfield_may_be_null = not mysql

if oracle and 'gis' in settings.DATABASES[DEFAULT_DB_ALIAS]['ENGINE']:
    from django.contrib.gis.db.backends.oracle.models import OracleSpatialRefSys as SpatialRefSys
elif postgis:
    from django.contrib.gis.db.backends.postgis.models import PostGISSpatialRefSys as SpatialRefSys
elif spatialite:
    from django.contrib.gis.db.backends.spatialite.models import SpatialiteSpatialRefSys as SpatialRefSys
else:
    SpatialRefSys = None
