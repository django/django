from django.contrib import admin
from django.contrib.admin.tests import AdminSeleniumTestCase
from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import path, reverse

site = admin.AdminSite(name="test_admin_keyboard_shortcuts")

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
            response, '<button id="open-shortcuts" data-keyboard-shortcut="?">'
        )
        self.assertContains(
            response, '<dialog class="keyboard-shortcuts" id="shortcuts-dialog">'
        )

    def test_shortcuts_dialog_unauthenticated(self):
        self.client.logout()
        response = self.client.get(reverse("test_admin_keyboard_shortcuts:login"))
        self.assertNotContains(
            response, '<button id="open-shortcuts" data-keyboard-shortcut="?">'
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

        body.send_keys("?")
        self.assertTrue(dialog.is_displayed())
        body.send_keys(Keys.ESCAPE)
        self.assertFalse(dialog.is_displayed())
