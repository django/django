import warnings

from django.utils.deprecation import (
    RemovedInDjango60Warning,
    adjust_stacklevel_for_warning,
)

try:
    import oracledb

    is_oracledb = True
except ImportError as e:
    try:
        import cx_Oracle as oracledb  # NOQA

        warnings.warn(
            "cx_Oracle is deprecated. Use oracledb instead.",
            RemovedInDjango60Warning,
            **adjust_stacklevel_for_warning(__file__),
        )
        is_oracledb = False
    except ImportError:
        raise e from None
