from django.contrib.admin.tests import AdminSeleniumTestCase
from django.contrib.auth.models import User
from django.test import override_settings
from django.urls import reverse

from .models import Bookmark


@override_settings(ROOT_URLCONF="admin_views.urls")
class SeleniumTests(AdminSeleniumTestCase):
    available_apps = ["admin_views"] + AdminSeleniumTestCase.available_apps

    def setUp(self):
        self.BOOKMARK_ADD_URL = reverse("admin:admin_views_bookmark_add")
        self.BOOKMARK_LIST_URL = reverse("admin:admin_views_bookmark_changelist")
        self.ALERT_MESSAGE = (
            "You have already submitted this form. "
            "Are you sure you want to submit it again?"
        )
        self.superuser = User.objects.create_superuser(
            username="super",
            password="secret",
            email="super@example.com",
        )
        self.admin_login(
            username="super",
            password="secret",
            login_url=reverse("admin:index"),
        )

    def test_single_submit_click_is_success_without_alert(self):
        from selenium.webdriver.common.by import By

        self.selenium.get(self.live_server_url + self.BOOKMARK_ADD_URL)
        input_ = self.selenium.find_element(By.ID, "id_name")
        input_.send_keys("Bookmark name")
        save_button = self.selenium.find_element(By.CSS_SELECTOR, "input[name=_save]")
        save_button.click()
        self.assertEqual(
            self.selenium.current_url, self.live_server_url + self.BOOKMARK_LIST_URL
        )
        self.assertEqual(Bookmark.objects.count(), 1)

    def _double_click_submit(self):
        from selenium.webdriver.common.action_chains import ActionChains
        from selenium.webdriver.common.by import By

        self.selenium.get(self.live_server_url + self.BOOKMARK_ADD_URL)
        input_ = self.selenium.find_element(By.ID, "id_name")
        input_.send_keys("Bookmark name")
        save_button = self.selenium.find_element(By.CSS_SELECTOR, "input[name=_save]")
        ActionChains(self.selenium).double_click(save_button).perform()

    def test_confirm_double_submit_alert(self):
        self._double_click_submit()
        alert = self.selenium.switch_to.alert
        self.assertEqual(alert.text, self.ALERT_MESSAGE)
        alert.accept()
        self.wait_page_ready()

        OBJECTS_CREATED = 1
        if self.browser == "chrome":
            OBJECTS_CREATED = 2
        elif self.browser == "firefox":
            pass

        self.assertEqual(Bookmark.objects.count(), OBJECTS_CREATED)

    def test_cancel_double_submit_alert(self):
        self._double_click_submit()
        alert = self.selenium.switch_to.alert
        self.assertEqual(alert.text, self.ALERT_MESSAGE)
        alert.dismiss()
        self.wait_page_ready()
        self.assertEqual(Bookmark.objects.count(), 1)

    def test_submit_and_go_back(self):
        from selenium.webdriver.common.by import By

        self.selenium.get(self.live_server_url + self.BOOKMARK_ADD_URL)
        input_ = self.selenium.find_element(By.ID, "id_name")
        input_.send_keys("Bookmark name")

        # submit by first time
        save_button = self.selenium.find_element(By.CSS_SELECTOR, "input[name=_save]")
        save_button.click()
        self.assertEqual(Bookmark.objects.count(), 1)
        self.assertEqual(
            self.selenium.current_url, self.live_server_url + self.BOOKMARK_LIST_URL
        )

        # go back
        self.selenium.back()
        self.assertEqual(
            self.selenium.current_url, self.live_server_url + self.BOOKMARK_ADD_URL
        )

        # submit again
        input_ = self.selenium.find_element(By.ID, "id_name")
        input_.clear()
        input_.send_keys("Other bookmark name")
        save_button = self.selenium.find_element(By.CSS_SELECTOR, "input[name=_save]")
        save_button.click()

        self.assertEqual(Bookmark.objects.count(), 2)
