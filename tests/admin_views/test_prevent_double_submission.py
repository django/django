from django.contrib.admin.tests import AdminSeleniumTestCase
from django.contrib.auth.models import User
from django.test import override_settings
from django.test.selenium import SeleniumTestCase
from django.urls import reverse

from .models import Bookmark


@override_settings(ROOT_URLCONF='admin_views.urls')
class SeleniumTests(AdminSeleniumTestCase):
    available_apps = ['admin_views'] + AdminSeleniumTestCase.available_apps

    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username='super', password='secret', email='super@example.com',
        )
        self.admin_login(
            username='super', password='secret', login_url=reverse('admin:index'),
        )

    def test_save_buttons_are_disabled_after_click_submit(self):
        from selenium.webdriver.common.by import By

        self.selenium.get(self.live_server_url + reverse('admin:admin_views_bookmark_add'))
        input_ = self.selenium.find_element(By.ID, 'id_name')
        input_.send_keys('Bookmark name')
        save_button = self.selenium.find_element(By.CSS_SELECTOR, 'input[name=_save]')
        self.selenium.execute_script("arguments[0].click(); window.stop();", save_button)
        submit_buttons = self.selenium.find_elements(By.CSS_SELECTOR, 'input[type=submit]')
        # All submits buttons are DISABLED
        for button in submit_buttons:
            self.assertFalse(button.is_enabled())
        self.assertEqual(Bookmark.objects.count(), 0)

    def test_submit_and_go_back(self):
        from selenium.webdriver.common.by import By

        self.selenium.get(self.live_server_url + reverse('admin:admin_views_bookmark_add'))
        input_ = self.selenium.find_element(By.ID, 'id_name')
        input_.send_keys('Bookmark name')
        save_button = self.selenium.find_element(By.CSS_SELECTOR, 'input[name=_save]')
        save_button.click()
        self.selenium.back()
        submit_buttons = self.selenium.find_elements(By.CSS_SELECTOR, 'input[type=submit]')
        # All submits buttons are ENABLED
        for button in submit_buttons:
            self.assertTrue(button.is_enabled())
        self.assertEqual(Bookmark.objects.count(), 1)

    def test_double_submit_click_wont_create_multiple_objects(self):
        from selenium.webdriver.common.action_chains import ActionChains
        from selenium.webdriver.common.by import By

        self.selenium.get(self.live_server_url + reverse('admin:admin_views_bookmark_add'))
        input_ = self.selenium.find_element(By.ID, 'id_name')
        input_.send_keys('Bookmark name')
        save_button = self.selenium.find_element(By.CSS_SELECTOR, 'input[name=_save]')

        with self.wait_page_loaded():
            ActionChains(self.selenium).double_click(save_button).perform()

        self.assertEqual(Bookmark.objects.count(), 1)


@override_settings(ROOT_URLCONF='admin_views.urls')
class SeleniumTestsWithJavascriptDisabled(AdminSeleniumTestCase):
    """
    If we don't load javascript, we don't prevent multiple requests
    """

    available_apps = ['admin_views'] + AdminSeleniumTestCase.available_apps

    @classmethod
    def setUpClass(cls):
        super(SeleniumTestCase, cls).setUpClass()
        options = cls.create_options()
        if cls.browser == 'chrome':
            options.add_experimental_option('prefs', {'profile.managed_default_content_settings.javascript': 2})
        elif cls.browser == 'firefox':
            options.set_preference('javascript.enabled', False)
        cls.selenium = cls.import_webdriver(cls.browser)(options=options)
        cls.selenium.implicitly_wait(cls.implicit_wait)

    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username='super', password='secret', email='super@example.com',
        )
        self.admin_login(
            username='super', password='secret', login_url=reverse('admin:index'),
        )

    def test_double_submit_click_will_create_multiple_objects(self):
        from selenium.webdriver.common.action_chains import ActionChains
        from selenium.webdriver.common.by import By

        self.selenium.get(self.live_server_url + reverse('admin:admin_views_bookmark_add'))
        input_ = self.selenium.find_element(By.ID, 'id_name')
        input_.send_keys('Bookmark name')
        save_button = self.selenium.find_element(By.CSS_SELECTOR, 'input[name=_save]')

        with self.wait_page_loaded():
            ActionChains(self.selenium).double_click(save_button).perform()

        if self.browser == 'chrome':
            self.assertEqual(Bookmark.objects.count(), 2)
        elif self.browser == 'firefox':  # no duplicated, it works without js!
            self.assertEqual(Bookmark.objects.count(), 1)
