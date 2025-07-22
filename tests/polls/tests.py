from contextlib import contextmanager
from pathlib import Path

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement

from django.contrib.admin.tests import AdminSeleniumTestCase
from django.contrib.auth.models import User
from django.test import modify_settings, override_settings
from django.test.selenium import ChangeWindowSize, screenshot_cases
from django.urls import reverse

SIZES = ["docs_size"]


@modify_settings(INSTALLED_APPS={"append": "django.contrib.flatpages"})
@override_settings(ROOT_URLCONF="polls.urls")
class AdminDjangoTutorialImageGenerationSeleniumTests(AdminSeleniumTestCase):
    """Selenium tests for generating Django admin images used in the Django tutorial"""

    available_apps = AdminSeleniumTestCase.available_apps + [
        "django.contrib.flatpages",
        "polls",
    ]

    path = Path.cwd().parent / "docs" / "intro" / "_images"

    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username="admin",
            password="secret",
            email="admin@example.com",
            first_name="Admin",
            last_name="Super",
        )

        # TODO: This shouldn't be necessary
        """Sets light mode in local storage to avoid auto dark mode."""
        try:
            self.selenium.execute_script("localStorage.setItem('theme', 'light');")
        except Exception:
            # If localStorage is not available, we can skip this step.
            pass

    def tearDown(self):
        self.selenium.execute_script("localStorage.removeItem('theme');")

    def hide_nav_sidebar(self):
        """Hide the navigation sidebar if it's open."""
        if self.selenium.find_element(By.ID, "nav-sidebar").is_displayed():
            self.selenium.find_element(By.CSS_SELECTOR, "#toggle-nav-sidebar").click()
        self.selenium.execute_script(
            'document.getElementById("toggle-nav-sidebar").style.display = "none";'
        )

    def change_header_display(self, display):
        self.selenium.execute_script(
            f'document.getElementById("header").style.display = "{display}";'
        )
        self.selenium.execute_script(
            f'document.getElementsByTagName("nav")[0].style.display = "{display}";'
        )

    @contextmanager
    def docs_size(self):
        with ChangeWindowSize(800, 800, self.selenium):
            yield

    def take_window_screenshot(self, filename):
        """Take a screenshot of the full window."""
        path = self.path
        assert path.exists()
        self.selenium.save_screenshot(path / f"{filename}.png")

    def take_element_screenshot(self, element: WebElement, filename: str):
        """Take a screenshot of a specific element."""
        full_path = self.path / f"{filename}.png"
        element.screenshot(str(full_path))

    @screenshot_cases(SIZES)
    def test_tutorial_admin_login(self):
        """Take a screenshot of the admin login form"""
        self.selenium.get(self.live_server_url + reverse("admin:index"))

        login_form = self.selenium.find_element(By.ID, "container")
        self.take_element_screenshot(login_form, "admin01")

    def take_cropped_screenshot(
        self,
        image: bytes,
        filename: str,
        width: int,
        height: int,
        left: int = 0,
        top: int = 0,
    ):
        """
        Take a cropped screenshot of the current page.

        Parameters:
            filename: Name of the output file (without extension)
            width: Width of the cropped area in pixels
            height: Height of the cropped area in pixels
            left: Left position for cropping (default: 0)
            top: Top position for cropping (default: 0)
        """

        import io

        from PIL import Image

        # Convert to PIL Image
        image = Image.open(io.BytesIO(image))

        # Calculate crop boundaries
        right = left + width
        bottom = top + height

        # Validate crop area
        if right > image.width or bottom > image.height:
            raise ValueError(
                f"Crop area ({left}, {top}, {right}, {bottom}) exceeds "
                f"image dimensions ({image.width}, {image.height})"
            )

        # Crop the image
        cropped_image = image.crop((left, top, right, bottom))

        # Save the cropped image
        cropped_image.save(self.path / f"{filename}.png")

    @screenshot_cases(SIZES)
    def test_tutorial_admin_main_page(self):
        """Take a screenshot of the main admin page"""

        self.admin_login(username="admin", password="secret")

        self.selenium.get(self.live_server_url + reverse("admin:index"))

        screenshot = self.selenium.get_screenshot_as_png()

        # Take the 2nd screenshot
        self.take_cropped_screenshot(screenshot, "admin02", 1000, 400, left=0, top=0)
