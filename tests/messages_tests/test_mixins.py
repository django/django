from django.test import SimpleTestCase, override_settings
from django.urls import reverse

from .messages_tests.test_models import SomeObjects
from .messages_tests.urls import ContactFormViewWithMsg, DeleteFormViewWithMsg


@override_settings(ROOT_URLCONF='messages_tests.urls')
class SuccessMessageMixinTests(SimpleTestCase):

    def test_set_messages_success(self):
        author = {'name': 'John Doe', 'slug': 'success-msg'}
        add_url = reverse('add_success_msg')
        req = self.client.post(add_url, author)
        self.assertIn(ContactFormViewWithMsg.success_message % author, req.cookies['messages'].value)

    def test_set_message_success_on_delete(self):
        object_to_delete = SomeObjects.objects.create(name="MyObject")
        delete_url = reverse('success_msg_on_delete', args=[object_to_delete.pk])
        req = self.client.delete(delete_url)
        self.assertIn(DeleteFormViewWithMsg.success_message, req.cookies['messages'].value)
