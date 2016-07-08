from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import modify_settings
from django.test.selenium import SeleniumTestCase
from django.utils.deprecation import MiddlewareMixin
from django.utils.translation import ugettext as _


class CSPMiddleware(MiddlewareMixin):
    """The admin's JavaScript should be compatible with CSP."""
    def process_response(self, request, response):
        response['Content-Security-Policy'] = "default-src 'self'"
        return response


@modify_settings(MIDDLEWARE={'append': 'django.contrib.admin.tests.CSPMiddleware'})
class AdminSeleniumTestCase(SeleniumTestCase, StaticLiveServerTestCase):

    available_apps = [
        'django.contrib.admin',
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.sessions',
        'django.contrib.sites',
    ]

    def wait_until(self, callback, timeout=10):
        """
        Helper function that blocks the execution of the tests until the
        specified callback returns a value that is not falsy. This function can
        be called, for example, after clicking a link or submitting a form.
        See the other public methods that call this function for more details.
        """
        from selenium.webdriver.support.wait import WebDriverWait
        WebDriverWait(self.selenium, timeout).until(callback)

    def wait_for_popup(self, num_windows=2, timeout=10):
        """
        Block until `num_windows` are present (usually 2, but can be
        overridden in the case of pop-ups opening other pop-ups).
        """
        self.wait_until(lambda d: len(d.window_handles) == num_windows, timeout)

    def wait_for(self, css_selector, timeout=10):
        """
        Helper function that blocks until a CSS selector is found on the page.
        """
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as ec
        self.wait_until(
            ec.presence_of_element_located((By.CSS_SELECTOR, css_selector)),
            timeout
        )

    def wait_for_text(self, css_selector, text, timeout=10):
        """
        Helper function that blocks until the text is found in the CSS selector.
        """
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as ec
        self.wait_until(
            ec.text_to_be_present_in_element(
                (By.CSS_SELECTOR, css_selector), text),
            timeout
        )

    def wait_for_value(self, css_selector, text, timeout=10):
        """
        Helper function that blocks until the value is found in the CSS selector.
        """
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as ec
        self.wait_until(
            ec.text_to_be_present_in_element_value(
                (By.CSS_SELECTOR, css_selector), text),
            timeout
        )

    def wait_until_visible(self, css_selector, timeout=10):
        """
        Block until the element described by the CSS selector is visible.
        """
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as ec
        self.wait_until(
            ec.visibility_of_element_located((By.CSS_SELECTOR, css_selector)),
            timeout
        )

    def wait_until_invisible(self, css_selector, timeout=10):
        """
        Block until the element described by the CSS selector is invisible.
        """
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as ec
        self.wait_until(
            ec.invisibility_of_element_located((By.CSS_SELECTOR, css_selector)),
            timeout
        )

    def wait_page_loaded(self):
        """
        Block until page has started to load.
        """
        from selenium.common.exceptions import TimeoutException
        try:
            # Wait for the next page to be loaded
            self.wait_for('body')
        except TimeoutException:
            # IE7 occasionally returns an error "Internet Explorer cannot
            # display the webpage" and doesn't load the next page. We just
            # ignore it.
            pass

    def admin_login(self, username, password, login_url='/admin/'):
        """
        Helper function to log into the admin.
        """
        self.selenium.get('%s%s' % (self.live_server_url, login_url))
        username_input = self.selenium.find_element_by_name('username')
        username_input.send_keys(username)
        password_input = self.selenium.find_element_by_name('password')
        password_input.send_keys(password)
        login_text = _('Log in')
        self.selenium.find_element_by_xpath(
            '//input[@value="%s"]' % login_text).click()
        self.wait_page_loaded()

    def get_css_value(self, selector, attribute):
        """
        Helper function that returns the value for the CSS attribute of an
        DOM element specified by the given selector. Uses the jQuery that ships
        with Django.
        """
        return self.selenium.execute_script(
            'return django.jQuery("%s").css("%s")' % (selector, attribute))

    def get_select_option(self, selector, value):
        """
        Returns the <OPTION> with the value `value` inside the <SELECT> widget
        identified by the CSS selector `selector`.
        """
        from selenium.common.exceptions import NoSuchElementException
        options = self.selenium.find_elements_by_css_selector('%s > option' % selector)
        for option in options:
            if option.get_attribute('value') == value:
                return option
        raise NoSuchElementException('Option "%s" not found in "%s"' % (value, selector))

    def _assertOptionsValues(self, options_selector, values):
        if values:
            options = self.selenium.find_elements_by_css_selector(options_selector)
            actual_values = []
            for option in options:
                actual_values.append(option.get_attribute('value'))
            self.assertEqual(values, actual_values)
        else:
            # Prevent the `find_elements_by_css_selector` call from blocking
            # if the selector doesn't match any options as we expect it
            # to be the case.
            with self.disable_implicit_wait():
                self.wait_until(
                    lambda driver: len(driver.find_elements_by_css_selector(options_selector)) == 0
                )

    def assertSelectOptions(self, selector, values):
        """
        Asserts that the <SELECT> widget identified by `selector` has the
        options with the given `values`.
        """
        self._assertOptionsValues("%s > option" % selector, values)

    def assertSelectedOptions(self, selector, values):
        """
        Asserts that the <SELECT> widget identified by `selector` has the
        selected options with the given `values`.
        """
        self._assertOptionsValues("%s > option:checked" % selector, values)

    def has_css_class(self, selector, klass):
        """
        Returns True if the element identified by `selector` has the CSS class
        `klass`.
        """
        return (self.selenium.find_element_by_css_selector(selector)
                .get_attribute('class').find(klass) != -1)
