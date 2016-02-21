from django.test import SimpleTestCase, ignore_warnings, override_settings
from django.urls import reverse
from django.utils.deprecation import RemovedInDjango20Warning

from .urls import ContactFormViewWithLegacyMsg, ContactFormViewWithMsg


@override_settings(ROOT_URLCONF='messages_tests.urls')
class SuccessMessageMixinTests(SimpleTestCase):

    def test_set_messages_success(self):
        author = {'name': 'John Doe',
                  'slug': 'success-msg'}
        add_url = reverse('add_success_msg')
        req = self.client.post(add_url, author)
        self.assertIn(
            ContactFormViewWithMsg.success_message.format(**author),
            req.cookies['messages'].value,
        )

    @ignore_warnings(category=RemovedInDjango20Warning)
    def test_set_messages_success_percent_placeholder(self):
        author = {
            'name': 'John Doe',
            'slug': 'success-msg',
        }
        add_url = reverse('add_success_legacy_msg')
        req = self.client.post(add_url, author)
        self.assertIn(
            ContactFormViewWithLegacyMsg.success_message % author,
            req.cookies['messages'].value,
        )
