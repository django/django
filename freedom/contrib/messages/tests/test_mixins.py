from freedom.test import TestCase, override_settings
from freedom.contrib.messages.tests.urls import ContactFormViewWithMsg
from freedom.core.urlresolvers import reverse


@override_settings(ROOT_URLCONF='freedom.contrib.messages.tests.urls')
class SuccessMessageMixinTests(TestCase):

    def test_set_messages_success(self):
        author = {'name': 'John Doe',
                  'slug': 'success-msg'}
        add_url = reverse('add_success_msg')
        req = self.client.post(add_url, author)
        self.assertIn(ContactFormViewWithMsg.success_message % author,
                      req.cookies['messages'].value)
