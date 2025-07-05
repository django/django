from contextlib import contextmanager

from django.contrib import admin
from django.contrib.admin.tests import AdminSeleniumTestCase
from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import path, reverse

from .admin import Language, LanguageAdmin

site = admin.AdminSite(name="test_admin_keyboard_shortcuts")
site.register(Language, LanguageAdmin)

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
        self.assertContains(response, '<input type="checkbox" id="toggle-shortcuts">')

    def test_shortcuts_dialog_not_on_login(self):
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

    @contextmanager
    def shortcuts_dialog_opened(self):
        """Temporarily opens the shortcuts dialog
        for interacting with elements within dialog
        """
        from selenium.webdriver.common.by import By

        dialog = self.selenium.find_element(By.ID, "shortcuts-dialog")
        open_btn = self.selenium.find_element(By.ID, "open-shortcuts")
        close_btn = dialog.find_element(By.XPATH, ".//button[@aria-label='Close']")

        open_btn.click()
        yield
        close_btn.click()

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

        # Enable shortcuts for most of the tests
        self.selenium.execute_script(
            "localStorage.setItem('django.admin.shortcutsEnabled', 'true')"
        )
        self.selenium.refresh()

    def test_shortcuts_toggle_off_by_default(self):
        from selenium.webdriver.common.by import By

        self.selenium.execute_script(
            "localStorage.removeItem('django.admin.shortcutsEnabled')"
        )
        self.selenium.refresh()
        toggle = self.selenium.find_element(By.ID, "toggle-shortcuts")
        self.assertFalse(toggle.is_selected())

    def test_shortcuts_toggle_state_persists(self):
        from selenium.webdriver.common.by import By

        # Start with toggle off state
        toggle = self.selenium.find_element(By.ID, "toggle-shortcuts")
        if toggle.is_selected():
            with self.shortcuts_dialog_opened():
                toggle.click()

        # Enable shortcuts
        with self.shortcuts_dialog_opened():
            toggle.click()
        self.assertTrue(toggle.is_selected())
        self.assertEqual(
            self.selenium.execute_script(
                "return localStorage.getItem('django.admin.shortcutsEnabled')"
            ),
            "true",
        )

        # Check state persists after refresh
        self.selenium.refresh()
        toggle = self.selenium.find_element(By.ID, "toggle-shortcuts")
        self.assertTrue(toggle.is_selected())

        # Disable shortcuts
        with self.shortcuts_dialog_opened():
            toggle.click()
        self.assertFalse(toggle.is_selected())
        self.assertEqual(
            self.selenium.execute_script(
                "return localStorage.getItem('django.admin.shortcutsEnabled')"
            ),
            "false",
        )

        # Check state persists after refresh
        self.selenium.refresh()
        toggle = self.selenium.find_element(By.ID, "toggle-shortcuts")
        self.assertFalse(toggle.is_selected())

    def test_shortcuts_disabled_when_toggle_off(self):
        from selenium.webdriver.common.by import By

        toggle = self.selenium.find_element(By.ID, "toggle-shortcuts")

        # Toggle off
        if toggle.is_selected():
            with self.shortcuts_dialog_opened():
                toggle.click()

        # "?" shortcut key does not open the shortcuts dialog
        self.selenium.find_element(By.TAG_NAME, "body").send_keys("?")
        self.assertFalse(
            self.selenium.find_element(By.ID, "shortcuts-dialog").is_displayed()
        )

    def test_shortcut_global_open_shortcuts_dialog(self):
        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.keys import Keys

        body = self.selenium.find_element(By.TAG_NAME, "body")
        dialog = self.selenium.find_element(By.ID, "shortcuts-dialog")

        body.send_keys("?")
        self.assertTrue(dialog.is_displayed())
        body.send_keys(Keys.ESCAPE)
        self.assertFalse(dialog.is_displayed())

    def test_shortcut_global_go_to_index(self):
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

    def test_shortcut_changelist_focus_next_row(self):
        from selenium.webdriver.common.by import By

        Language.objects.create(iso="l1")
        Language.objects.create(iso="l2")

        self.selenium.get(
            self.live_server_url
            + reverse("test_admin_keyboard_shortcuts:admin_views_language_changelist")
        )

        body = self.selenium.find_element(By.TAG_NAME, "body")
        action_toggle_checkbox = self.selenium.find_element(By.ID, "action-toggle")
        l1_checkbox = self.selenium.find_element(
            By.CSS_SELECTOR, "input[name='_selected_action'][value='l1']"
        )
        l2_checkbox = self.selenium.find_element(
            By.CSS_SELECTOR, "input[name='_selected_action'][value='l2']"
        )

        # On first trigger, "focus next row" shortcut
        # focuses Select all objects checkbox
        body.send_keys("j")
        self.assertEqual(self.selenium.switch_to.active_element, action_toggle_checkbox)

        body.send_keys("j")
        self.assertEqual(self.selenium.switch_to.active_element, l1_checkbox)

        body.send_keys("j")
        self.assertEqual(self.selenium.switch_to.active_element, l2_checkbox)

        # Rolls over from last row/checkbox to the first row/checkbox
        body.send_keys("j")
        self.assertEqual(self.selenium.switch_to.active_element, action_toggle_checkbox)

    def test_shortcut_changelist_focus_previous_row(self):
        from selenium.webdriver.common.by import By

        Language.objects.create(iso="l1")
        Language.objects.create(iso="l2")

        self.selenium.get(
            self.live_server_url
            + reverse("test_admin_keyboard_shortcuts:admin_views_language_changelist")
        )

        body = self.selenium.find_element(By.TAG_NAME, "body")
        l1_checkbox = self.selenium.find_element(
            By.CSS_SELECTOR, "input[name='_selected_action'][value='l1']"
        )
        l2_checkbox = self.selenium.find_element(
            By.CSS_SELECTOR, "input[name='_selected_action'][value='l2']"
        )

        # On first trigger, "focus previous row" shortcut focuses last row/checkbox
        body.send_keys("k")
        self.assertEqual(self.selenium.switch_to.active_element, l2_checkbox)

        body.send_keys("k")
        self.assertEqual(self.selenium.switch_to.active_element, l1_checkbox)

    def test_shortcut_changelist_toggle_row_selection(self):
        from selenium.webdriver.common.by import By

        Language.objects.create(iso="l1")
        Language.objects.create(iso="l2")

        self.selenium.get(
            self.live_server_url
            + reverse("test_admin_keyboard_shortcuts:admin_views_language_changelist")
        )

        body = self.selenium.find_element(By.TAG_NAME, "body")
        action_toggle_checkbox = self.selenium.find_element(By.ID, "action-toggle")
        l1_checkbox = self.selenium.find_element(
            By.CSS_SELECTOR, "input[name='_selected_action'][value='l1']"
        )
        l2_checkbox = self.selenium.find_element(
            By.CSS_SELECTOR, "input[name='_selected_action'][value='l2']"
        )

        # Mark l2
        body.send_keys("k")
        self.assertEqual(self.selenium.switch_to.active_element, l2_checkbox)

        body.send_keys("x")
        self.assertTrue(l2_checkbox.is_selected())

        # Unmark l2
        body.send_keys("x")
        self.assertFalse(l2_checkbox.is_selected())

        # Mark action toggle checkbox
        body.send_keys("kk")
        self.assertEqual(self.selenium.switch_to.active_element, action_toggle_checkbox)

        body.send_keys("x")
        self.assertTrue(action_toggle_checkbox.is_selected())
        self.assertTrue(l1_checkbox.is_selected())
        self.assertTrue(l2_checkbox.is_selected())

    def test_shortcut_changelist_focus_actions_dropdown(self):
        from selenium.webdriver.common.by import By

        Language.objects.create(iso="l1")

        self.selenium.get(
            self.live_server_url
            + reverse("test_admin_keyboard_shortcuts:admin_views_language_changelist")
        )

        body = self.selenium.find_element(By.TAG_NAME, "body")
        actions_dropdown = self.selenium.find_element(
            By.CSS_SELECTOR, "select[name='action']"
        )

        body.send_keys("a")
        self.assertEqual(self.selenium.switch_to.active_element, actions_dropdown)
