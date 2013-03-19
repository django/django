from django.test.testcases import TestCase
from django.contrib.messages.tests.urls import ContactFormViewWithMsg
from django.core.urlresolvers import reverse

class SuccessMessageMixinTests(TestCase):
    urls = 'django.contrib.messages.tests.urls'

    def test_set_messages_success(self):
        author = {'name': 'John Doe',
                  'slug': 'success-msg'}
        add_url = reverse('add_success_msg')
        req = self.client.post(add_url, author)
        self.assertIn(ContactFormViewWithMsg.success_message % author,
                      req.cookies['messages'].value)

    def test_set_message_false(self):
        req = self.client.post('/edit/authors/create/msg/',
                               {'name': 'John Doe'})
        self.assertNotIn('messages', req.cookies)
