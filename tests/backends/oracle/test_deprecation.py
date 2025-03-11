import warnings

from django.db import connection
from django.test import TestCase


class OracleDeprecationTests(TestCase):
    databases = {"default"}

    def test_use_returning_into_deprecation(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            warnings.warn(
                "The 'use_returning_into' option is deprecated",
                DeprecationWarning,
            )

            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")

            self.assertTrue(
                any(issubclass(warn.category, DeprecationWarning) for warn in w),
                "Expected a DeprecationWarning but none was raised.",
            )

            self.assertTrue(
                any(
                    "The 'use_returning_into' option is deprecated" in str(warn.message)
                    for warn in w
                ),
                "Deprecation warning message is incorrect.",
            )
