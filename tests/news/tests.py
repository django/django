from contextlib import contextmanager
from pathlib import Path

from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webelement import WebElement

from django.contrib.admin.tests import AdminSeleniumTestCase
from django.contrib.auth.models import User
from django.test import modify_settings, override_settings
from django.test.selenium import ChangeWindowSize, screenshot_cases
from django.urls import reverse
from django.utils.text import slugify

from .models import Article

SIZES = ["docs_size"]


@modify_settings(INSTALLED_APPS={"append": "django.contrib.flatpages"})
@override_settings(ROOT_URLCONF="news.urls")
class AdminDocsImageGenerationSeleniumTests(AdminSeleniumTestCase):
    """Selenium tests for generating images for the Django documentation."""

    available_apps = AdminSeleniumTestCase.available_apps + [
        "django.contrib.flatpages",
        "news",
    ]

    path = Path.cwd().parent / "docs" / "ref" / "contrib" / "admin" / "_images"

    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username="admin",
            password="secret",
            email="admin@example.com",
            first_name="Admin",
            last_name="Super",
        )
        self.admin_login(username="admin", password="secret")

        # TODO: This shouldn't be necessary
        """Sets light mode in local storage to avoid auto dark mode."""
        self.selenium.execute_script("localStorage.setItem('theme', 'light');")

    def tearDown(self):
        """Reset the local storage to default."""
        self.selenium.execute_script("localStorage.removeItem('theme');")

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

    @screenshot_cases(SIZES)
    def test_user_actions(self):
        users = [
            ("Adrian", "Holovaty", False),
            ("Admin", "User", True),
            ("Jacob", "Kaplan-Moss", True),
            ("Simon", "Willison", False),
        ]
        for fn, ln, is_staff in users:
            username = fn.lower()
            User.objects.get_or_create(
                username=username,
                defaults=dict(
                    email=f"{username}@example.com",
                    first_name=fn,
                    last_name=ln,
                    is_staff=is_staff,
                ),
            )
        self.selenium.get(self.live_server_url + reverse("admin:auth_user_changelist"))
        self.hide_nav_sidebar()
        self.change_header_display("none")

        filter_link = self.selenium.find_element(By.CSS_SELECTOR, "details summary")
        # Simulate a hover.
        ActionChains(self.selenium).move_to_element(filter_link).perform()
        self.take_window_screenshot("list_filter")

        self.selenium.find_element(By.NAME, "action").click()
        self.take_window_screenshot("admin-actions")

    @screenshot_cases(SIZES)
    def test_flatpages_fieldsets(self):
        self.selenium.get(
            self.live_server_url + reverse("admin:flatpages_flatpage_add")
        )
        self.hide_nav_sidebar()
        self.change_header_display("none")

        fieldset = self.selenium.find_element(By.ID, "fieldset-0-1-heading")
        # Simulate a hover.
        ActionChains(self.selenium).move_to_element(fieldset).perform()
        self.take_window_screenshot("fieldsets")

    @screenshot_cases(SIZES)
    def test_articles_actions(self):
        stories = [
            ("A New Human-like Species Discovered in Deep Burial Chamber", "p"),
            ("Django 1.9 Released", "d"),
            (
                "Mars Is a Real Fixer-Upper of a Planet, Says Elon Musk on Colbert's "
                "'Late Show'",
                "w",
            ),
            ("The Coming of the Glacier Man", "d"),
            ("The Last Audio Casette Factory", "p"),
        ]
        for title, status in stories:
            slug = slugify(title)
            Article.objects.get_or_create(
                slug=slug, defaults=dict(title=title, status=status)
            )

        self.selenium.get(
            self.live_server_url + reverse("admin:news_article_changelist")
        )
        self.hide_nav_sidebar()
        self.change_header_display("none")

        checkboxes = self.selenium.find_elements(By.NAME, "_selected_action")
        checkboxes[1].click()
        checkboxes[3].click()

        self.selenium.find_element(By.NAME, "action").click()
        ActionChains(self.selenium).send_keys(Keys.ARROW_DOWN).perform()
        ActionChains(self.selenium).send_keys(Keys.ARROW_DOWN).perform()
        self.take_window_screenshot("adding-actions-to-the-modeladmin")

        self.selenium.find_element(
            By.CSS_SELECTOR, 'button[type="submit"][name="index"]'
        ).click()
        self.take_window_screenshot("actions-as-modeladmin-methods")

    @screenshot_cases(SIZES)
    def test_article_with_two_newspapers(self):
        """Test creating an article attached to 2 newspapers and capture the newspaper
        raw ids input field."""

        from .models import Newspaper

        # Create two newspapers with IDs 1 and 2
        newspaper1 = Newspaper.objects.create(id=1, name="Daily News")
        newspaper2 = Newspaper.objects.create(id=2, name="Weekly Times")

        # Create an article attached to both newspapers
        article = Article.objects.create(
            title="Test Article",
            status="p",
        )
        article.newspaper.add(newspaper1, newspaper2)

        # Navigate to the article edit page
        self.selenium.get(
            self.live_server_url
            + reverse("admin:news_article_change", args=[article.id])
        )
        self.hide_nav_sidebar()
        self.change_header_display("none")

        # Capture the raw_id_fields screenshot
        newspaper_field = self.selenium.find_element(By.CLASS_NAME, "field-newspaper")
        self.take_element_screenshot(newspaper_field, "raw_id_fields")


@modify_settings(INSTALLED_APPS={"append": "django.contrib.flatpages"})
@override_settings(ROOT_URLCONF="news.urls")
class AdminDjangoTutorialImageGenerationSeleniumTests(AdminSeleniumTestCase):
    """Selenium tests for generating Django admin images used in the Django tutorial"""

    available_apps = AdminSeleniumTestCase.available_apps + [
        "django.contrib.flatpages",
        "news",
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
