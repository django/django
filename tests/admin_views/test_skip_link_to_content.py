from django.contrib.admin.tests import AdminPlaywrightTestCase
from django.contrib.auth.models import User
from django.test import override_settings
from django.urls import reverse

from .models import Podcast


@override_settings(ROOT_URLCONF="admin_views.urls")
class PlaywrightTests(AdminPlaywrightTestCase):
    available_apps = ["admin_views"] + AdminPlaywrightTestCase.available_apps

    def setUp(self):
        if self.browser == "webkit":
            self.skipTest("WebKit Tab key only focuses form controls, not links.")
        self.superuser = User.objects.create_superuser(
            username="super",
            password="secret",
            email="super@example.com",
        )

    def test_use_skip_link_to_content(self):
        self.admin_login(
            username="super",
            password="secret",
            login_url=reverse("admin:index"),
        )

        # `Skip link` is not present.
        skip_link = self.page.locator(".skip-to-content-link")
        self.expect(skip_link).not_to_be_in_viewport()

        # 1st TAB is pressed, `skip link` is shown.
        self.page.keyboard.press("Tab")
        self.expect(skip_link).to_be_in_viewport()

        # Press RETURN to skip the navbar links (view site / documentation /
        # change password / log out) and focus first model in the admin_views
        # list.
        self.page.keyboard.press("Enter")
        self.expect(skip_link).not_to_be_in_viewport()  # `skip link` disappear.
        tab_count = 1 if self.browser == "firefox" else 2
        for _ in range(tab_count):
            self.page.keyboard.press("Tab")
        actors_link = self.page.get_by_role("link", name="Actors")
        self.expect(actors_link).to_be_focused()

        # Go to Actors changelist, skip sidebar and focus "Add actor +".
        actors_link.press("Enter")
        self.page.wait_for_load_state("load")
        self.page.keyboard.press("Tab")
        skip_link = self.page.locator(".skip-to-content-link")
        self.expect(skip_link).to_be_in_viewport()
        self.page.keyboard.press("Enter")
        self.page.keyboard.press("Tab")
        actors_add_url = reverse("admin:admin_views_actor_add")
        actors_add_link = self.page.locator(f"#content [href='{actors_add_url}']")
        self.expect(actors_add_link).to_be_focused()

        # Go to the Actor form and the first input will be focused
        # automatically.
        actors_add_link.press("Enter")
        first_input = self.page.locator("#id_name")
        self.expect(first_input).to_be_focused()

    def test_dont_use_skip_link_to_content(self):
        self.admin_login(
            username="super",
            password="secret",
            login_url=reverse("admin:index"),
        )

        # `Skip link` is not present.
        skip_link = self.page.locator(".skip-to-content-link")
        self.expect(skip_link).not_to_be_in_viewport()

        # 1st TAB is pressed, `skip link` is shown.
        self.page.keyboard.press("Tab")
        self.expect(skip_link).to_be_in_viewport()

        # The 2nd TAB will focus the page title.
        self.page.keyboard.press("Tab")
        django_administration_title = self.page.get_by_role(
            "link", name="Django administration"
        )
        self.expect(skip_link).not_to_be_in_viewport()  # `skip link` disappear.
        self.expect(django_administration_title).to_be_focused()

    def test_skip_link_with_RTL_language_doesnt_create_horizontal_scrolling(self):
        with override_settings(LANGUAGE_CODE="ar"):
            self.admin_login(
                username="super",
                password="secret",
                login_url=reverse("admin:index"),
            )

            self.page.goto(f"{self.live_server_url}{reverse('admin:index')}")

            skip_link = self.page.locator(".skip-to-content-link")
            body = self.page.locator("body")
            self.page.keyboard.press("Tab")
            self.expect(skip_link).to_be_in_viewport()

            is_vertical_scrolleable = body.evaluate(
                "el => el.scrollHeight > el.offsetHeight"
            )
            is_horizontal_scrolleable = body.evaluate(
                "el => el.scrollWidth > el.offsetWidth"
            )
            self.assertTrue(is_vertical_scrolleable)
            self.assertFalse(is_horizontal_scrolleable)

    def test_skip_link_keyboard_navigation_in_changelist(self):
        Podcast.objects.create(name="apple", release_date="2000-09-19")
        self.admin_login(
            username="super",
            password="secret",
            login_url=reverse("admin:index"),
        )
        self.page.goto(
            self.live_server_url + reverse("admin:admin_views_podcast_changelist")
        )
        selectors = [
            "ul.object-tools",  # object_tools.
            "search#changelist-filter",  # list_filter.
            "form#changelist-search",  # search_fields.
            "nav.toplinks",  # date_hierarchy.
            "form#changelist-form div.actions",  # action.
            "table#result_list",  # table.
            "div.changelist-footer",  # footer.
        ]
        self.page.locator("#content-start").press("Tab")

        for selector in selectors:
            with self.subTest(selector=selector):
                # Currently focused element.
                focused_outer_html = self.page.evaluate(
                    "document.activeElement.outerHTML"
                )
                expected_inner_html = self.page.locator(selector).inner_html()
                element_points = self.page.locator(
                    f"{selector} a, {selector} input, {selector} button"
                ).all()
                self.assertIn(focused_outer_html, expected_inner_html)
                # Move to the next container element via TAB.
                for point in element_points[::-1]:
                    if point.is_visible():
                        point.press("Tab")
                        break
