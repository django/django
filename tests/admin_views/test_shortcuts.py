from contextlib import contextmanager

from django.contrib import admin
from django.contrib.admin.tests import AdminSeleniumTestCase
from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import path, reverse

from .admin import Language, LanguageAdmin, Paper


class Shortcuts:
    class Global:
        SHOW_DIALOG = "?"
        CLOSE_DIALOG = "Escape"
        GO_TO_INDEX = "g i"

    class ChangeList:
        FOCUS_PREV_ROW = "k"
        FOCUS_NEXT_ROW = "j"
        TOGGLE_ROW_SELECTION = "x"
        FOCUS_ACTIONS_DROPDOWN = "a"

    class ChangeForm:
        SAVE = "Alt+s"
        SAVE_AND_CONTINUE = "Alt+c"
        SAVE_AND_ADD_ANOTHER = "Alt+a"
        DELETE = "Alt+d"

    class DeleteConfirmation:
        CONFIRM_DELETE = "Alt+y"
        CANCEL_DELETE = "Alt+n"


site = admin.AdminSite(name="test_admin_keyboard_shortcuts")
site.register(Language, LanguageAdmin)
site.register(Paper)

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
            response,
            '<button id="open-shortcuts"'
            f' aria-keyshortcuts="{Shortcuts.Global.SHOW_DIALOG}">',
        )
        self.assertContains(
            response, '<dialog class="keyboard-shortcuts" id="shortcuts-dialog">'
        )
        self.assertContains(response, '<input type="checkbox" id="toggle-shortcuts">')

    def test_shortcuts_dialog_not_on_login(self):
        self.client.logout()
        response = self.client.get(reverse("test_admin_keyboard_shortcuts:login"))
        self.assertNotContains(
            response,
            '<button id="open-shortcuts"'
            f' aria-keyshortcuts="{Shortcuts.Global.SHOW_DIALOG}">',
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
            f'<dd class="shortcut-keys"><kbd>{Shortcuts.Global.SHOW_DIALOG}</kbd></dd>',
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

    def perform_shortcut(self, shortcut):
        """Perform the keyboard shortcut using Selenium."""
        from selenium.webdriver.common.action_chains import ActionChains
        from selenium.webdriver.common.keys import Keys

        # split the shortcut keys string into list of list of keys
        # e.g. "Ctrl+S Alt+Shift+X" -> [["Ctrl", "S"], ["Alt", "Shift", "X"]]
        key_combos = [key_combo.split("+") for key_combo in shortcut.split(" ")]

        # parse modifiers
        special_keys = {
            "ctrl": Keys.CONTROL,
            "alt": Keys.ALT,
            "shift": Keys.SHIFT,
            "escape": Keys.ESCAPE,
        }
        key_combos = [
            [special_keys.get(key.lower(), key) for key in combo]
            for combo in key_combos
        ]

        # perform the key combinations
        actions = ActionChains(self.selenium)
        for combo in key_combos:
            for key in combo:
                actions.key_down(key)
            for key in combo:
                actions.key_up(key)
        actions.perform()

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
        self.perform_shortcut(Shortcuts.Global.SHOW_DIALOG)
        self.assertFalse(
            self.selenium.find_element(By.ID, "shortcuts-dialog").is_displayed()
        )

    def test_shortcut_global_open_shortcuts_dialog(self):
        from selenium.webdriver.common.by import By

        dialog = self.selenium.find_element(By.ID, "shortcuts-dialog")

        self.perform_shortcut(Shortcuts.Global.SHOW_DIALOG)
        self.assertTrue(dialog.is_displayed())
        self.perform_shortcut(Shortcuts.Global.CLOSE_DIALOG)
        self.assertFalse(dialog.is_displayed())

    def test_shortcut_global_go_to_index(self):
        # Url other than admin index to start with
        self.selenium.get(
            self.live_server_url
            + reverse("test_admin_keyboard_shortcuts:admin_views_language_changelist")
        )
        with self.wait_page_loaded():
            self.perform_shortcut(Shortcuts.Global.GO_TO_INDEX)
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

        action_toggle_checkbox = self.selenium.find_element(By.ID, "action-toggle")
        l1_checkbox = self.selenium.find_element(
            By.CSS_SELECTOR, "input[name='_selected_action'][value='l1']"
        )
        l2_checkbox = self.selenium.find_element(
            By.CSS_SELECTOR, "input[name='_selected_action'][value='l2']"
        )

        # On first trigger, "focus next row" shortcut
        # focuses Select all objects checkbox
        self.perform_shortcut(Shortcuts.ChangeList.FOCUS_NEXT_ROW)
        self.assertEqual(self.selenium.switch_to.active_element, action_toggle_checkbox)

        self.perform_shortcut(Shortcuts.ChangeList.FOCUS_NEXT_ROW)
        self.assertEqual(self.selenium.switch_to.active_element, l1_checkbox)

        self.perform_shortcut(Shortcuts.ChangeList.FOCUS_NEXT_ROW)
        self.assertEqual(self.selenium.switch_to.active_element, l2_checkbox)

        # Rolls over from last row/checkbox to the first row/checkbox
        self.perform_shortcut(Shortcuts.ChangeList.FOCUS_NEXT_ROW)
        self.assertEqual(self.selenium.switch_to.active_element, action_toggle_checkbox)

    def test_shortcut_changelist_focus_previous_row(self):
        from selenium.webdriver.common.by import By

        Language.objects.create(iso="l1")
        Language.objects.create(iso="l2")

        self.selenium.get(
            self.live_server_url
            + reverse("test_admin_keyboard_shortcuts:admin_views_language_changelist")
        )

        l1_checkbox = self.selenium.find_element(
            By.CSS_SELECTOR, "input[name='_selected_action'][value='l1']"
        )
        l2_checkbox = self.selenium.find_element(
            By.CSS_SELECTOR, "input[name='_selected_action'][value='l2']"
        )

        # On first trigger, "focus previous row" shortcut focuses last row/checkbox
        self.perform_shortcut(Shortcuts.ChangeList.FOCUS_PREV_ROW)
        self.assertEqual(self.selenium.switch_to.active_element, l2_checkbox)

        self.perform_shortcut(Shortcuts.ChangeList.FOCUS_PREV_ROW)
        self.assertEqual(self.selenium.switch_to.active_element, l1_checkbox)

    def test_shortcut_changelist_toggle_row_selection(self):
        from selenium.webdriver.common.by import By

        Language.objects.create(iso="l1")
        Language.objects.create(iso="l2")

        self.selenium.get(
            self.live_server_url
            + reverse("test_admin_keyboard_shortcuts:admin_views_language_changelist")
        )

        action_toggle_checkbox = self.selenium.find_element(By.ID, "action-toggle")
        l1_checkbox = self.selenium.find_element(
            By.CSS_SELECTOR, "input[name='_selected_action'][value='l1']"
        )
        l2_checkbox = self.selenium.find_element(
            By.CSS_SELECTOR, "input[name='_selected_action'][value='l2']"
        )

        # Mark l2
        self.perform_shortcut(Shortcuts.ChangeList.FOCUS_PREV_ROW)
        self.assertEqual(self.selenium.switch_to.active_element, l2_checkbox)

        self.perform_shortcut(Shortcuts.ChangeList.TOGGLE_ROW_SELECTION)
        self.assertTrue(l2_checkbox.is_selected())

        # Unmark l2
        self.perform_shortcut(Shortcuts.ChangeList.TOGGLE_ROW_SELECTION)
        self.assertFalse(l2_checkbox.is_selected())

        # Mark action toggle checkbox
        self.perform_shortcut(Shortcuts.ChangeList.FOCUS_PREV_ROW)
        self.perform_shortcut(Shortcuts.ChangeList.FOCUS_PREV_ROW)
        self.assertEqual(self.selenium.switch_to.active_element, action_toggle_checkbox)

        self.perform_shortcut(Shortcuts.ChangeList.TOGGLE_ROW_SELECTION)
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

        actions_dropdown = self.selenium.find_element(
            By.CSS_SELECTOR, "select[name='action']"
        )

        self.perform_shortcut(Shortcuts.ChangeList.FOCUS_ACTIONS_DROPDOWN)
        self.assertEqual(self.selenium.switch_to.active_element, actions_dropdown)

    def test_shortcut_changeform_save(self):
        from selenium.webdriver.common.by import By

        self.selenium.get(
            self.live_server_url
            + reverse("test_admin_keyboard_shortcuts:admin_views_paper_add")
        )

        title_input = self.selenium.find_element(By.ID, "id_title")
        title_input.send_keys("p1")

        with self.wait_page_loaded():
            self.perform_shortcut(Shortcuts.ChangeForm.SAVE)
        self.assertEqual(Paper.objects.count(), 1)
        self.assertEqual(
            self.selenium.current_url,
            self.live_server_url
            + reverse("test_admin_keyboard_shortcuts:admin_views_paper_changelist"),
        )

    def test_shortcut_changeform_save_and_add_another(self):
        from selenium.webdriver.common.by import By

        self.selenium.get(
            self.live_server_url
            + reverse("test_admin_keyboard_shortcuts:admin_views_paper_add")
        )

        title_input = self.selenium.find_element(By.ID, "id_title")
        title_input.send_keys("p1")

        with self.wait_page_loaded():
            self.perform_shortcut(Shortcuts.ChangeForm.SAVE_AND_ADD_ANOTHER)
        self.assertEqual(Paper.objects.count(), 1)
        self.assertEqual(
            self.selenium.current_url,
            self.live_server_url
            + reverse("test_admin_keyboard_shortcuts:admin_views_paper_add"),
        )

    def test_shortcut_changeform_save_and_continue_editing(self):
        from selenium.webdriver.common.by import By

        self.selenium.get(
            self.live_server_url
            + reverse("test_admin_keyboard_shortcuts:admin_views_paper_add")
        )

        title_input = self.selenium.find_element(By.ID, "id_title")
        title_input.send_keys("t1")

        with self.wait_page_loaded():
            self.perform_shortcut(Shortcuts.ChangeForm.SAVE_AND_CONTINUE)
        self.assertEqual(Paper.objects.count(), 1)

        # check if on changeform page for that same saved object
        paper = Paper.objects.first()
        self.assertEqual(
            self.selenium.current_url,
            self.live_server_url
            + reverse(
                "test_admin_keyboard_shortcuts:admin_views_paper_change",
                args=(paper.pk,),
            ),
        )

    def test_shortcut_changeform_delete(self):
        paper = Paper.objects.create(title="p1")
        self.selenium.get(
            self.live_server_url
            + reverse(
                "test_admin_keyboard_shortcuts:admin_views_paper_change",
                args=(paper.pk,),
            )
        )

        with self.wait_page_loaded():
            self.perform_shortcut(Shortcuts.ChangeForm.DELETE)
        self.assertEqual(
            self.selenium.current_url,
            self.live_server_url
            + reverse(
                "test_admin_keyboard_shortcuts:admin_views_paper_delete",
                args=(paper.pk,),
            ),
        )

        # Cancel delete
        with self.wait_page_loaded():
            self.perform_shortcut(Shortcuts.DeleteConfirmation.CANCEL_DELETE)
        self.assertEqual(Paper.objects.count(), 1)
        self.assertEqual(
            self.selenium.current_url,
            self.live_server_url
            + reverse(
                "test_admin_keyboard_shortcuts:admin_views_paper_change",
                args=(paper.pk,),
            ),
        )

        with self.wait_page_loaded():
            self.perform_shortcut(Shortcuts.ChangeForm.DELETE)
        # Confirm delete
        self.perform_shortcut(Shortcuts.DeleteConfirmation.CONFIRM_DELETE)
        self.assertEqual(Paper.objects.count(), 0)
