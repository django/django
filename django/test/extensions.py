from django.conf import settings
from django.core import mail


class TestExtension(object):
    def setup_environment(self):
        pass

    def teardown_environment(self):
        pass

    def setup_test(self):
        pass

    def teardown_test(self):
        pass


class MailOutbox(TestExtension):
    def setup_environment(self):
        self._original_email_backend = settings.EMAIL_BACKEND
        settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
        mail.outbox = []

    def teardown_environment(self):
        settings.EMAIL_BACKEND = self._original_email_backend
        del self._original_email_backend
        del mail.outbox

    def setup_test(self):
        mail.outbox = []
