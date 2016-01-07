class SeleniumHelpers(object):
    # selenium imports must be inner imports since selenium isn't a required
    # dependency of the test suite.

    def wait_until(self, callback, timeout=10):
        """
        Block until the `callback` returns a value that is not falsy. This can
        be called, for example, after clicking a link or submitting a form.
        """
        from selenium.webdriver.support.wait import WebDriverWait
        WebDriverWait(self.selenium, timeout).until(callback)

    def wait_for_popup(self, num_windows=2, timeout=10):
        """
        Block until `num_windows` are present (usually 2, but can be overridden
        in the case of popups opening other popups).
        """
        self.wait_until(lambda d: len(d.window_handles) == num_windows, timeout)

    def wait_loaded_tag(self, tag_name, timeout=10):
        """
        Block until the element with the given `tag_name` is found on the page.
        """
        self.wait_for(tag_name, timeout)

    def wait_for(self, css_selector, timeout=10):
        """
        Block until `css_selector` is found on the page.
        """
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as ec
        self.wait_until(
            ec.presence_of_element_located((By.CSS_SELECTOR, css_selector)),
            timeout
        )

    def wait_for_text(self, css_selector, text, timeout=10):
        """
        Block until the `text` is found in the `css_selector`.
        """
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as ec
        self.wait_until(
            ec.text_to_be_present_in_element((By.CSS_SELECTOR, css_selector), text),
            timeout
        )

    def wait_for_value(self, css_selector, text, timeout=10):
        """
        Block until the value is found in the CSS selector.
        """
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as ec
        self.wait_until(
            ec.text_to_be_present_in_element_value((By.CSS_SELECTOR, css_selector), text),
            timeout
        )

    def wait_page_loaded(self):
        """
        Block until page has started to load (indicated by presence of the
        body tag).
        """
        from selenium.common.exceptions import TimeoutException
        try:
            # Wait for the next page to be loaded
            self.wait_loaded_tag('body')
        except TimeoutException:
            # IE7 occasionally returns an error "Internet Explorer cannot
            # display the webpage" and doesn't load the next page. We just
            # ignore it.
            pass

    def get_select_option(self, selector, value):
        """
        Return the <OPTION> with the value `value` inside the <SELECT> widget
        identified by the CSS selector `selector`.
        """
        from selenium.common.exceptions import NoSuchElementException
        options = self.selenium.find_elements_by_css_selector('%s > option' % selector)
        for option in options:
            if option.get_attribute('value') == value:
                return option
        raise NoSuchElementException('Option "%s" not found in "%s"' % (value, selector))

    def assertSelectOptions(self, selector, values):
        """
        Assert that the <SELECT> widget identified by `selector` has the
        options with the given `values`.
        """
        options = self.selenium.find_elements_by_css_selector('%s > option' % selector)
        actual_values = []
        for option in options:
            actual_values.append(option.get_attribute('value'))
        self.assertEqual(values, actual_values)

    def has_css_class(self, selector, klass):
        """
        Return True if the element identified by `selector` has the CSS class
        `klass`.
        """
        element = self.selenium.find_element_by_css_selector(selector)
        return element.get_attribute('class').find(klass) != -1
