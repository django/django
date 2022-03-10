from django.core.signing import b64_decode
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import SomeObject
from .urls import ContactFormViewWithMsg, DeleteFormViewWithMsg


@override_settings(ROOT_URLCONF="messages_tests.urls")
class SuccessMessageMixinTests(TestCase):
    def test_set_messages_success(self):
        author = {"name": "John Doe", "slug": "success-msg"}
        add_url = reverse("add_success_msg")
        req = self.client.post(add_url, author)
        # Uncompressed message is stored in the cookie.
        value = b64_decode(
            req.cookies["messages"].value.split(":")[0].encode(),
        ).decode()
        self.assertIn(ContactFormViewWithMsg.success_message % author, value)

    def test_set_messages_success_on_delete(self):
        object_to_delete = SomeObject.objects.create(name="MyObject")
        delete_url = reverse("success_msg_on_delete", args=[object_to_delete.pk])
        response = self.client.post(delete_url, follow=True)
        self.assertContains(response, DeleteFormViewWithMsg.success_message)
