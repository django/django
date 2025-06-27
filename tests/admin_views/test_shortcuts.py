from contextlib import contextmanager

from django.contrib import admin
from django.contrib.admin.tests import AdminSeleniumTestCase
from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import path, reverse

from .admin import Color

site = admin.AdminSite(name="test_admin_keyboard_shortcuts")
site.register(Color)

urlpatterns = [
    path("test_admin_keyboard_shortcuts/", site.urls),
]


@override_settings(ROOT_URLCONF="admin_views.test_shortcuts")
class AdminKeyboardShorcutsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            username="super",
            password="secret",
            email="super@example.com",
        )

    def setUp(self):
        self.client.force_login(self.superuser)

    def test_shortcuts_dialog_on_index(self):
        response = self.client.get(reverse("test_admin_keyboard_shortcuts:index"))
        self.assertContains(
            response, '<button id="open-shortcuts" aria-keyshortcuts="?">'
        )
        self.assertContains(
            response, '<dialog class="keyboard-shortcuts" id="shortcuts-dialog">'
        )

    def test_shortcuts_dialog_unauthenticated(self):
        self.client.logout()
        response = self.client.get(reverse("test_admin_keyboard_shortcuts:login"))
        self.assertNotContains(
            response, '<button id="open-shortcuts" aria-keyshortcuts="?">'
        )
        self.assertNotContains(
            response, '<dialog class="keyboard-shortcuts" id="shortcuts-dialog">'
        )
        self.assertNotContains(
            response, '<script src="/static/admin/js/shortcuts.js"></script>'
        )

    def test_shortcuts_dialog_descriptions(self):
        response = self.client.get(reverse("test_admin_keyboard_shortcuts:index"))
        self.assertContains(
            response,
            '<dt class="shortcut-description">Show this dialog</dt>'
            '<dd class="shortcut-keys"><kbd>?</kbd></dd>',
            html=True,
        )


@override_settings(ROOT_URLCONF="admin_views.test_shortcuts")
class SeleniumTests(AdminSeleniumTestCase):
    available_apps = ["admin_views"] + AdminSeleniumTestCase.available_apps

    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username="super",
            password="secret",
            email="super@example.com",
        )
        self.admin_login(
            username="super",
            password="secret",
            login_url=reverse("test_admin_keyboard_shortcuts:index"),
        )

    @contextmanager
    def assertElementClicked(self, css_selector):
        """
        Modifies the element's onclick handler
        to set a data attribute when clicked, and asserts that the element is clicked
        by checking for that attribute after the context block.
        """
        from selenium.webdriver.common.by import By

        self.selenium.execute_script(
            f"""
            document.querySelector("{css_selector}").onclick = function() {{
                this.setAttribute("data-clicked", "true");
            }};
            """
        )
        yield

        el = self.selenium.find_element(By.CSS_SELECTOR, css_selector)
        self.assertEqual(el.get_attribute("data-clicked"), "true")

    def test_shortcuts_dialog_open_close_with_buttons(self):
        from selenium.webdriver.common.by import By

        dialog = self.selenium.find_element(By.ID, "shortcuts-dialog")
        open_btn = self.selenium.find_element(By.ID, "open-shortcuts")
        close_btn = dialog.find_element(By.XPATH, ".//button[@aria-label='Close']")

        # dialog is closed initially
        self.assertFalse(dialog.is_displayed())

        open_btn.click()
        self.assertTrue(dialog.is_displayed())
        close_btn.click()
        self.assertFalse(dialog.is_displayed())

    def test_shortcuts_dialog_open_close_with_keys(self):
        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.keys import Keys

        body = self.selenium.find_element(By.TAG_NAME, "body")
        dialog = self.selenium.find_element(By.ID, "shortcuts-dialog")

        with self.assertElementClicked("#open-shortcuts"):
            body.send_keys("?")
        self.assertTrue(dialog.is_displayed())
        body.send_keys(Keys.ESCAPE)
        self.assertFalse(dialog.is_displayed())

    def test_go_to_index(self):
        from selenium.webdriver.common.by import By

        # Url other than admin index to start with
        self.selenium.get(
            self.live_server_url
            + reverse("test_admin_keyboard_shortcuts:password_change")
        )
        body = self.selenium.find_element(By.TAG_NAME, "body")
        with self.wait_page_loaded():
            body.send_keys("gi")
        self.assertEqual(
            self.selenium.current_url,
            self.live_server_url + reverse("test_admin_keyboard_shortcuts:index"),
        )

    def test_changeform_add(self):
        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.keys import Keys

        self.selenium.get(
            self.live_server_url
            + reverse("test_admin_keyboard_shortcuts:admin_views_color_add")
        )
        body = self.selenium.find_element(By.TAG_NAME, "body")
        with self.assertElementClicked("input[name=_save]"):
            body.send_keys(Keys.ALT, "s")
