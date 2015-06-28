from django.contrib import messages
from django.core.urlresolvers import reverse
from django.test import TestCase, override_settings

from .urls import ContactFormViewWithMsg


@override_settings(ROOT_URLCONF='messages_tests.urls')
class TestMessagesOutbox(TestCase):
    extensions = ['django.contrib.messages.test.MessagesOutbox']

    def test_set_messages_success(self):
        author = {'name': 'John Doe',
                  'slug': 'success-msg'}
        add_url = reverse('add_success_msg')
        self.client.post(add_url, author)
        self.assertEqual(ContactFormViewWithMsg.success_message % author,
                      messages.outbox[0].message)
