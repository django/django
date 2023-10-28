from django.contrib.admin.tests import AdminSeleniumTestCase
from django.contrib.auth.models import User
from django.test import override_settings
from django.urls import reverse


@override_settings(ROOT_URLCONF="admin_views.urls")
class SeleniumTests(AdminSeleniumTestCase):
    available_apps = ["admin_views"] + AdminSeleniumTestCase.available_apps

    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username="super", password="secret", email="super@example.com"
        )
        self.admin_login(
            username="super", password="secret", login_url=reverse("admin:index")
        )

    def test_related_object_link_images_attributes(self):
        from selenium.webdriver.common.by import By

        album_add_url = reverse("admin:admin_views_album_add")
        self.selenium.get(self.live_server_url + album_add_url)

        tests = [
            "add_id_owner",
            "change_id_owner",
            "delete_id_owner",
            "view_id_owner",
        ]
        for link_id in tests:
            with self.subTest(link_id):
                link_image = self.selenium.find_element(
                    By.XPATH, f'//*[@id="{link_id}"]/img'
                )
                self.assertEqual(link_image.get_attribute("alt"), "")
                self.assertEqual(link_image.get_attribute("width"), "20")
                self.assertEqual(link_image.get_attribute("height"), "20")

    def test_related_object_lookup_link_initial_state(self):
        from selenium.webdriver.common.by import By

        album_add_url = reverse("admin:admin_views_album_add")
        self.selenium.get(self.live_server_url + album_add_url)

        tests = [
            "change_id_owner",
            "delete_id_owner",
            "view_id_owner",
        ]
        for link_id in tests:
            with self.subTest(link_id):
                link = self.selenium.find_element(By.XPATH, f'//*[@id="{link_id}"]')
                self.assertEqual(link.get_attribute("aria-disabled"), "true")

    def test_related_object_lookup_link_enabled(self):
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.select import Select

        album_add_url = reverse("admin:admin_views_album_add")
        self.selenium.get(self.live_server_url + album_add_url)

        select_element = self.selenium.find_element(By.XPATH, '//*[@id="id_owner"]')
        option = Select(select_element).options[-1]
        self.assertEqual(option.text, "super")
        select_element.click()
        option.click()

        tests = [
            "add_id_owner",
            "change_id_owner",
            "delete_id_owner",
            "view_id_owner",
        ]
        for link_id in tests:
            with self.subTest(link_id):
                link = self.selenium.find_element(By.XPATH, f'//*[@id="{link_id}"]')
                self.assertIsNone(link.get_attribute("aria-disabled"))

    def test_radio_select_add_related_object(self):
        from selenium.webdriver.common.by import By

        redirect_add_url = reverse("admin:redirects_redirect_add")
        self.selenium.get(self.live_server_url + redirect_add_url)

        # There is an add icon and it points to add site page.
        # There are some query parameters in the URL. Check the start.
        add_link = self.selenium.find_element(By.ID, "add_id_site")
        href = add_link.get_attribute("href")
        add_site_url = self.live_server_url + reverse("admin:sites_site_add")
        self.assertTrue(href.startswith(add_site_url))

        # The view_related and delete_related icons should not exist.
        # Selenium takes too much time searching for non-existing elements.
        # The strategy is to check that the preceding sibling of the add link is
        # the radio select, and the parent element should contain two elements:
        # the radio select and the add link, but nothing else.

        # The preceding sibling is the radio select.
        radio_select = self.selenium.find_element(By.ID, "id_site")
        self.assertEqual(radio_select.get_attribute("class"), "radiolist")
        preceding_sibling = add_link.find_element(By.XPATH, "preceding-sibling::*")
        self.assertEqual(radio_select, preceding_sibling)

        # The parent contains the radio select and the add link, but nothing else.
        parent = radio_select.find_element(By.XPATH, "..")
        self.assertEqual(len(parent.find_elements(By.XPATH, "*")), 2)
