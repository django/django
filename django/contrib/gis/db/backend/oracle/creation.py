
def create_test_spatial_db(verbosity=1, autoclobber=False):
    "A wrapper over the Oracle `create_test_db` routine."
    from django.db import connection
    connection.creation.create_test_db(verbosity, autoclobber)
