from django.db.backends.oracle.creation import create_test_db

def create_spatial_db(test=True, verbosity=1, autoclobber=False):
    "A wrapper over the Oracle `create_test_db` routine."
    if not test: raise NotImplementedError('This uses `create_test_db` from db/backends/oracle/creation.py')
    from django.conf import settings
    from django.db import connection
    create_test_db(settings, connection, verbosity, autoclobber)
