from django.test import SimpleTestCase


class HttpResponseTestCase(SimpleTestCase):
    def _assert_response(self, actual_response, expected_response_class):
        self.assertEqual(
            actual_response.status_code, expected_response_class.status_code
        )
