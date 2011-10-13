from __future__ import absolute_import

from django.core.urlresolvers import reverse
from django.template.response import TemplateResponse
from django.test import TestCase

from .models import Action


class AdminCustomUrlsTest(TestCase):
    fixtures = ['users.json', 'actions.json']

    def setUp(self):
        self.client.login(username='super', password='secret')

    def tearDown(self):
        self.client.logout()

    def testBasicAddGet(self):
        """
        A smoke test to ensure GET on the add_view works.
        """
        response = self.client.get('/custom_urls/admin/admin_custom_urls/action/!add/')
        self.assertIsInstance(response, TemplateResponse)
        self.assertEqual(response.status_code, 200)

    def testAddWithGETArgs(self):
        response = self.client.get('/custom_urls/admin/admin_custom_urls/action/!add/', {'name': 'My Action'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            'value="My Action"' in response.content,
            "Couldn't find an input with the right value in the response."
        )

    def testBasicAddPost(self):
        """
        A smoke test to ensure POST on add_view works.
        """
        post_data = {
            '_popup': u'1',
            "name": u'Action added through a popup',
            "description": u"Description of added action",
        }
        response = self.client.post('/custom_urls/admin/admin_custom_urls/action/!add/', post_data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'dismissAddAnotherPopup')
        self.assertContains(response, 'Action added through a popup')

    def testAdminUrlsNoClash(self):
        """
        Test that some admin URLs work correctly. The model has a CharField
        PK and the add_view URL has been customized.
        """
        # Should get the change_view for model instance with PK 'add', not show
        # the add_view
        response = self.client.get('/custom_urls/admin/admin_custom_urls/action/add/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Change action')

        # Ditto, but use reverse() to build the URL
        path = reverse('admin:%s_action_change' % Action._meta.app_label,
                args=('add',))
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Change action')

        # Should correctly get the change_view for the model instance with the
        # funny-looking PK
        path = reverse('admin:%s_action_change' % Action._meta.app_label,
                args=("path/to/html/document.html",))
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Change action')
        self.assertContains(response, 'value="path/to/html/document.html"')
