import re
import unittest
from urlparse import urlsplit, urlunsplit

from django.http import QueryDict
from django.db import transaction
from django.core import mail
from django.core.management import call_command
from django.test import _doctest as doctest
from django.test.client import Client

normalize_long_ints = lambda s: re.sub(r'(?<![\w])(\d+)L(?![\w])', '\\1', s)

def to_list(value):
    """
    Puts value into a list if it's not already one.
    Returns an empty list if value is None.
    """
    if value is None:
        value = []
    elif not isinstance(value, list):
        value = [value]
    return value


class OutputChecker(doctest.OutputChecker):
    def check_output(self, want, got, optionflags):
        ok = doctest.OutputChecker.check_output(self, want, got, optionflags)

        # Doctest does an exact string comparison of output, which means long
        # integers aren't equal to normal integers ("22L" vs. "22"). The
        # following code normalizes long integers so that they equal normal
        # integers.
        if not ok:
            return normalize_long_ints(want) == normalize_long_ints(got)
        return ok

class DocTestRunner(doctest.DocTestRunner):
    def __init__(self, *args, **kwargs):
        doctest.DocTestRunner.__init__(self, *args, **kwargs)
        self.optionflags = doctest.ELLIPSIS

    def report_unexpected_exception(self, out, test, example, exc_info):
        doctest.DocTestRunner.report_unexpected_exception(self, out, test,
                                                          example, exc_info)
        # Rollback, in case of database errors. Otherwise they'd have
        # side effects on other tests.
        transaction.rollback_unless_managed()

class TestCase(unittest.TestCase):
    def _pre_setup(self):
        """Performs any pre-test setup. This includes:

            * Flushing the database.
            * If the Test Case class has a 'fixtures' member, installing the 
              named fixtures.
            * Clearing the mail test outbox.
        """
        call_command('flush', verbosity=0, interactive=False)
        if hasattr(self, 'fixtures'):
            # We have to use this slightly awkward syntax due to the fact
            # that we're using *args and **kwargs together.
            call_command('loaddata', *self.fixtures, **{'verbosity': 0})
        mail.outbox = []

    def __call__(self, result=None):
        """
        Wrapper around default __call__ method to perform common Django test
        set up. This means that user-defined Test Cases aren't required to
        include a call to super().setUp().
        """
        self.client = Client()
        try:
            self._pre_setup()
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception:
            import sys
            result.addError(self, sys.exc_info())
            return
        super(TestCase, self).__call__(result)

    def assertRedirects(self, response, expected_url, status_code=302,
                        target_status_code=200, host=None):
        """Asserts that a response redirected to a specific URL, and that the
        redirect URL can be loaded.

        Note that assertRedirects won't work for external links since it uses
        TestClient to do a request.
        """
        self.assertEqual(response.status_code, status_code,
            ("Response didn't redirect as expected: Response code was %d"
             " (expected %d)" % (response.status_code, status_code)))
        url = response['Location']
        scheme, netloc, path, query, fragment = urlsplit(url)
        e_scheme, e_netloc, e_path, e_query, e_fragment = urlsplit(expected_url)
        if not (e_scheme or e_netloc):
            expected_url = urlunsplit(('http', host or 'testserver', e_path,
                    e_query, e_fragment))
        self.assertEqual(url, expected_url,
            "Response redirected to '%s', expected '%s'" % (url, expected_url))

        # Get the redirection page, using the same client that was used
        # to obtain the original response.
        redirect_response = response.client.get(path, QueryDict(query))
        self.assertEqual(redirect_response.status_code, target_status_code,
            ("Couldn't retrieve redirection page '%s': response code was %d"
             " (expected %d)") %
                 (path, redirect_response.status_code, target_status_code))

    def assertContains(self, response, text, count=None, status_code=200):
        """
        Asserts that a response indicates that a page was retrieved
        successfully, (i.e., the HTTP status code was as expected), and that
        ``text`` occurs ``count`` times in the content of the response.
        If ``count`` is None, the count doesn't matter - the assertion is true
        if the text occurs at least once in the response.
        """
        self.assertEqual(response.status_code, status_code,
            "Couldn't retrieve page: Response code was %d (expected %d)'" %
                (response.status_code, status_code))
        real_count = response.content.count(text)
        if count is not None:
            self.assertEqual(real_count, count,
                "Found %d instances of '%s' in response (expected %d)" %
                    (real_count, text, count))
        else:
            self.failUnless(real_count != 0,
                            "Couldn't find '%s' in response" % text)

    def assertFormError(self, response, form, field, errors):
        """
        Asserts that a form used to render the response has a specific field
        error.
        """
        # Put context(s) into a list to simplify processing.
        contexts = to_list(response.context)
        if not contexts:
            self.fail('Response did not use any contexts to render the'
                      ' response')

        # Put error(s) into a list to simplify processing.
        errors = to_list(errors)

        # Search all contexts for the error.
        found_form = False
        for i,context in enumerate(contexts):
            if form not in context:
                continue
            found_form = True
            for err in errors:
                if field:
                    if field in context[form].errors:
                        field_errors = context[form].errors[field]
                        self.failUnless(err in field_errors,
                                        "The field '%s' on form '%s' in"
                                        " context %d does not contain the"
                                        " error '%s' (actual errors: %s)" %
                                            (field, form, i, err,
                                             repr(field_errors)))
                    elif field in context[form].fields:
                        self.fail("The field '%s' on form '%s' in context %d"
                                  " contains no errors" % (field, form, i))
                    else:
                        self.fail("The form '%s' in context %d does not"
                                  " contain the field '%s'" %
                                      (form, i, field))
                else:
                    non_field_errors = context[form].non_field_errors()
                    self.failUnless(err in non_field_errors,
                        "The form '%s' in context %d does not contain the"
                        " non-field error '%s' (actual errors: %s)" %
                            (form, i, err, non_field_errors))
        if not found_form:
            self.fail("The form '%s' was not used to render the response" %
                          form)

    def assertTemplateUsed(self, response, template_name):
        """
        Asserts that the template with the provided name was used in rendering
        the response.
        """
        template_names = [t.name for t in to_list(response.template)]
        if not template_names:
            self.fail('No templates used to render the response')
        self.failUnless(template_name in template_names,
            (u"Template '%s' was not a template used to render the response."
             u" Actual template(s) used: %s") % (template_name,
                                                 u', '.join(template_names)))

    def assertTemplateNotUsed(self, response, template_name):
        """
        Asserts that the template with the provided name was NOT used in
        rendering the response.
        """
        template_names = [t.name for t in to_list(response.template)]
        self.failIf(template_name in template_names,
            (u"Template '%s' was used unexpectedly in rendering the"
             u" response") % template_name)
