from django.contrib.messages import constants
from django.test import TestCase, override_settings
from django.urls import reverse

from .test_session import SessionTests, set_session_data
from .utils import PermanentStorage


class CustomStorageTests(SessionTests, TestCase):
    storage_class = PermanentStorage

    def test_get(self):
        storage = self.storage_class(self.get_request())
        example_messages = ["test", "me"]
        set_session_data(storage, example_messages)
        self.assertEqual(list(storage), example_messages)

    @override_settings(MESSAGE_LEVEL=constants.DEBUG)
    def test_with_template_response(self):
        data = {
            "messages": ["Test message %d" % x for x in range(5)],
            "permanent": [bool(x % 2) for x in range(5)],
        }
        show_url = reverse("show_template_response")
        for level in self.levels:
            add_url = reverse("add_template_response_extra", args=(level,))
            response = self.client.post(add_url, data, follow=True)
            self.assertRedirects(response, show_url)
            self.assertIn("messages", response.context)
            for msg in data["messages"]:
                self.assertContains(response, msg)

            # there shouldn't be any messages on second GET request
            response = self.client.get(show_url)
            for idx, msg in enumerate(data["messages"]):
                if data["permanent"][idx]:
                    self.assertContains(response, msg)
                else:
                    self.assertNotContains(response, msg)
