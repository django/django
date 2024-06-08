import warnings

from django.core.exceptions import ImproperlyConfigured
from django.utils.deprecation import RemovedInDjango60Warning

try:
    import oracledb

    is_oracledb = True
except ImportError as e:
    try:
        import cx_Oracle as oracledb  # NOQA

        warnings.warn(
            "cx_Oracle is deprecated. Use oracledb instead.",
            RemovedInDjango60Warning,
            stacklevel=2,
        )
        is_oracledb = False
    except ImportError:
        raise ImproperlyConfigured(f"Error loading oracledb module: {e}")
