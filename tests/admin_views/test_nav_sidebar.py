from django.contrib import admin
from django.contrib.admin.tests import AdminSeleniumTestCase
from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import path, reverse

from .models import Héllo


class AdminSiteWithSidebar(admin.AdminSite):
    pass


class AdminSiteWithoutSidebar(admin.AdminSite):
    enable_nav_sidebar = False


site_with_sidebar = AdminSiteWithSidebar(name="test_with_sidebar")
site_without_sidebar = AdminSiteWithoutSidebar(name="test_without_sidebar")

site_with_sidebar.register(User)
site_with_sidebar.register(Héllo)

urlpatterns = [
    path("test_sidebar/admin/", site_with_sidebar.urls),
    path("test_wihout_sidebar/admin/", site_without_sidebar.urls),
]


@override_settings(ROOT_URLCONF="admin_views.test_nav_sidebar")
class AdminSidebarTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            username="super",
            password="secret",
            email="super@example.com",
        )

    def setUp(self):
        self.client.force_login(self.superuser)

    def test_sidebar_not_on_index(self):
        response = self.client.get(reverse("test_with_sidebar:index"))
        self.assertContains(response, '<div class="main" id="main">')
        self.assertNotContains(response, '<nav class="sticky" id="nav-sidebar">')

    def test_sidebar_disabled(self):
        response = self.client.get(reverse("test_without_sidebar:index"))
        self.assertNotContains(response, '<nav class="sticky" id="nav-sidebar">')

    def test_sidebar_unauthenticated(self):
        self.client.logout()
        response = self.client.get(reverse("test_with_sidebar:login"))
        self.assertNotContains(response, '<nav class="sticky" id="nav-sidebar">')

    def test_sidebar_aria_current_page(self):
        url = reverse("test_with_sidebar:auth_user_changelist")
        response = self.client.get(url)
        self.assertContains(response, '<nav class="sticky" id="nav-sidebar">')
        self.assertContains(
            response, '<a href="%s" aria-current="page">Users</a>' % url
        )

    @override_settings(
        TEMPLATES=[
            {
                "BACKEND": "django.template.backends.django.DjangoTemplates",
                "DIRS": [],
                "APP_DIRS": True,
                "OPTIONS": {
                    "context_processors": [
                        "django.contrib.auth.context_processors.auth",
                        "django.contrib.messages.context_processors.messages",
                    ],
                },
            }
        ]
    )
    def test_sidebar_aria_current_page_missing_without_request_context_processor(self):
        url = reverse("test_with_sidebar:auth_user_changelist")
        response = self.client.get(url)
        self.assertContains(response, '<nav class="sticky" id="nav-sidebar">')
        # Does not include aria-current attribute.
        self.assertContains(response, '<a href="%s">Users</a>' % url)
        self.assertNotContains(response, "aria-current")

    @override_settings(DEBUG=True)
    def test_included_app_list_template_context_fully_set(self):
        # All context variables should be set when rendering the sidebar.
        url = reverse("test_with_sidebar:auth_user_changelist")
        with self.assertNoLogs("django.template", "DEBUG"):
            self.client.get(url)

    def test_sidebar_model_name_non_ascii(self):
        url = reverse("test_with_sidebar:admin_views_héllo_changelist")
        response = self.client.get(url)
        self.assertContains(
            response, '<div class="app-admin_views module current-app">'
        )
        self.assertContains(response, '<tr class="model-héllo current-model">')
        self.assertContains(
            response,
            '<th scope="row">'
            '<a href="/test_sidebar/admin/admin_views/h%C3%A9llo/" aria-current="page">'
            "Héllos</a></th>",
        )


@override_settings(ROOT_URLCONF="admin_views.test_nav_sidebar")
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
            login_url=reverse("test_with_sidebar:index"),
        )
        self.selenium.execute_script(
            "localStorage.removeItem('django.admin.navSidebarIsOpen')"
        )

    def test_sidebar_starts_open(self):
        from selenium.webdriver.common.by import By

        self.selenium.get(
            self.live_server_url + reverse("test_with_sidebar:auth_user_changelist")
        )
        main_element = self.selenium.find_element(By.CSS_SELECTOR, "#main")
        self.assertIn("shifted", main_element.get_attribute("class").split())

    def test_sidebar_can_be_closed(self):
        from selenium.webdriver.common.by import By

        self.selenium.get(
            self.live_server_url + reverse("test_with_sidebar:auth_user_changelist")
        )
        toggle_button = self.selenium.find_element(
            By.CSS_SELECTOR, "#toggle-nav-sidebar"
        )
        self.assertEqual(toggle_button.tag_name, "button")
        self.assertEqual(toggle_button.get_attribute("aria-label"), "Toggle navigation")
        for link in self.selenium.find_elements(By.CSS_SELECTOR, "#nav-sidebar a"):
            self.assertEqual(link.get_attribute("tabIndex"), "0")
        filter_input = self.selenium.find_element(By.CSS_SELECTOR, "#nav-filter")
        self.assertEqual(filter_input.get_attribute("tabIndex"), "0")
        toggle_button.click()
        # Hidden sidebar is not reachable via keyboard navigation.
        for link in self.selenium.find_elements(By.CSS_SELECTOR, "#nav-sidebar a"):
            self.assertEqual(link.get_attribute("tabIndex"), "-1")
        filter_input = self.selenium.find_element(By.CSS_SELECTOR, "#nav-filter")
        self.assertEqual(filter_input.get_attribute("tabIndex"), "-1")
        main_element = self.selenium.find_element(By.CSS_SELECTOR, "#main")
        self.assertNotIn("shifted", main_element.get_attribute("class").split())

    def test_sidebar_state_persists(self):
        from selenium.webdriver.common.by import By

        self.selenium.get(
            self.live_server_url + reverse("test_with_sidebar:auth_user_changelist")
        )
        self.assertIsNone(
            self.selenium.execute_script(
                "return localStorage.getItem('django.admin.navSidebarIsOpen')"
            )
        )
        toggle_button = self.selenium.find_element(
            By.CSS_SELECTOR, "#toggle-nav-sidebar"
        )
        toggle_button.click()
        self.assertEqual(
            self.selenium.execute_script(
                "return localStorage.getItem('django.admin.navSidebarIsOpen')"
            ),
            "false",
        )
        self.selenium.get(
            self.live_server_url + reverse("test_with_sidebar:auth_user_changelist")
        )
        main_element = self.selenium.find_element(By.CSS_SELECTOR, "#main")
        self.assertNotIn("shifted", main_element.get_attribute("class").split())

        toggle_button = self.selenium.find_element(
            By.CSS_SELECTOR, "#toggle-nav-sidebar"
        )
        # Hidden sidebar is not reachable via keyboard navigation.
        for link in self.selenium.find_elements(By.CSS_SELECTOR, "#nav-sidebar a"):
            self.assertEqual(link.get_attribute("tabIndex"), "-1")
        filter_input = self.selenium.find_element(By.CSS_SELECTOR, "#nav-filter")
        self.assertEqual(filter_input.get_attribute("tabIndex"), "-1")
        toggle_button.click()
        for link in self.selenium.find_elements(By.CSS_SELECTOR, "#nav-sidebar a"):
            self.assertEqual(link.get_attribute("tabIndex"), "0")
        filter_input = self.selenium.find_element(By.CSS_SELECTOR, "#nav-filter")
        self.assertEqual(filter_input.get_attribute("tabIndex"), "0")
        self.assertEqual(
            self.selenium.execute_script(
                "return localStorage.getItem('django.admin.navSidebarIsOpen')"
            ),
            "true",
        )
        self.selenium.get(
            self.live_server_url + reverse("test_with_sidebar:auth_user_changelist")
        )
        main_element = self.selenium.find_element(By.CSS_SELECTOR, "#main")
        self.assertIn("shifted", main_element.get_attribute("class").split())

    def test_sidebar_filter_persists(self):
        from selenium.webdriver.common.by import By

        self.selenium.get(
            self.live_server_url + reverse("test_with_sidebar:auth_user_changelist")
        )
        filter_value_script = (
            "return sessionStorage.getItem('django.admin.navSidebarFilterValue')"
        )
        self.assertIsNone(self.selenium.execute_script(filter_value_script))
        filter_input = self.selenium.find_element(By.CSS_SELECTOR, "#nav-filter")
        filter_input.send_keys("users")
        self.assertEqual(self.selenium.execute_script(filter_value_script), "users")
