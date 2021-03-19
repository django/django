from django.core.signing import b64_decode
from django.test import SimpleTestCase, override_settings
from django.urls import reverse

from .urls import ContactFormViewWithMsg


@override_settings(ROOT_URLCONF='messages_tests.urls')
class SuccessMessageMixinTests(SimpleTestCase):

    def test_set_messages_success(self):
        author = {'name': 'John Doe', 'slug': 'success-msg'}
        add_url = reverse('add_success_msg')
        req = self.client.post(add_url, author)
        # Uncompressed message is stored in the cookie.
        value = b64_decode(
            req.cookies['messages'].value.split(":")[0].encode(),
        ).decode()
        self.assertIn(ContactFormViewWithMsg.success_message % author, value)
