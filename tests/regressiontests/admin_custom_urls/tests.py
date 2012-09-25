from __future__ import absolute_import, unicode_literals

from django.contrib.admin.util import quote
from django.core.urlresolvers import reverse
from django.template.response import TemplateResponse
from django.test import TestCase
from django.test.utils import override_settings

from .models import Action


@override_settings(PASSWORD_HASHERS=('django.contrib.auth.hashers.SHA1PasswordHasher',))
class AdminCustomUrlsTest(TestCase):
    """
    Remember that:
    * The Action model has a CharField PK.
    * The ModelAdmin for Action customizes the add_view URL, it's
      '<app name>/<model name>/!add/'
    """
    fixtures = ['users.json', 'actions.json']

    def setUp(self):
        self.client.login(username='super', password='secret')

    def tearDown(self):
        self.client.logout()

    def testBasicAddGet(self):
        """
        Ensure GET on the add_view works.
        """
        response = self.client.get('/custom_urls/admin/admin_custom_urls/action/!add/')
        self.assertIsInstance(response, TemplateResponse)
        self.assertEqual(response.status_code, 200)

    def testAddWithGETArgs(self):
        """
        Ensure GET on the add_view plus specifying a field value in the query
        string works.
        """
        response = self.client.get('/custom_urls/admin/admin_custom_urls/action/!add/', {'name': 'My Action'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'value="My Action"')

    def testBasicAddPost(self):
        """
        Ensure POST on add_view works.
        """
        post_data = {
            '_popup': '1',
            "name": 'Action added through a popup',
            "description": "Description of added action",
        }
        response = self.client.post('/custom_urls/admin/admin_custom_urls/action/!add/', post_data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'dismissAddAnotherPopup')
        self.assertContains(response, 'Action added through a popup')

    def testAdminUrlsNoClash(self):
        """
        Test that some admin URLs work correctly.
        """
        # Should get the change_view for model instance with PK 'add', not show
        # the add_view
        response = self.client.get('/custom_urls/admin/admin_custom_urls/action/add/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Change action')

        # Ditto, but use reverse() to build the URL
        url = reverse('admin:%s_action_change' % Action._meta.app_label,
                args=(quote('add'),))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Change action')

        # Should correctly get the change_view for the model instance with the
        # funny-looking PK (the one wth a 'path/to/html/document.html' value)
        url = reverse('admin:%s_action_change' % Action._meta.app_label,
                args=(quote("path/to/html/document.html"),))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Change action')
        self.assertContains(response, 'value="path/to/html/document.html"')
