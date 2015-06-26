from django.conf import settings
from django.core import mail


class TestExtension(object):
    def setup_test_environment(self):
        pass

    def teardown_test_environment(self):
        pass

    def pre_setup(self):
        pass

    def post_teardown(self):
        pass


class MailOutbox(TestExtension):
    def setup_test_environment(self):
        self._original_email_backend = settings.EMAIL_BACKEND
        settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
        mail.outbox = []

    def teardown_test_environment(self):
        settings.EMAIL_BACKEND = self._original_email_backend
        del self._original_email_backend
        del mail.outbox

    def pre_setup(self):
        mail.outbox = []
