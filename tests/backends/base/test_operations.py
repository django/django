from django.db import NotSupportedError, connection
from django.test import SimpleTestCase, skipIfDBFeature


class DatabaseOperationTests(SimpleTestCase):
    @skipIfDBFeature('supports_over_clause')
    def test_window_frame_raise_not_supported_error(self):
        msg = 'This backend does not support window expressions.'
        with self.assertRaisesMessage(NotSupportedError, msg):
            connection.ops.window_frame_rows_start_end()
