import re, doctest, unittest
from urlparse import urlparse
from django.db import transaction
from django.core import management
from django.db.models import get_apps
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
    def install_fixtures(self):
        """If the Test Case class has a 'fixtures' member, clear the database and
        install the named fixtures at the start of each test.
        
        """
        management.flush(verbosity=0, interactive=False)
        if hasattr(self, 'fixtures'):
            management.load_data(self.fixtures, verbosity=0)

    def run(self, result=None):
        """Wrapper around default run method so that user-defined Test Cases 
        automatically call install_fixtures without having to include a call to 
        super().
        
        """
        self.client = Client()
        self.install_fixtures()
        super(TestCase, self).run(result)

    def assertRedirects(self, response, expected_path):
        """Assert that a response redirected to a specific URL, and that the 
        redirect URL can be loaded.
        
        """
        self.assertEqual(response.status_code, 302, 
            "Response didn't redirect: Reponse code was %d" % response.status_code)
        scheme, netloc, path, params, query, fragment = urlparse(response['Location'])
        self.assertEqual(path, expected_path, 
            "Response redirected to '%s', expected '%s'" % (path, expected_path))
        redirect_response = self.client.get(path)
        self.assertEqual(redirect_response.status_code, 200, 
            "Couldn't retrieve redirection page '%s'" % path)
    
    def assertContains(self, response, text, count=1):
        """Assert that a response indicates that a page was retreived successfully,
        (i.e., the HTTP status code was 200), and that ``text`` occurs ``count`` 
        times in the content of the response.
        
        """
        self.assertEqual(response.status_code, 200,
            "Couldn't retrieve page'")
        real_count = response.content.count(text)
        self.assertEqual(real_count, count,
            "Could only find %d of %d instances of '%s' in response" % (real_count, count, text))
            