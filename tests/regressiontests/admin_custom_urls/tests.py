from __future__ import absolute_import, unicode_literals
import warnings

from django.contrib.admin.util import quote
from django.core.urlresolvers import reverse
from django.template.response import TemplateResponse
from django.test import TestCase
from django.test.utils import override_settings

from .models import Action, Person, Car, CarDeprecated


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


@override_settings(PASSWORD_HASHERS=('django.contrib.auth.hashers.SHA1PasswordHasher',))
class CustomRedirects(TestCase):
    fixtures = ['users.json', 'actions.json']

    def setUp(self):
        self.client.login(username='super', password='secret')

    def tearDown(self):
        self.client.logout()

    def test_post_save_add_redirect(self):
        """
        Ensures that ModelAdmin.response_post_save_add() controls the
        redirection after the 'Save' button has been pressed when adding a
        new object.
        Refs 8001, 18310, 19505.
        """
        post_data = { 'name': 'John Doe', }
        self.assertEqual(Person.objects.count(), 0)
        response = self.client.post(
            reverse('admin:admin_custom_urls_person_add'), post_data)
        persons = Person.objects.all()
        self.assertEqual(len(persons), 1)
        self.assertRedirects(
            response, reverse('admin:admin_custom_urls_person_history', args=[persons[0].pk]))

    def test_post_save_change_redirect(self):
        """
        Ensures that ModelAdmin.response_post_save_change() controls the
        redirection after the 'Save' button has been pressed when editing an
        existing object.
        Refs 8001, 18310, 19505.
        """
        Person.objects.create(name='John Doe')
        self.assertEqual(Person.objects.count(), 1)
        person = Person.objects.all()[0]
        post_data = { 'name': 'Jack Doe', }
        response = self.client.post(
            reverse('admin:admin_custom_urls_person_change', args=[person.pk]), post_data)
        self.assertRedirects(
            response, reverse('admin:admin_custom_urls_person_delete', args=[person.pk]))

    def test_post_url_continue(self):
        """
        Ensures that the ModelAdmin.response_add()'s parameter `post_url_continue`
        controls the redirection after an object has been created.
        """
        post_data = { 'name': 'SuperFast', '_continue': '1' }
        self.assertEqual(Car.objects.count(), 0)
        response = self.client.post(
            reverse('admin:admin_custom_urls_car_add'), post_data)
        cars = Car.objects.all()
        self.assertEqual(len(cars), 1)
        self.assertRedirects(
            response, reverse('admin:admin_custom_urls_car_history', args=[cars[0].pk]))

    def test_post_url_continue_string_formats(self):
        """
        Ensures that string formats are accepted for post_url_continue. This
        is a deprecated functionality that will be removed in Django 1.6 along
        with this test.
        """
        with warnings.catch_warnings(record=True) as w:
            post_data = { 'name': 'SuperFast', '_continue': '1' }
            self.assertEqual(Car.objects.count(), 0)
            response = self.client.post(
                reverse('admin:admin_custom_urls_cardeprecated_add'), post_data)
            cars = CarDeprecated.objects.all()
            self.assertEqual(len(cars), 1)
            self.assertRedirects(
                response, reverse('admin:admin_custom_urls_cardeprecated_history', args=[cars[0].pk]))
        self.assertEqual(len(w), 1)
        self.assertTrue(isinstance(w[0].message, DeprecationWarning))
