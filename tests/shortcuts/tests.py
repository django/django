from django.test import TestCase
from django.test.utils import override_settings


@override_settings(ROOT_URLCONF='shortcuts.urls')
class RenderShortcutsTest(TestCase):

    def test_request_context_instance_misuse(self):
        """
        For backwards-compatibility, ensure that it's possible to pass a
        RequestContext instance in the dictionary argument instead of the
        context_instance argument.
        """
        response = self.client.get('/request_context_misuse/')
        self.assertContains(response, 'context processor output')
