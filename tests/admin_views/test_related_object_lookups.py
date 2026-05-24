from django.contrib.admin.tests import AdminPlaywrightTestCase
from django.contrib.auth.models import User
from django.test import override_settings
from django.urls import reverse

from .models import CamelCaseModel


@override_settings(ROOT_URLCONF="admin_views.urls")
class PlaywrightTests(AdminPlaywrightTestCase):
    available_apps = ["admin_views"] + AdminPlaywrightTestCase.available_apps

    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username="super", password="secret", email="super@example.com"
        )
        self.admin_login(
            username="super", password="secret", login_url=reverse("admin:index")
        )

    def test_related_object_link_images_attributes(self):
        album_add_url = reverse("admin:admin_views_album_add")
        self.page.goto(self.live_server_url + album_add_url)

        tests = [
            "add_id_owner",
            "change_id_owner",
            "delete_id_owner",
            "view_id_owner",
        ]
        for link_id in tests:
            with self.subTest(link_id):
                link_image = self.page.locator(f"#{link_id} img")
                self.expect(link_image).to_have_attribute("alt", "")
                self.expect(link_image).to_have_attribute("width", "24")
                self.expect(link_image).to_have_attribute("height", "24")

    def test_related_object_lookup_link_initial_state(self):
        album_add_url = reverse("admin:admin_views_album_add")
        self.page.goto(self.live_server_url + album_add_url)

        tests = [
            "change_id_owner",
            "delete_id_owner",
            "view_id_owner",
        ]
        for link_id in tests:
            with self.subTest(link_id):
                link = self.page.locator(f"#{link_id}")
                self.expect(link).to_have_attribute("aria-disabled", "true")

    def test_related_object_lookup_link_enabled(self):
        album_add_url = reverse("admin:admin_views_album_add")
        self.page.goto(self.live_server_url + album_add_url)

        last_option = self.page.locator("#id_owner option").last
        self.expect(last_option).to_have_text("super")
        self.page.locator("#id_owner").select_option(label="super")

        tests = [
            "add_id_owner",
            "change_id_owner",
            "delete_id_owner",
            "view_id_owner",
        ]
        for link_id in tests:
            with self.subTest(link_id):
                link = self.page.locator(f"#{link_id}")
                self.assertIsNone(link.get_attribute("aria-disabled"))

    def test_related_object_update_with_camel_casing(self):
        add_url = reverse("admin:admin_views_camelcaserelatedmodel_add")
        self.page.goto(self.live_server_url + add_url)
        interesting_name = "A test name"

        # Add a new CamelCaseModel using the "+" icon next to the "fk" field.
        with self.page.expect_popup() as popup_info:
            self.page.locator("#add_id_fk").click()
        popup = popup_info.value

        # Find the "interesting_name" field and enter a value, then save it.
        popup.locator("#id_interesting_name").fill(interesting_name)
        with popup.expect_event("close"):
            popup.locator('input[value="Save"]').click()

        id_value = CamelCaseModel.objects.get(interesting_name=interesting_name).id

        # Check that both the "Available" m2m box and the "Fk" dropdown now
        # include the newly added CamelCaseModel instance.
        fk_dropdown = self.page.locator("#id_fk")
        self.assertHTMLEqual(
            fk_dropdown.inner_html(),
            f"""
            <option value="" selected="">- Select an option -</option>
            <option value="{id_value}" selected>{interesting_name}</option>
            """,
        )
        # Check the newly added instance is not also added in the "to" box.
        m2m_to = self.page.locator("#id_m2m_to")
        self.assertHTMLEqual(m2m_to.inner_html(), "")
        m2m_box = self.page.locator("#id_m2m_from")
        self.assertHTMLEqual(
            m2m_box.inner_html(),
            f"""
            <option title="{interesting_name}" value="{id_value}">
            {interesting_name}</option>
            """,
        )

    def test_related_object_add_js_actions(self):
        add_url = reverse("admin:admin_views_camelcaserelatedmodel_add")
        self.page.goto(self.live_server_url + add_url)
        m2m_to = self.page.locator("#id_m2m_to")
        m2m_box = self.page.locator("#id_m2m_from")
        fk_dropdown = self.page.locator("#id_fk")

        # Add new related entry using +.
        name = "Bergeron"
        with self.page.expect_popup() as popup_info:
            self.page.locator("#add_id_m2m").click()
        popup = popup_info.value
        popup.locator("#id_interesting_name").fill(name)
        with popup.expect_event("close"):
            popup.locator('input[value="Save"]').click()

        id_value = CamelCaseModel.objects.get(interesting_name=name).id

        # Check the new value correctly appears in the "to" box.
        self.assertHTMLEqual(
            m2m_to.inner_html(),
            f"""<option title="{name}" value="{id_value}">{name}</option>""",
        )
        self.assertHTMLEqual(m2m_box.inner_html(), "")
        self.assertHTMLEqual(
            fk_dropdown.inner_html(),
            f"""
            <option value="" selected>- Select an option -</option>
            <option value="{id_value}">{name}</option>
            """,
        )

        # Move the new value to the from box.
        self.page.locator("#id_m2m_to").select_option(value=str(id_value))
        self.page.locator("#id_m2m_remove").click()

        self.assertHTMLEqual(
            m2m_box.inner_html(),
            f"""<option title="{name}" value="{id_value}">{name}</option>""",
        )
        self.assertHTMLEqual(m2m_to.inner_html(), "")

        # Move the new value to the to box.
        self.page.locator("#id_m2m_from").select_option(value=str(id_value))
        self.page.locator("#id_m2m_add").click()

        self.assertHTMLEqual(m2m_box.inner_html(), "")
        self.assertHTMLEqual(
            m2m_to.inner_html(),
            f"""<option title="{name}" value="{id_value}">{name}</option>""",
        )

    def test_child_popup_not_closed_when_parent_minimized(self):
        if self.browser != "chromium":
            self.skipTest("CDP is required to minimize the browser window.")
        album_add_url = reverse("admin:admin_views_album_add")
        self.page.goto(self.live_server_url + album_add_url)

        # Open a popup window using the "+" icon next to the "owner" field.
        with self.page.expect_popup() as popup_info:
            self.page.locator("#add_id_owner").click()
        popup = popup_info.value

        # Minimize the main window via CDP.
        cdp = self.page.context.new_cdp_session(self.page)
        window_info = cdp.send("Browser.getWindowForTarget")
        cdp.send(
            "Browser.setWindowBounds",
            {
                "windowId": window_info["windowId"],
                "bounds": {"windowState": "minimized"},
            },
        )

        # The popup should not be closed by dismissChildPopups().
        self.page.wait_for_timeout(1000)
        self.assertFalse(popup.is_closed())

        # Restore the main window.
        cdp.send(
            "Browser.setWindowBounds",
            {
                "windowId": window_info["windowId"],
                "bounds": {"windowState": "normal"},
            },
        )
        cdp.detach()
