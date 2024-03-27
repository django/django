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

    def test_filter_horizontal_without_duplication(self):
        """
        Test that the filter_horizontal widget doesn't duplicate entries
        in the Chosen column after instance is added from another field
        using the plus JS action.
        """
        # Use Transition and TransitionState models from
        # tests.admin_views.models with the TransitionAdmin
        # from tests.admin_views.admin
        from selenium.webdriver.common.by import By

        def _get_HTML_inside_element_by_id(id_):
            return self.selenium.find_element(By.ID, id_).get_attribute("innerHTML")

        transition_add_url = reverse("admin:admin_views_transition_add")
        self.selenium.get(self.live_server_url + transition_add_url)
        state_name = "test state"

        # Add a TransitionState from the plus button on the Target field
        self.selenium.find_element(By.ID, "add_id_target").click()

        # Switch to the popup window
        self.wait_for_and_switch_to_popup()

        # Find the label field and add text to it
        self.selenium.find_element(By.ID, "id_label").send_keys(state_name)

        # Now find the save button and click it
        self.selenium.find_element(By.NAME, "_save").click()

        # Return to the main window
        self.wait_until(lambda d: len(d.window_handles) == 1, 1)
        self.selenium.switch_to.window(self.selenium.window_handles[0])

        # Now check that the state shows in the Target box
        self.assertHTMLEqual(
            _get_HTML_inside_element_by_id("id_target"),
            f"""
            <option value="" selected="">---------</option>
            <option value="1" selected>{state_name}</option>
            """,
        )

        # Check that the state is in the Available Source box
        self.assertHTMLEqual(
            _get_HTML_inside_element_by_id("id_source_from"),
            f"""
            <option value="1">{state_name}</option>
            """,
        )

        # Check that the state is not in the Chosen box (hence, box is empty)
        self.assertHTMLEqual(_get_HTML_inside_element_by_id("id_source_to"), "")
