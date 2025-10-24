import copy
import unittest
from functools import wraps
from unittest import mock

from django.conf import settings
from django.contrib.gis.geos.libgeos import geos_version_tuple
from django.db import DEFAULT_DB_ALIAS, connection
from django.db.models import Func


def skipUnlessGISLookup(*gis_lookups):
    """
    Skip a test unless a database supports all of gis_lookups.
    """

    def decorator(test_func):
        @wraps(test_func)
        def skip_wrapper(*args, **kwargs):
            if any(key not in connection.ops.gis_operators for key in gis_lookups):
                raise unittest.SkipTest(
                    "Database doesn't support all the lookups: %s"
                    % ", ".join(gis_lookups)
                )
            return test_func(*args, **kwargs)

        return skip_wrapper

    return decorator


_default_db = settings.DATABASES[DEFAULT_DB_ALIAS]["ENGINE"].rsplit(".")[-1]
# MySQL spatial indices can't handle NULL geometries.
gisfield_may_be_null = _default_db != "mysql"
# GEOSWKTWriter_write() behavior was changed in GEOS 3.12+ to include
# parentheses for sub-members. MariaDB doesn't accept WKT representations with
# additional parentheses for MultiPoint. This is an accepted bug (MDEV-36166)
# in MariaDB that should be fixed in the future.
cannot_save_multipoint = connection.ops.mariadb and geos_version_tuple() >= (3, 12)
can_save_multipoint = not cannot_save_multipoint


class FuncTestMixin:
    """Assert that Func expressions aren't mutated during their as_sql()."""

    def setUp(self):
        def as_sql_wrapper(original_as_sql):
            def inner(*args, **kwargs):
                func = original_as_sql.__self__
                # Resolve output_field before as_sql() so touching it in
                # as_sql() won't change __dict__.
                func.output_field
                __dict__original = copy.deepcopy(func.__dict__)
                result = original_as_sql(*args, **kwargs)
                msg = (
                    "%s Func was mutated during compilation." % func.__class__.__name__
                )
                self.assertEqual(func.__dict__, __dict__original, msg)
                return result

            return inner

        def __getattribute__(self, name):
            if name != vendor_impl:
                return __getattribute__original(self, name)
            try:
                as_sql = __getattribute__original(self, vendor_impl)
            except AttributeError:
                as_sql = __getattribute__original(self, "as_sql")
            return as_sql_wrapper(as_sql)

        vendor_impl = "as_" + connection.vendor
        __getattribute__original = Func.__getattribute__
        func_patcher = mock.patch.object(Func, "__getattribute__", __getattribute__)
        func_patcher.start()
        self.addCleanup(func_patcher.stop)
        super().setUp()
