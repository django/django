from django.contrib import admin
from django.contrib.admin.tests import AdminSeleniumTestCase
from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import path, reverse


class AdminSiteWithSidebar(admin.AdminSite):
    pass


class AdminSiteWithoutSidebar(admin.AdminSite):
    enable_nav_sidebar = False


site_with_sidebar = AdminSiteWithSidebar(name='test_with_sidebar')
site_without_sidebar = AdminSiteWithoutSidebar(name='test_without_sidebar')

site_with_sidebar.register(User)

urlpatterns = [
    path('test_sidebar/admin/', site_with_sidebar.urls),
    path('test_wihout_sidebar/admin/', site_without_sidebar.urls),
]


@override_settings(ROOT_URLCONF='admin_views.test_nav_sidebar')
class AdminSidebarTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            username='super',
            password='secret',
            email='super@example.com',
        )

    def setUp(self):
        self.client.force_login(self.superuser)

    def test_sidebar_not_on_index(self):
        response = self.client.get(reverse('test_with_sidebar:index'))
        self.assertNotContains(response, '<nav class="sticky" id="nav-sidebar">')

    def test_sidebar_disabled(self):
        response = self.client.get(reverse('test_without_sidebar:index'))
        self.assertNotContains(response, '<nav class="sticky" id="nav-sidebar">')

    def test_sidebar_unauthenticated(self):
        self.client.logout()
        response = self.client.get(reverse('test_with_sidebar:login'))
        self.assertNotContains(response, '<nav class="sticky" id="nav-sidebar">')

    def test_sidebar_aria_current_page(self):
        url = reverse('test_with_sidebar:auth_user_changelist')
        response = self.client.get(url)
        self.assertContains(response, '<nav class="sticky" id="nav-sidebar">')
        self.assertContains(response, '<a href="%s" aria-current="page">Users</a>' % url)

    @override_settings(
        TEMPLATES=[{
            'BACKEND': 'django.template.backends.django.DjangoTemplates',
            'DIRS': [],
            'APP_DIRS': True,
            'OPTIONS': {
                'context_processors': [
                    'django.contrib.auth.context_processors.auth',
                    'django.contrib.messages.context_processors.messages',
                ],
            },
        }]
    )
    def test_sidebar_aria_current_page_missing_without_request_context_processor(self):
        url = reverse('test_with_sidebar:auth_user_changelist')
        response = self.client.get(url)
        self.assertContains(response, '<nav class="sticky" id="nav-sidebar">')
        # Does not include aria-current attribute.
        self.assertContains(response, '<a href="%s">Users</a>' % url)
        self.assertNotContains(response, 'aria-current')


@override_settings(ROOT_URLCONF='admin_views.test_nav_sidebar')
class SeleniumTests(AdminSeleniumTestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username='super',
            password='secret',
            email='super@example.com',
        )
        self.admin_login(username='super', password='secret', login_url=reverse('test_with_sidebar:index'))
        self.selenium.execute_script("localStorage.removeItem('django.admin.navSidebarIsOpen')")

    def test_sidebar_starts_open(self):
        self.selenium.get(self.live_server_url + reverse('test_with_sidebar:auth_user_changelist'))
        main_element = self.selenium.find_element_by_css_selector('#main')
        self.assertIn('shifted', main_element.get_attribute('class').split())

    def test_sidebar_can_be_closed(self):
        self.selenium.get(self.live_server_url + reverse('test_with_sidebar:auth_user_changelist'))
        toggle_button = self.selenium.find_element_by_css_selector('#toggle-nav-sidebar')
        self.assertEqual(toggle_button.tag_name, 'button')
        self.assertEqual(toggle_button.get_attribute('aria-label'), 'Toggle navigation')
        for link in self.selenium.find_elements_by_css_selector('#nav-sidebar a'):
            self.assertEqual(link.get_attribute('tabIndex'), '0')
        toggle_button.click()
        # Hidden sidebar is not reachable via keyboard navigation.
        for link in self.selenium.find_elements_by_css_selector('#nav-sidebar a'):
            self.assertEqual(link.get_attribute('tabIndex'), '-1')
        main_element = self.selenium.find_element_by_css_selector('#main')
        self.assertNotIn('shifted', main_element.get_attribute('class').split())

    def test_sidebar_state_persists(self):
        self.selenium.get(self.live_server_url + reverse('test_with_sidebar:auth_user_changelist'))
        self.assertIsNone(self.selenium.execute_script("return localStorage.getItem('django.admin.navSidebarIsOpen')"))
        toggle_button = self.selenium.find_element_by_css_selector('#toggle-nav-sidebar')
        toggle_button.click()
        self.assertEqual(
            self.selenium.execute_script("return localStorage.getItem('django.admin.navSidebarIsOpen')"),
            'false',
        )
        self.selenium.get(self.live_server_url + reverse('test_with_sidebar:auth_user_changelist'))
        main_element = self.selenium.find_element_by_css_selector('#main')
        self.assertNotIn('shifted', main_element.get_attribute('class').split())

        toggle_button = self.selenium.find_element_by_css_selector('#toggle-nav-sidebar')
        # Hidden sidebar is not reachable via keyboard navigation.
        for link in self.selenium.find_elements_by_css_selector('#nav-sidebar a'):
            self.assertEqual(link.get_attribute('tabIndex'), '-1')
        toggle_button.click()
        for link in self.selenium.find_elements_by_css_selector('#nav-sidebar a'):
            self.assertEqual(link.get_attribute('tabIndex'), '0')
        self.assertEqual(
            self.selenium.execute_script("return localStorage.getItem('django.admin.navSidebarIsOpen')"),
            'true',
        )
        self.selenium.get(self.live_server_url + reverse('test_with_sidebar:auth_user_changelist'))
        main_element = self.selenium.find_element_by_css_selector('#main')
        self.assertIn('shifted', main_element.get_attribute('class').split())
