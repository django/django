from django.contrib.admin.tests import AdminPlaywrightTestCase
from django.contrib.auth.models import User
from django.test import override_settings
from django.test.playwright import screenshot_cases
from django.urls import reverse


@override_settings(ROOT_URLCONF="auth_tests.urls_admin")
class PlaywrightAuthTests(AdminPlaywrightTestCase):
    available_apps = AdminPlaywrightTestCase.available_apps

    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username="super",
            password="secret",
            email="super@example.com",
        )

    def test_add_new_user(self):
        """A user with no password can be added.

        Enabling/disabling the usable password field shows/hides the password
        fields when adding a user.
        """
        user_add_url = reverse("auth_test_admin:auth_user_add")
        self.admin_login(username="super", password="secret")
        self.page.goto(self.live_server_url + user_add_url)

        pw_switch_on = self.page.locator('input[name="usable_password"][value="true"]')
        pw_switch_off = self.page.locator(
            'input[name="usable_password"][value="false"]'
        )
        password1 = self.page.locator('input[name="password1"]')
        password2 = self.page.locator('input[name="password2"]')

        # Default is to set a password on user creation.
        self.expect(pw_switch_on).to_be_checked()
        self.expect(pw_switch_off).not_to_be_checked()

        # The password fields are visible.
        self.expect(password1).to_be_visible()
        self.expect(password2).to_be_visible()

        # Click to disable password-based authentication.
        pw_switch_off.click()

        # Radio buttons are updated accordingly.
        self.expect(pw_switch_on).not_to_be_checked()
        self.expect(pw_switch_off).to_be_checked()

        # The password fields are hidden.
        self.expect(password1).to_be_hidden()
        self.expect(password2).to_be_hidden()

        # The warning message should not be shown.
        self.expect(self.page.locator("#id_unusable_warning")).to_have_count(0)

    def test_change_password_for_existing_user(self):
        """A user can have their password changed or unset.

        Enabling/disabling the usable password field shows/hides the password
        fields and the warning about password lost.
        """
        user = User.objects.create_user(
            username="ada", password="charles", email="ada@example.com"
        )
        user_url = reverse("auth_test_admin:auth_user_password_change", args=(user.pk,))
        self.admin_login(username="super", password="secret")
        self.page.goto(self.live_server_url + user_url)

        pw_switch_on = self.page.locator('input[name="usable_password"][value="true"]')
        pw_switch_off = self.page.locator(
            'input[name="usable_password"][value="false"]'
        )
        password1 = self.page.locator('input[name="password1"]')
        password2 = self.page.locator('input[name="password2"]')
        submit_set = self.page.locator('input[type="submit"].set-password')
        submit_unset = self.page.locator('input[type="submit"].unset-password')

        # By default password-based authentication is enabled.
        self.expect(pw_switch_on).to_be_checked()
        self.expect(pw_switch_off).not_to_be_checked()

        # The password fields are visible.
        self.expect(password1).to_be_visible()
        self.expect(password2).to_be_visible()

        # Only the set password submit button is visible.
        self.expect(submit_set).to_be_visible()
        self.expect(submit_unset).to_be_hidden()

        # Click to disable password-based authentication.
        pw_switch_off.click()

        # Radio buttons are updated accordingly.
        self.expect(pw_switch_on).not_to_be_checked()
        self.expect(pw_switch_off).to_be_checked()

        # The password fields are hidden.
        self.expect(password1).to_be_hidden()
        self.expect(password2).to_be_hidden()

        # Only the unset password submit button is visible.
        self.expect(submit_unset).to_be_visible()
        self.expect(submit_set).to_be_hidden()

        # The warning about password being lost is shown.
        warning = self.page.locator("#id_unusable_warning")
        self.expect(warning).to_be_visible()

        # Click to enable password-based authentication.
        pw_switch_on.click()

        # The warning disappears.
        self.expect(warning).to_be_hidden()

        # The password fields are shown.
        self.expect(password1).to_be_visible()
        self.expect(password2).to_be_visible()

        # Only the set password submit button is visible.
        self.expect(submit_set).to_be_visible()
        self.expect(submit_unset).to_be_hidden()

    @screenshot_cases(["desktop_size", "mobile_size", "rtl", "dark", "high_contrast"])
    def test_fieldset_legend_wide_alignment(self):
        user_add_url = reverse("auth_test_admin:auth_user_add")
        self.admin_login(username="super", password="secret")
        self.page.goto(self.live_server_url + user_add_url)

        # The fieldset legend is aligned with other fields.
        self.take_screenshot("fieldset_legend_wide")
