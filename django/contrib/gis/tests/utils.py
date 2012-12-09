from django.conf import settings
from django.db import DEFAULT_DB_ALIAS

# function that will pass a test.
def pass_test(*args): return

def no_backend(test_func, backend):
    "Use this decorator to disable test on specified backend."
    if settings.DATABASES[DEFAULT_DB_ALIAS]['ENGINE'].rsplit('.')[-1] == backend:
        return pass_test
    else:
        return test_func

# Decorators to disable entire test functions for specific
# spatial backends.
def no_oracle(func): return no_backend(func, 'oracle')
def no_postgis(func): return no_backend(func, 'postgis')
def no_mysql(func): return no_backend(func, 'mysql')
def no_spatialite(func): return no_backend(func, 'spatialite')

# Shortcut booleans to omit only portions of tests.
_default_db = settings.DATABASES[DEFAULT_DB_ALIAS]['ENGINE'].rsplit('.')[-1]
oracle  = _default_db == 'oracle'
postgis = _default_db == 'postgis'
mysql   = _default_db == 'mysql'
spatialite = _default_db == 'spatialite'

HAS_SPATIALREFSYS = True
if oracle and 'gis' in settings.DATABASES[DEFAULT_DB_ALIAS]['ENGINE']:
    from django.contrib.gis.db.backends.oracle.models import SpatialRefSys
elif postgis:
    from django.contrib.gis.db.backends.postgis.models import SpatialRefSys
elif spatialite:
    from django.contrib.gis.db.backends.spatialite.models import SpatialRefSys
else:
    HAS_SPATIALREFSYS = False
    SpatialRefSys = None
