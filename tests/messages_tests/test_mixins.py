from django.core.signing import b64decode_decompress
from django.test import SimpleTestCase, override_settings
from django.urls import reverse

from .urls import ContactFormViewWithMsg


@override_settings(ROOT_URLCONF='messages_tests.urls')
class SuccessMessageMixinTests(SimpleTestCase):

    def test_set_messages_success(self):
        author = {'name': 'John Doe', 'slug': 'success-msg'}
        add_url = reverse('add_success_msg')
        req = self.client.post(add_url, author)
        print(type(req.cookies['messages'].value))
        print(req.cookies['messages'].value)
        self.assertIn(
            bytes(ContactFormViewWithMsg.success_message % author, 'utf-8'),
            b64decode_decompress(req.cookies['messages'].value))
