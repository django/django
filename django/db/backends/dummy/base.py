"""
Dummy database backend for Django.

Django uses this if the DATABASE_ENGINE setting is empty (None or empty string).

Each of these API functions, except connection.close(), raises
ImproperlyConfigured.
"""

from django.core.exceptions import ImproperlyConfigured

def complain(*args, **kwargs):
    raise ImproperlyConfigured, "You haven't set the DATABASE_ENGINE setting yet."

class DatabaseError(Exception):
    pass

class DatabaseWrapper:
    cursor = complain
    _commit = complain
    _rollback = complain

    def __init__(self, **kwargs):
        pass

    def close(self):
        pass # close()

supports_constraints = False
uses_case_insensitive_names = False
quote_name = complain
dictfetchone = complain
dictfetchmany = complain
dictfetchall = complain
get_last_insert_id = complain
get_date_extract_sql = complain
get_date_trunc_sql = complain
get_limit_offset_sql = complain
get_random_function_sql = complain
get_deferrable_sql = complain
get_fulltext_search_sql = complain
get_drop_foreignkey_sql = complain
get_sql_flush = complain

OPERATOR_MAPPING = {}
