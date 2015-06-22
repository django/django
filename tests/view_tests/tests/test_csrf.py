from django.test import Client, TestCase, override_settings
from django.utils.translation import override


@override_settings(ROOT_URLCONF="view_tests.urls")
class CsrfViewTests(TestCase):

    def setUp(self):
        super(CsrfViewTests, self).setUp()
        self.client = Client(enforce_csrf_checks=True)

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
        response = self.client.post('/')
        self.assertContains(response, "Forbidden", status_code=403)
        self.assertContains(response,
                            "CSRF verification failed. Request aborted.",
                            status_code=403)

        with self.settings(LANGUAGE_CODE='nl'), override('en-us'):
            response = self.client.post('/')
            self.assertContains(response, "Verboden", status_code=403)
            self.assertContains(response,
                                "CSRF-verificatie mislukt. Verzoek afgebroken.",
                                status_code=403)

    @override_settings(
        SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTO', 'https')
    )
    def test_no_referer(self):
        """
        Referer header is strictly checked for POST over HTTPS. Trigger the
        exception by sending an incorrect referer.
        """
        response = self.client.post('/', HTTP_X_FORWARDED_PROTO='https')
        self.assertContains(response,
                            "You are seeing this message because this HTTPS "
                            "site requires a &#39;Referer header&#39; to be "
                            "sent by your Web browser, but none was sent.",
                            status_code=403)

    def test_no_cookies(self):
        """
        The CSRF cookie is checked for POST. Failure to send this cookie should
        provide a nice error message.
        """
        response = self.client.post('/')
        self.assertContains(response,
                            "You are seeing this message because this site "
                            "requires a CSRF cookie when submitting forms. "
                            "This cookie is required for security reasons, to "
                            "ensure that your browser is not being hijacked "
                            "by third parties.",
                            status_code=403)

    # In Django 1.10, this can be changed to TEMPLATES=[] because the code path
    # that reads the TEMPLATE_* settings in that case will have been removed.
    @override_settings(TEMPLATES=[{
        'BACKEND': 'django.template.backends.dummy.TemplateStrings',
    }])
    def test_no_django_template_engine(self):
        """
        The CSRF view doesn't depend on the TEMPLATES configuration (#24388).
        """
        response = self.client.post('/')
        self.assertContains(response, "Forbidden", status_code=403)
