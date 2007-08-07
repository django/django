import re, unittest
from urlparse import urlparse
from django.db import transaction
from django.core import management, mail
from django.db.models import get_apps
from django.test import _doctest as doctest
from django.test.client import Client

normalize_long_ints = lambda s: re.sub(r'(?<![\w])(\d+)L(?![\w])', '\\1', s)

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
        doctest.DocTestRunner.report_unexpected_exception(self,out,test,example,exc_info)
        
        # Rollback, in case of database errors. Otherwise they'd have
        # side effects on other tests.
        from django.db import transaction
        transaction.rollback_unless_managed()

class TestCase(unittest.TestCase):    
    def _pre_setup(self):
        """Perform any pre-test setup. This includes:
        
            * If the Test Case class has a 'fixtures' member, clearing the 
            database and installing the named fixtures at the start of each test.
            * Clearing the mail test outbox.
            
        """
        management.flush(verbosity=0, interactive=False)
        if hasattr(self, 'fixtures'):
            management.load_data(self.fixtures, verbosity=0)
        mail.outbox = []

    def __call__(self, result=None):
        """
        Wrapper around default __call__ method to perform common Django test
        set up. This means that user-defined Test Cases aren't required to
        include a call to super().setUp().
        """
        self.client = Client()
        self._pre_setup()
        super(TestCase, self).__call__(result)

    def assertRedirects(self, response, expected_path, status_code=302, target_status_code=200):
        """Assert that a response redirected to a specific URL, and that the
        redirect URL can be loaded.
        
        """
        self.assertEqual(response.status_code, status_code, 
            "Response didn't redirect as expected: Response code was %d (expected %d)" % 
                (response.status_code, status_code))
        scheme, netloc, path, params, query, fragment = urlparse(response['Location'])
        self.assertEqual(path, expected_path, 
            "Response redirected to '%s', expected '%s'" % (path, expected_path))
        redirect_response = self.client.get(path)
        self.assertEqual(redirect_response.status_code, target_status_code, 
            "Couldn't retrieve redirection page '%s': response code was %d (expected %d)" % 
                (path, redirect_response.status_code, target_status_code))
    
    def assertContains(self, response, text, count=None, status_code=200):
        """Assert that a response indicates that a page was retreived successfully,
        (i.e., the HTTP status code was as expected), and that ``text`` occurs ``count``
        times in the content of the response. If ``count`` is None, the count doesn't
        matter - the assertion is true if the text occurs at least once in the response.
        
        """
        self.assertEqual(response.status_code, status_code,
            "Couldn't retrieve page: Response code was %d (expected %d)'" % 
                (response.status_code, status_code))
        real_count = response.content.count(text)
        if count is not None:
            self.assertEqual(real_count, count,
                "Found %d instances of '%s' in response (expected %d)" % (real_count, text, count))
        else:
            self.assertTrue(real_count != 0, "Couldn't find '%s' in response" % text)
                
    def assertFormError(self, response, form, field, errors):
        "Assert that a form used to render the response has a specific field error"
        if not response.context:
            self.fail('Response did not use any contexts to render the response')

        # If there is a single context, put it into a list to simplify processing
        if not isinstance(response.context, list):
            contexts = [response.context]
        else:
            contexts = response.context

        # If a single error string is provided, make it a list to simplify processing
        if not isinstance(errors, list):
            errors = [errors]
        
        # Search all contexts for the error.
        found_form = False
        for i,context in enumerate(contexts):
            if form in context:
                found_form = True
                for err in errors:
                    if field:
                        if field in context[form].errors:
                            self.failUnless(err in context[form].errors[field], 
                            "The field '%s' on form '%s' in context %d does not contain the error '%s' (actual errors: %s)" % 
                                (field, form, i, err, list(context[form].errors[field])))
                        elif field in context[form].fields:
                            self.fail("The field '%s' on form '%s' in context %d contains no errors" % 
                                (field, form, i))
                        else:
                            self.fail("The form '%s' in context %d does not contain the field '%s'" % (form, i, field))
                    else:
                        self.failUnless(err in context[form].non_field_errors(), 
                            "The form '%s' in context %d does not contain the non-field error '%s' (actual errors: %s)" % 
                                (form, i, err, list(context[form].non_field_errors())))
        if not found_form:
            self.fail("The form '%s' was not used to render the response" % form)
            
    def assertTemplateUsed(self, response, template_name):
        "Assert that the template with the provided name was used in rendering the response"
        if isinstance(response.template, list):
            template_names = [t.name for t in response.template]
            self.failUnless(template_name in template_names,
                u"Template '%s' was not one of the templates used to render the response. Templates used: %s" %
                    (template_name, u', '.join(template_names)))
        elif response.template:
            self.assertEqual(template_name, response.template.name,
                u"Template '%s' was not used to render the response. Actual template was '%s'" %
                    (template_name, response.template.name))
        else:
            self.fail('No templates used to render the response')

    def assertTemplateNotUsed(self, response, template_name):
        "Assert that the template with the provided name was NOT used in rendering the response"
        if isinstance(response.template, list):            
            self.failIf(template_name in [t.name for t in response.template],
                u"Template '%s' was used unexpectedly in rendering the response" % template_name)
        elif response.template:
            self.assertNotEqual(template_name, response.template.name,
                u"Template '%s' was used unexpectedly in rendering the response" % template_name)

