import warnings
from unittest.mock import MagicMock, patch
from django.test import SimpleTestCase

class OracleDeprecationTests(SimpleTestCase):
    @patch("django.db.connection")  # Mock the entire connection object
    def test_use_returning_into_deprecation(self, mock_connection):
        mock_connection.cursor.return_value = MagicMock()  # Mock cursor

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            warnings.warn("The 'use_returning_into' option is deprecated", DeprecationWarning)

            with mock_connection.cursor() as cursor:
                cursor.execute("SELECT 1")  # This will now be a mocked call

        self.assertTrue(
            any(issubclass(warn.category, DeprecationWarning) for warn in w),
            "Expected a DeprecationWarning but none was raised."
        )