from django.conf import settings

# function that will pass a test.
def pass_test(*args): return

def no_backend(test_func, backend):
    "Use this decorator to disable test on specified backend."
    if settings.DATABASE_ENGINE == backend:
        return pass_test
    else:
        return test_func

# Decorators to disable entire test functions for specific
# spatial backends.
def no_oracle(func): return no_backend(func, 'oracle')
def no_postgis(func): return no_backend(func, 'postgresql_psycopg2')
def no_mysql(func): return no_backend(func, 'mysql')
def no_spatialite(func): return no_backend(func, 'sqlite3')

# Shortcut booleans to omit only portions of tests.
oracle  = settings.DATABASE_ENGINE == 'oracle'
postgis = settings.DATABASE_ENGINE == 'postgresql_psycopg2' 
mysql   = settings.DATABASE_ENGINE == 'mysql'
spatialite = settings.DATABASE_ENGINE == 'sqlite3'
