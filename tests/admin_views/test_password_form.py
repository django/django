from django.contrib.admin.tests import AdminSeleniumTestCase
from django.contrib.auth.models import User
from django.test import override_settings
from django.urls import reverse


@override_settings(ROOT_URLCONF="auth_tests.urls_admin")
class SeleniumAuthTests(AdminSeleniumTestCase):
    available_apps = AdminSeleniumTestCase.available_apps

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
        from selenium.common import NoSuchElementException
        from selenium.webdriver.common.by import By

        user_add_url = reverse("auth_test_admin:auth_user_add")
        self.admin_login(username="super", password="secret")
        self.selenium.get(self.live_server_url + user_add_url)

        pw_switch_on = self.selenium.find_element(
            By.CSS_SELECTOR, 'input[name="usable_password"][value="true"]'
        )
        pw_switch_off = self.selenium.find_element(
            By.CSS_SELECTOR, 'input[name="usable_password"][value="false"]'
        )
        password1 = self.selenium.find_element(
            By.CSS_SELECTOR, 'input[name="password1"]'
        )
        password2 = self.selenium.find_element(
            By.CSS_SELECTOR, 'input[name="password2"]'
        )

        # Default is to set a password on user creation.
        self.assertIs(pw_switch_on.is_selected(), True)
        self.assertIs(pw_switch_off.is_selected(), False)

        # The password fields are visible.
        self.assertIs(password1.is_displayed(), True)
        self.assertIs(password2.is_displayed(), True)

        # Click to disable password-based authentication.
        pw_switch_off.click()

        # Radio buttons are updated accordingly.
        self.assertIs(pw_switch_on.is_selected(), False)
        self.assertIs(pw_switch_off.is_selected(), True)

        # The password fields are hidden.
        self.assertIs(password1.is_displayed(), False)
        self.assertIs(password2.is_displayed(), False)

        # The warning message should not be shown.
        with self.assertRaises(NoSuchElementException):
            self.selenium.find_element(By.ID, "id_unusable_warning")

    def test_change_password_for_existing_user(self):
        """A user can have their password changed or unset.

        Enabling/disabling the usable password field shows/hides the password
        fields and the warning about password lost.
        """
        from selenium.webdriver.common.by import By

        user = User.objects.create_user(
            username="ada", password="charles", email="ada@example.com"
        )
        user_url = reverse("auth_test_admin:auth_user_password_change", args=(user.pk,))
        self.admin_login(username="super", password="secret")
        self.selenium.get(self.live_server_url + user_url)

        pw_switch_on = self.selenium.find_element(
            By.CSS_SELECTOR, 'input[name="usable_password"][value="true"]'
        )
        pw_switch_off = self.selenium.find_element(
            By.CSS_SELECTOR, 'input[name="usable_password"][value="false"]'
        )
        password1 = self.selenium.find_element(
            By.CSS_SELECTOR, 'input[name="password1"]'
        )
        password2 = self.selenium.find_element(
            By.CSS_SELECTOR, 'input[name="password2"]'
        )
        submit_set = self.selenium.find_element(
            By.CSS_SELECTOR, 'input[type="submit"].set-password'
        )
        submit_unset = self.selenium.find_element(
            By.CSS_SELECTOR, 'input[type="submit"].unset-password'
        )

        # By default password-based authentication is enabled.
        self.assertIs(pw_switch_on.is_selected(), True)
        self.assertIs(pw_switch_off.is_selected(), False)

        # The password fields are visible.
        self.assertIs(password1.is_displayed(), True)
        self.assertIs(password2.is_displayed(), True)

        # Only the set password submit button is visible.
        self.assertIs(submit_set.is_displayed(), True)
        self.assertIs(submit_unset.is_displayed(), False)

        # Click to disable password-based authentication.
        pw_switch_off.click()

        # Radio buttons are updated accordingly.
        self.assertIs(pw_switch_on.is_selected(), False)
        self.assertIs(pw_switch_off.is_selected(), True)

        # The password fields are hidden.
        self.assertIs(password1.is_displayed(), False)
        self.assertIs(password2.is_displayed(), False)

        # Only the unset password submit button is visible.
        self.assertIs(submit_unset.is_displayed(), True)
        self.assertIs(submit_set.is_displayed(), False)

        # The warning about password being lost is shown.
        warning = self.selenium.find_element(By.ID, "id_unusable_warning")
        self.assertIs(warning.is_displayed(), True)

        # Click to enable password-based authentication.
        pw_switch_on.click()

        # The warning disappears.
        self.assertIs(warning.is_displayed(), False)

        # The password fields are shown.
        self.assertIs(password1.is_displayed(), True)
        self.assertIs(password2.is_displayed(), True)

        # Only the set password submit button is visible.
        self.assertIs(submit_set.is_displayed(), True)
        self.assertIs(submit_unset.is_displayed(), False)
