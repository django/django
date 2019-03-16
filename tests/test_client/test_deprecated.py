from django.test import SimpleTestCase, override_settings
from django.utils.deprecation import RemovedInDjango40Warning


@override_settings(ROOT_URLCONF='test_client.urls')
class ClientDeprecatedTest(SimpleTestCase):
    @override_settings(DEBUG_PROPAGATE_EXCEPTIONS=False)
    def test_exception_warning(self):
        msg = (
            'Raising exceptions during test client requests is deprecated. To '
            'continue raising the exception, set the setting '
            'DEBUG_PROPAGATE_EXCEPTIONS to True. To silence this warning, set '
            'it to None. The exception can continue to be tested by inspecting '
            'response.exc_info or by using '
            'SimpleTestCase.assertRequestRaises().'
        )
        with self.assertWarnsMessage(RemovedInDjango40Warning, msg):
            with self.assertRaises(KeyError):
                self.client.get('/broken_view/')
