from django.test import TestCase, override_settings, Client
from django.utils.translation import override


class CsrfViewTests(TestCase):
    urls = "view_tests.urls"

    @override_settings(
        USE_I18N=True,
        MIDDLEWARE_CLASSES=(
            'django.middleware.locale.LocaleMiddleware',
            'django.middleware.common.CommonMiddleware',
            'django.middleware.csrf.CsrfViewMiddleware',
        ),
    )
    def test_translation(self):
        """
        Test that an invalid request is rejected with a localized error message.
        """
        self.client = Client(enforce_csrf_checks=True)

        response = self.client.post('/', HTTP_HOST='www.example.com')
        self.assertContains(response, "Forbidden", status_code=403)
        self.assertContains(response,
                            "CSRF verification failed. Request aborted.",
                            status_code=403)

        with self.settings(LANGUAGE_CODE='nl'), override('en-us'):
            response = self.client.post('/', HTTP_HOST='www.example.com')
            self.assertContains(response, "Verboden", status_code=403)
            self.assertContains(response,
                                "CSRF-verificatie mislukt. Verzoek afgebroken.",
                                status_code=403)
