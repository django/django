from django.test.utils import create_test_db

def create_spatial_db(test=True, verbosity=1, autoclobber=False):
    if not test: raise NotImplementedError('This uses `create_test_db` from test/utils.py')
    create_test_db(verbosity, autoclobber)
