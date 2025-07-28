from contextlib import contextmanager
from pathlib import Path

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement

from django.contrib.admin.models import ADDITION, LogEntry
from django.contrib.admin.tests import AdminSeleniumTestCase
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
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
        )

        from .models import Question

        Question.objects.create(id=1, question_text="What's up?", pub_date="2025-07-01")

    #     # TODO: This shouldn't be necessary
    #     """Sets light mode in local storage to avoid auto dark mode."""
    #     self.selenium.execute_script("localStorage.setItem('theme', 'light');")

    # def tearDown(self):
    #     """Reset the local storage to default."""
    #     self.selenium.execute_script("localStorage.removeItem('theme');")

    def hide_nav_sidebar(self):
        """Hide the navigation sidebar if it's open."""
        try:
            if self.selenium.find_element(By.ID, "nav-sidebar").is_displayed():
                self.selenium.find_element(
                    By.CSS_SELECTOR, "#toggle-nav-sidebar"
                ).click()
        except NoSuchElementException:
            pass
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
        Take a cropped screenshot of a screenshot.

        Parameters:
            image: Screenshot image in bytes
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
    def test_tutorial_admin_login(self):
        """Take a screenshot of the admin login form"""
        self.selenium.get(self.live_server_url + reverse("admin:index"))

        login_form = self.selenium.find_element(By.ID, "container")
        self.take_element_screenshot(login_form, "admin01")

    @screenshot_cases(SIZES)
    def test_tutorial_admin_main_page(self):
        """Take a screenshot of the main admin page"""

        self.admin_login(username="admin", password="secret")

        self.selenium.get(self.live_server_url + reverse("admin:index"))

        screenshot = self.selenium.get_screenshot_as_png()

        # Take the 2nd screenshot
        self.take_cropped_screenshot(screenshot, "admin02", 800, 400, left=0, top=0)

        # Take the 3rd screenshot - 140 pixels below the top to avoid the navbar
        self.take_cropped_screenshot(screenshot, "admin03t", 800, 400, left=0, top=140)

    @screenshot_cases(SIZES)
    def test_tutorial_question_model_list(self):
        """Take a screenshot of the question model list"""

        from polls.models import Question
        from selenium.webdriver.common.action_chains import ActionChains

        q = Question.objects.get(question_text="What's up?")

        # Simulate creating a question via the admin interface
        # to be shown in the screenshot
        LogEntry.objects.create(
            user_id=self.superuser.pk,
            content_type_id=ContentType.objects.get_for_model(Question).pk,
            object_id=q.pk,
            object_repr=str(q),
            action_flag=ADDITION,
            change_message="Added.",
        )

        self.admin_login(username="admin", password="secret")

        # admin04t - Create a question and take a screenshot of the questions list

        self.selenium.get(
            self.live_server_url + reverse("admin:polls_question_changelist")
        )

        self.hide_nav_sidebar()
        self.change_header_display("none")

        content = self.selenium.find_element(By.ID, "content-start")
        self.take_element_screenshot(content, "admin04t")

        # admin05t - Edit question form

        # click the What's up? question to open the change form
        question_link = self.selenium.find_element(By.LINK_TEXT, "What's up?")
        question_link.click()

        # Take a screenshot of the change question form
        question_content = self.selenium.find_element(By.ID, "content")
        self.take_element_screenshot(question_content, "admin05t")

        # Change the “Date published” by clicking the “Today” and “Now” shortcuts.
        # Then click “Save and continue editing.”

        # TODO: This doesn't take into account i18n
        actions = ActionChains(self.selenium)
        today_button = self.selenium.find_element(By.PARTIAL_LINK_TEXT, "Today")
        now_button = self.selenium.find_element(By.PARTIAL_LINK_TEXT, "Now")
        save_continue_button = self.selenium.find_element(By.NAME, "_continue")

        actions.click(today_button).click(now_button).click(
            save_continue_button
        ).perform()

        # Wait 1 seconds for the request to be processed
        # Not sure why selenium.implicitly_wait(1) doesnt stops
        import time

        time.sleep(1)

        # admin06t - Admin change history for question model
        # Navigate to the change history of the question model
        self.selenium.get(
            self.live_server_url + reverse("admin:polls_question_history", args=(1,))
        )
        history_content = self.selenium.find_element(By.ID, "content")
        self.take_element_screenshot(history_content, "admin06t")

    @screenshot_cases(SIZES)
    def test_tutorial_question_part_seven(self):
        """Generate admin images of the part 7 of the tutorial"""

        from polls.models import Question

        from django.contrib import admin

        class QuestionAdmin(admin.ModelAdmin):
            fields = ["pub_date", "question_text"]

        # Modify the admin interface to screenshot it
        if admin.site.is_registered(Question):
            admin.site.unregister(Question)

        admin.site.register(Question, QuestionAdmin)

        self.admin_login(username="admin", password="secret")

        # Go to the Question model edit page
        self.selenium.get(
            self.live_server_url + reverse("admin:polls_question_change", args=(1,))
        )

        self.hide_nav_sidebar()
        self.change_header_display("none")

        # Take a screenshot of the change question form
        # similar to admin05t but with the fields changed
        question_content = self.selenium.find_element(By.ID, "content")
        self.take_element_screenshot(question_content, "admin07")

        # HACK Modify the registered admin in runtime
        admin.site.get_model_admin(Question).fieldsets = [
            (None, {"fields": ["question_text"]}),
            ("Date information", {"fields": ["pub_date"]}),
        ]

        self.selenium.refresh()

        # Take a screenshot of the change question form with the new fieldsets
        question_content = self.selenium.find_element(By.ID, "content")
        self.take_element_screenshot(question_content, "admin08t")

        # admin09t - Screenshot Add choice form
        self.selenium.get(self.live_server_url + reverse("admin:polls_choice_add"))
        choice_content = self.selenium.find_element(By.ID, "content")
        self.take_element_screenshot(choice_content, "admin09")

    # admin10t - Add question form with choices. Date information collapsed
    # admin11t - Choices tabular inline simple
    # admin12t - Question model list with question created
    # admin13t - Question model list with filter
    # admin14t - Choices tabular inline expanded
