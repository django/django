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
        save_and_add_another = self.selenium.find_element(By.CSS_SELECTOR, 'input[name="_addanother"]')
        save_and_continue_editing = self.selenium.find_element(By.CSS_SELECTOR, 'input[name="_continue"]')
        self.assertFalse(save_button.is_enabled())
        self.assertFalse(save_and_add_another.is_enabled())
        self.assertFalse(save_and_continue_editing.is_enabled())
        self.assertEqual(Bookmark.objects.count(), 0)

    def test_double_submit_click_wont_create_multiple_objects(self):
        from selenium.webdriver.common.action_chains import ActionChains
        from selenium.webdriver.common.by import By

        self.selenium.get(self.live_server_url + reverse('admin:admin_views_bookmark_add'))
        input_ = self.selenium.find_element(By.ID, 'id_name')
        input_.send_keys('Bookmark name')
        save_button = self.selenium.find_element(By.CSS_SELECTOR, 'input[name=_save]')
        ActionChains(self.selenium).double_click(save_button).perform()
        self.assertEqual(Bookmark.objects.count(), 1)


@override_settings(ROOT_URLCONF='admin_views.urls')
class SeleniumTestsWithJavascriptDisabled(AdminSeleniumTestCase):
    """
    Without loading `change_form.js` we don't prevent multiple requests
    """
    available_apps = ['admin_views'] + AdminSeleniumTestCase.available_apps

    @classmethod
    def setUpClass(cls):
        super(SeleniumTestCase, cls).setUpClass()
        options = cls.create_options()
        if cls.browser == "chrome":
            options.add_experimental_option("prefs", {'profile.managed_default_content_settings.javascript': 2})
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
        """
        Objects duplicated caused by faster clicks
        """
        from selenium.webdriver.common.action_chains import ActionChains
        from selenium.webdriver.common.by import By

        self.selenium.get(self.live_server_url + reverse('admin:admin_views_bookmark_add'))
        input_ = self.selenium.find_element(By.ID, 'id_name')
        input_.send_keys('Bookmark name')
        save_button = self.selenium.find_element(By.CSS_SELECTOR, 'input[name=_save]')
        ActionChains(self.selenium).double_click(save_button).perform()
        self.assertEqual(Bookmark.objects.count(), 2)
