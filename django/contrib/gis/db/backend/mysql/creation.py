
def create_spatial_db(test=True, verbosity=1, autoclobber=False):
    if not test: raise NotImplementedError('This uses `create_test_db` from test/utils.py')
    from django.db import connection
    connection.creation.create_test_db(verbosity, autoclobber)
