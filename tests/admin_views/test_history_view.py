import re

from django.contrib.admin.models import CHANGE, LogEntry
from django.contrib.admin.tests import AdminPlaywrightTestCase
from django.contrib.auth.models import User
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
class PlaywrightTests(AdminPlaywrightTestCase):
    available_apps = ["admin_views"] + AdminPlaywrightTestCase.available_apps

    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username="super",
            password="secret",
            email="super@example.com",
        )
        for i in range(1, 1101):
            LogEntry.objects.log_actions(
                self.superuser.pk,
                [self.superuser],
                CHANGE,
                change_message=f"Changed something {i}",
            )
        self.admin_login(
            username="super",
            password="secret",
            login_url=reverse("admin:index"),
        )

    def test_pagination(self):
        user_history_url = reverse("admin:auth_user_history", args=(self.superuser.pk,))
        self.page.goto(self.live_server_url + user_history_url)

        paginator = self.page.locator(".paginator")
        self.expect(paginator).to_have_role("navigation")
        labelledby = paginator.get_attribute("aria-labelledby")
        description = self.page.locator("#%s" % labelledby)
        self.expect(description).to_have_text("Pagination user entries")
        self.expect(description).to_have_class("visually-hidden")
        self.expect(paginator).to_be_visible()
        aria_current_link = paginator.locator("[aria-current]")
        self.expect(aria_current_link).to_have_count(1)
        # The current page.
        current_page_link = aria_current_link.first
        self.expect(current_page_link).to_have_attribute("aria-current", "page")
        self.expect(current_page_link).to_have_attribute("href", "")
        self.expect(paginator).to_contain_text("%s entries" % LogEntry.objects.count())
        self.expect(paginator).to_contain_text(str(Paginator.ELLIPSIS))
        self.expect(current_page_link).to_have_text("1")
        # The last page.
        last_page_link = self.page.locator("ul > li:last-child > a")
        self.expect(last_page_link).to_have_text("11")
        # Select the second page.
        pages = paginator.locator("a")
        second_page_link = pages.nth(1)
        self.expect(second_page_link).to_have_text("2")
        second_page_link.click()
        self.expect(self.page).to_have_url(re.compile(r"\?p=2"))
        rows = self.page.locator("#change-history tbody tr")
        self.expect(rows.first).to_contain_text("Changed something 101")
        self.expect(rows.last).to_contain_text("Changed something 200")
