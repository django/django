from django.contrib.admin.tests import AdminSeleniumTestCase
from django.contrib.auth.models import User
from django.test import override_settings
from django.urls import reverse

from .models import Bookmark


@override_settings(ROOT_URLCONF='admin_views.urls')
class SeleniumTests(AdminSeleniumTestCase):
    available_apps = ['admin_views'] + AdminSeleniumTestCase.available_apps

    def setUp(self):
        self.BOOKMARK_ADD_URL = reverse('admin:admin_views_bookmark_add')
        self.superuser = User.objects.create_superuser(
            username='super', password='secret', email='super@example.com',
        )
        self.admin_login(
            username='super', password='secret', login_url=reverse('admin:index'),
        )

    def _fill_form_and_get_save_button(self):
        from selenium.webdriver.common.by import By

        self.selenium.get(self.live_server_url + self.BOOKMARK_ADD_URL)
        input_ = self.selenium.find_element(By.ID, 'id_name')
        input_.send_keys('Bookmark name')

        return self.selenium.find_element(By.CSS_SELECTOR, 'input[name=_save]')

    def test_save_buttons_are_disabled_after_click_submit(self):
        from selenium.webdriver.common.by import By

        save_button = self._fill_form_and_get_save_button()
        self.selenium.execute_script("arguments[0].click(); window.stop();", save_button)
        submit_buttons = self.selenium.find_elements(By.CSS_SELECTOR, 'input[type=submit]')
        # Submits buttons are DISABLED
        for button in submit_buttons:
            self.assertFalse(button.is_enabled())
        self.assertEqual(Bookmark.objects.count(), 0)

    def test_submit_and_go_back(self):
        from selenium.webdriver.common.by import By

        save_button = self._fill_form_and_get_save_button()
        save_button.click()
        self.selenium.back()
        submit_buttons = self.selenium.find_elements(By.CSS_SELECTOR, 'input[type=submit]')
        # Submits buttons are ENABLED
        for button in submit_buttons:
            self.assertTrue(button.is_enabled())
        self.assertEqual(Bookmark.objects.count(), 1)

    def test_double_submit_click_wont_create_multiple_objects(self):
        from selenium.webdriver.common.action_chains import ActionChains

        save_button = self._fill_form_and_get_save_button()

        with self.wait_page_loaded():
            ActionChains(self.selenium).double_click(save_button).perform()

        self.assertEqual(Bookmark.objects.count(), 1)
