from django.contrib.admin.models import CHANGE, LogEntry
from django.contrib.admin.tests import AdminSeleniumTestCase
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.paginator import Paginator
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import City, State


@override_settings(ROOT_URLCONF="admin_views.urls")
class AdminHistoryViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            username="super",
            password="secret",
            email="super@example.com",
        )

    def setUp(self):
        self.client.force_login(self.superuser)

    def test_changed_message_uses_form_labels(self):
        """
        Admin's model history change messages use form labels instead of
        field names.
        """
        state = State.objects.create(name="My State Name")
        city = City.objects.create(name="My City Name", state=state)
        change_dict = {
            "name": "My State Name 2",
            "nolabel_form_field": True,
            "city_set-0-name": "My City name 2",
            "city_set-0-id": city.pk,
            "city_set-TOTAL_FORMS": "3",
            "city_set-INITIAL_FORMS": "1",
            "city_set-MAX_NUM_FORMS": "0",
        }
        state_change_url = reverse("admin:admin_views_state_change", args=(state.pk,))
        self.client.post(state_change_url, change_dict)
        logentry = LogEntry.objects.filter(content_type__model__iexact="state").latest(
            "id"
        )
        self.assertEqual(
            logentry.get_change_message(),
            "Changed State name (from form’s Meta.labels), "
            "nolabel_form_field and not_a_form_field. "
            "Changed City verbose_name for city “%s”." % city,
        )


@override_settings(ROOT_URLCONF="admin_views.urls")
class SeleniumTests(AdminSeleniumTestCase):
    available_apps = ["admin_views"] + AdminSeleniumTestCase.available_apps

    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username="super",
            password="secret",
            email="super@example.com",
        )
        content_type_pk = ContentType.objects.get_for_model(User).pk
        for i in range(1, 1101):
            LogEntry.objects.log_action(
                self.superuser.pk,
                content_type_pk,
                self.superuser.pk,
                repr(self.superuser),
                CHANGE,
                change_message=f"Changed something {i}",
            )
        self.admin_login(
            username="super",
            password="secret",
            login_url=reverse("admin:index"),
        )

    def test_pagination(self):
        from selenium.webdriver.common.by import By

        user_history_url = reverse("admin:auth_user_history", args=(self.superuser.pk,))
        self.selenium.get(self.live_server_url + user_history_url)

        paginator = self.selenium.find_element(By.CSS_SELECTOR, ".paginator")
        self.assertTrue(paginator.is_displayed())
        self.assertIn("%s entries" % LogEntry.objects.count(), paginator.text)
        self.assertIn(str(Paginator.ELLIPSIS), paginator.text)
        # The current page.
        current_page_link = self.selenium.find_element(
            By.CSS_SELECTOR, "span.this-page"
        )
        self.assertEqual(current_page_link.text, "1")
        # The last page.
        last_page_link = self.selenium.find_element(By.CSS_SELECTOR, ".end")
        self.assertTrue(last_page_link.text, "20")
        # Select the second page.
        pages = paginator.find_elements(By.TAG_NAME, "a")
        second_page_link = pages[0]
        self.assertEqual(second_page_link.text, "2")
        second_page_link.click()
        self.assertIn("?p=2", self.selenium.current_url)
        rows = self.selenium.find_elements(By.CSS_SELECTOR, "#change-history tbody tr")
        self.assertIn("Changed something 101", rows[0].text)
        self.assertIn("Changed something 200", rows[-1].text)
