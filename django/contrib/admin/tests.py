from contextlib import contextmanager

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import modify_settings
from django.test.selenium import SeleniumTestCase
from django.utils.deprecation import MiddlewareMixin
from django.utils.translation import gettext as _

# Make unittest ignore frames in this module when reporting failures.
__unittest = True


class CSPMiddleware(MiddlewareMixin):
    """The admin's JavaScript should be compatible with CSP."""

    def process_response(self, request, response):
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        return response


@modify_settings(MIDDLEWARE={"append": "django.contrib.admin.tests.CSPMiddleware"})
class AdminSeleniumTestCase(SeleniumTestCase, StaticLiveServerTestCase):
    available_apps = [
        "django.contrib.admin",
        "django.contrib.auth",
        "django.contrib.contenttypes",
        "django.contrib.sessions",
        "django.contrib.sites",
    ]

    def wait_until(self, callback, timeout=10):
        """
        Block the execution of the tests until the specified callback returns a
        value that is not falsy. This method can be called, for example, after
        clicking a link or submitting a form. See the other public methods that
        call this function for more details.
        """
        from selenium.webdriver.support.wait import WebDriverWait

        WebDriverWait(self.selenium, timeout).until(callback)

    def wait_for_and_switch_to_popup(self, num_windows=2, timeout=10):
        """
        Block until `num_windows` are present and are ready (usually 2, but can
        be overridden in the case of pop-ups opening other pop-ups). Switch the
        current window to the new pop-up.
        """
        self.wait_until(lambda d: len(d.window_handles) == num_windows, timeout)
        self.selenium.switch_to.window(self.selenium.window_handles[-1])
        self.wait_page_ready()

    def wait_for(self, css_selector, timeout=10):
        """
        Block until a CSS selector is found on the page.
        """
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as ec

        self.wait_until(
            ec.presence_of_element_located((By.CSS_SELECTOR, css_selector)), timeout
        )

    def wait_for_text(self, css_selector, text, timeout=10):
        """
        Block until the text is found in the CSS selector.
        """
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as ec

        self.wait_until(
            ec.text_to_be_present_in_element((By.CSS_SELECTOR, css_selector), text),
            timeout,
        )

    def wait_for_value(self, css_selector, text, timeout=10):
        """
        Block until the value is found in the CSS selector.
        """
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as ec

        self.wait_until(
            ec.text_to_be_present_in_element_value(
                (By.CSS_SELECTOR, css_selector), text
            ),
            timeout,
        )

    def wait_until_visible(self, css_selector, timeout=10):
        """
        Block until the element described by the CSS selector is visible.
        """
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as ec

        self.wait_until(
            ec.visibility_of_element_located((By.CSS_SELECTOR, css_selector)), timeout
        )

    def wait_until_invisible(self, css_selector, timeout=10):
        """
        Block until the element described by the CSS selector is invisible.
        """
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as ec

        self.wait_until(
            ec.invisibility_of_element_located((By.CSS_SELECTOR, css_selector)), timeout
        )

    def wait_page_ready(self, timeout=10):
        """
        Block until the  page is ready.
        """
        self.wait_until(
            lambda driver: driver.execute_script("return document.readyState;")
            == "complete",
            timeout,
        )

    @contextmanager
    def wait_page_loaded(self, timeout=10):
        """
        Block until a new page has loaded and is ready.
        """
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as ec

        old_page = self.selenium.find_element(By.TAG_NAME, "html")
        yield
        # Wait for the next page to be loaded
        self.wait_until(ec.staleness_of(old_page), timeout=timeout)
        self.wait_page_ready(timeout=timeout)

    def admin_login(self, username, password, login_url="/admin/"):
        """
        Log in to the admin.
        """
        from selenium.webdriver.common.by import By

        self.selenium.get("%s%s" % (self.live_server_url, login_url))
        username_input = self.selenium.find_element(By.NAME, "username")
        username_input.send_keys(username)
        password_input = self.selenium.find_element(By.NAME, "password")
        password_input.send_keys(password)
        login_text = _("Log in")
        with self.wait_page_loaded():
            self.selenium.find_element(
                By.XPATH, '//input[@value="%s"]' % login_text
            ).click()

    def select_option(self, selector, value):
        """
        Select the <OPTION> with the value `value` inside the <SELECT> widget
        identified by the CSS selector `selector`.
        """
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import Select

        select = Select(self.selenium.find_element(By.CSS_SELECTOR, selector))
        select.select_by_value(value)

    def deselect_option(self, selector, value):
        """
        Deselect the <OPTION> with the value `value` inside the <SELECT> widget
        identified by the CSS selector `selector`.
        """
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import Select

        select = Select(self.selenium.find_element(By.CSS_SELECTOR, selector))
        select.deselect_by_value(value)

    def assertCountSeleniumElements(self, selector, count, root_element=None):
        """
        Assert number of matches for a CSS selector.

        `root_element` allow restriction to a pre-selected node.
        """
        from selenium.webdriver.common.by import By

        root_element = root_element or self.selenium
        self.assertEqual(
            len(root_element.find_elements(By.CSS_SELECTOR, selector)), count
        )

    def _assertOptionsValues(self, options_selector, values):
        from selenium.webdriver.common.by import By

        if values:
            options = self.selenium.find_elements(By.CSS_SELECTOR, options_selector)
            actual_values = []
            for option in options:
                actual_values.append(option.get_attribute("value"))
            self.assertEqual(values, actual_values)
        else:
            # Prevent the `find_elements(By.CSS_SELECTOR, …)` call from blocking
            # if the selector doesn't match any options as we expect it
            # to be the case.
            with self.disable_implicit_wait():
                self.wait_until(
                    lambda driver: not driver.find_elements(
                        By.CSS_SELECTOR, options_selector
                    )
                )

    def assertSelectOptions(self, selector, values):
        """
        Assert that the <SELECT> widget identified by `selector` has the
        options with the given `values`.
        """
        self._assertOptionsValues("%s > option" % selector, values)

    def assertSelectedOptions(self, selector, values):
        """
        Assert that the <SELECT> widget identified by `selector` has the
        selected options with the given `values`.
        """
        self._assertOptionsValues("%s > option:checked" % selector, values)

    def is_disabled(self, selector):
        """
        Return True if the element identified by `selector` has the `disabled`
        attribute.
        """
        from selenium.webdriver.common.by import By

        return (
            self.selenium.find_element(By.CSS_SELECTOR, selector).get_attribute(
                "disabled"
            )
            == "true"
        )
