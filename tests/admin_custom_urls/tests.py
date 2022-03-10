from django.contrib.admin.utils import quote
from django.contrib.admin.views.main import IS_POPUP_VAR
from django.contrib.auth.models import User
from django.template.response import TemplateResponse
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Action, Car, Person


@override_settings(
    ROOT_URLCONF="admin_custom_urls.urls",
)
class AdminCustomUrlsTest(TestCase):
    """
    Remember that:
    * The Action model has a CharField PK.
    * The ModelAdmin for Action customizes the add_view URL, it's
      '<app name>/<model name>/!add/'
    """

    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            username="super", password="secret", email="super@example.com"
        )
        Action.objects.create(name="delete", description="Remove things.")
        Action.objects.create(name="rename", description="Gives things other names.")
        Action.objects.create(name="add", description="Add things.")
        Action.objects.create(
            name="path/to/file/", description="An action with '/' in its name."
        )
        Action.objects.create(
            name="path/to/html/document.html",
            description="An action with a name similar to a HTML doc path.",
        )
        Action.objects.create(
            name="javascript:alert('Hello world');\">Click here</a>",
            description="An action with a name suspected of being a XSS attempt",
        )

    def setUp(self):
        self.client.force_login(self.superuser)

    def test_basic_add_GET(self):
        """
        Ensure GET on the add_view works.
        """
        add_url = reverse("admin_custom_urls:admin_custom_urls_action_add")
        self.assertTrue(add_url.endswith("/!add/"))
        response = self.client.get(add_url)
        self.assertIsInstance(response, TemplateResponse)
        self.assertEqual(response.status_code, 200)

    def test_add_with_GET_args(self):
        """
        Ensure GET on the add_view plus specifying a field value in the query
        string works.
        """
        response = self.client.get(
            reverse("admin_custom_urls:admin_custom_urls_action_add"),
            {"name": "My Action"},
        )
        self.assertContains(response, 'value="My Action"')

    def test_basic_add_POST(self):
        """
        Ensure POST on add_view works.
        """
        post_data = {
            IS_POPUP_VAR: "1",
            "name": "Action added through a popup",
            "description": "Description of added action",
        }
        response = self.client.post(
            reverse("admin_custom_urls:admin_custom_urls_action_add"), post_data
        )
        self.assertContains(response, "Action added through a popup")

    def test_admin_URLs_no_clash(self):
        # Should get the change_view for model instance with PK 'add', not show
        # the add_view
        url = reverse(
            "admin_custom_urls:%s_action_change" % Action._meta.app_label,
            args=(quote("add"),),
        )
        response = self.client.get(url)
        self.assertContains(response, "Change action")

        # Should correctly get the change_view for the model instance with the
        # funny-looking PK (the one with a 'path/to/html/document.html' value)
        url = reverse(
            "admin_custom_urls:%s_action_change" % Action._meta.app_label,
            args=(quote("path/to/html/document.html"),),
        )
        response = self.client.get(url)
        self.assertContains(response, "Change action")
        self.assertContains(response, 'value="path/to/html/document.html"')

    def test_post_save_add_redirect(self):
        """
        ModelAdmin.response_post_save_add() controls the redirection after
        the 'Save' button has been pressed when adding a new object.
        """
        post_data = {"name": "John Doe"}
        self.assertEqual(Person.objects.count(), 0)
        response = self.client.post(
            reverse("admin_custom_urls:admin_custom_urls_person_add"), post_data
        )
        persons = Person.objects.all()
        self.assertEqual(len(persons), 1)
        redirect_url = reverse(
            "admin_custom_urls:admin_custom_urls_person_history", args=[persons[0].pk]
        )
        self.assertRedirects(response, redirect_url)

    def test_post_save_change_redirect(self):
        """
        ModelAdmin.response_post_save_change() controls the redirection after
        the 'Save' button has been pressed when editing an existing object.
        """
        Person.objects.create(name="John Doe")
        self.assertEqual(Person.objects.count(), 1)
        person = Person.objects.all()[0]
        post_url = reverse(
            "admin_custom_urls:admin_custom_urls_person_change", args=[person.pk]
        )
        response = self.client.post(post_url, {"name": "Jack Doe"})
        self.assertRedirects(
            response,
            reverse(
                "admin_custom_urls:admin_custom_urls_person_delete", args=[person.pk]
            ),
        )

    def test_post_url_continue(self):
        """
        The ModelAdmin.response_add()'s parameter `post_url_continue` controls
        the redirection after an object has been created.
        """
        post_data = {"name": "SuperFast", "_continue": "1"}
        self.assertEqual(Car.objects.count(), 0)
        response = self.client.post(
            reverse("admin_custom_urls:admin_custom_urls_car_add"), post_data
        )
        cars = Car.objects.all()
        self.assertEqual(len(cars), 1)
        self.assertRedirects(
            response,
            reverse(
                "admin_custom_urls:admin_custom_urls_car_history", args=[cars[0].pk]
            ),
        )
