
def create_test_spatial_db(verbosity=1, autoclobber=False):
    "A wrapper over the MySQL `create_test_db` method."
    from django.db import connection
    connection.creation.create_test_db(verbosity, autoclobber)
