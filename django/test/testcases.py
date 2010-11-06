import re
import sys
from urlparse import urlsplit, urlunsplit
from xml.dom.minidom import parseString, Node

from django.conf import settings
from django.core import mail
from django.core.management import call_command
from django.core.urlresolvers import clear_url_caches
from django.db import transaction, connection, connections, DEFAULT_DB_ALIAS
from django.http import QueryDict
from django.test import _doctest as doctest
from django.test.client import Client
from django.utils import simplejson, unittest as ut2
from django.utils.encoding import smart_str
from django.utils.functional import wraps

__all__ = ('DocTestRunner', 'OutputChecker', 'TestCase', 'TransactionTestCase',
           'skipIfDBFeature', 'skipUnlessDBFeature')


try:
    all
except NameError:
    from django.utils.itercompat import all

normalize_long_ints = lambda s: re.sub(r'(?<![\w])(\d+)L(?![\w])', '\\1', s)
normalize_decimals = lambda s: re.sub(r"Decimal\('(\d+(\.\d*)?)'\)", lambda m: "Decimal(\"%s\")" % m.groups()[0], s)


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

real_commit = transaction.commit
real_rollback = transaction.rollback
real_enter_transaction_management = transaction.enter_transaction_management
real_leave_transaction_management = transaction.leave_transaction_management
real_managed = transaction.managed

def nop(*args, **kwargs):
    return

def disable_transaction_methods():
    transaction.commit = nop
    transaction.rollback = nop
    transaction.enter_transaction_management = nop
    transaction.leave_transaction_management = nop
    transaction.managed = nop

def restore_transaction_methods():
    transaction.commit = real_commit
    transaction.rollback = real_rollback
    transaction.enter_transaction_management = real_enter_transaction_management
    transaction.leave_transaction_management = real_leave_transaction_management
    transaction.managed = real_managed

class OutputChecker(doctest.OutputChecker):
    def check_output(self, want, got, optionflags):
        "The entry method for doctest output checking. Defers to a sequence of child checkers"
        checks = (self.check_output_default,
                  self.check_output_numeric,
                  self.check_output_xml,
                  self.check_output_json)
        for check in checks:
            if check(want, got, optionflags):
                return True
        return False

    def check_output_default(self, want, got, optionflags):
        "The default comparator provided by doctest - not perfect, but good for most purposes"
        return doctest.OutputChecker.check_output(self, want, got, optionflags)

    def check_output_numeric(self, want, got, optionflags):
        """Doctest does an exact string comparison of output, which means that
        some numerically equivalent values aren't equal. This check normalizes
         * long integers (22L) so that they equal normal integers. (22)
         * Decimals so that they are comparable, regardless of the change
           made to __repr__ in Python 2.6.
        """
        return doctest.OutputChecker.check_output(self,
            normalize_decimals(normalize_long_ints(want)),
            normalize_decimals(normalize_long_ints(got)),
            optionflags)

    def check_output_xml(self, want, got, optionsflags):
        """Tries to do a 'xml-comparision' of want and got.  Plain string
        comparision doesn't always work because, for example, attribute
        ordering should not be important.

        Based on http://codespeak.net/svn/lxml/trunk/src/lxml/doctestcompare.py
        """
        _norm_whitespace_re = re.compile(r'[ \t\n][ \t\n]+')
        def norm_whitespace(v):
            return _norm_whitespace_re.sub(' ', v)

        def child_text(element):
            return ''.join([c.data for c in element.childNodes
                            if c.nodeType == Node.TEXT_NODE])

        def children(element):
            return [c for c in element.childNodes
                    if c.nodeType == Node.ELEMENT_NODE]

        def norm_child_text(element):
            return norm_whitespace(child_text(element))

        def attrs_dict(element):
            return dict(element.attributes.items())

        def check_element(want_element, got_element):
            if want_element.tagName != got_element.tagName:
                return False
            if norm_child_text(want_element) != norm_child_text(got_element):
                return False
            if attrs_dict(want_element) != attrs_dict(got_element):
                return False
            want_children = children(want_element)
            got_children = children(got_element)
            if len(want_children) != len(got_children):
                return False
            for want, got in zip(want_children, got_children):
                if not check_element(want, got):
                    return False
            return True

        want, got = self._strip_quotes(want, got)
        want = want.replace('\\n','\n')
        got = got.replace('\\n','\n')

        # If the string is not a complete xml document, we may need to add a
        # root element. This allow us to compare fragments, like "<foo/><bar/>"
        if not want.startswith('<?xml'):
            wrapper = '<root>%s</root>'
            want = wrapper % want
            got = wrapper % got

        # Parse the want and got strings, and compare the parsings.
        try:
            want_root = parseString(want).firstChild
            got_root = parseString(got).firstChild
        except:
            return False
        return check_element(want_root, got_root)

    def check_output_json(self, want, got, optionsflags):
        "Tries to compare want and got as if they were JSON-encoded data"
        want, got = self._strip_quotes(want, got)
        try:
            want_json = simplejson.loads(want)
            got_json = simplejson.loads(got)
        except:
            return False
        return want_json == got_json

    def _strip_quotes(self, want, got):
        """
        Strip quotes of doctests output values:

        >>> o = OutputChecker()
        >>> o._strip_quotes("'foo'")
        "foo"
        >>> o._strip_quotes('"foo"')
        "foo"
        >>> o._strip_quotes("u'foo'")
        "foo"
        >>> o._strip_quotes('u"foo"')
        "foo"
        """
        def is_quoted_string(s):
            s = s.strip()
            return (len(s) >= 2
                    and s[0] == s[-1]
                    and s[0] in ('"', "'"))

        def is_quoted_unicode(s):
            s = s.strip()
            return (len(s) >= 3
                    and s[0] == 'u'
                    and s[1] == s[-1]
                    and s[1] in ('"', "'"))

        if is_quoted_string(want) and is_quoted_string(got):
            want = want.strip()[1:-1]
            got = got.strip()[1:-1]
        elif is_quoted_unicode(want) and is_quoted_unicode(got):
            want = want.strip()[2:-1]
            got = got.strip()[2:-1]
        return want, got


class DocTestRunner(doctest.DocTestRunner):
    def __init__(self, *args, **kwargs):
        doctest.DocTestRunner.__init__(self, *args, **kwargs)
        self.optionflags = doctest.ELLIPSIS

    def report_unexpected_exception(self, out, test, example, exc_info):
        doctest.DocTestRunner.report_unexpected_exception(self, out, test,
                                                          example, exc_info)
        # Rollback, in case of database errors. Otherwise they'd have
        # side effects on other tests.
        for conn in connections:
            transaction.rollback_unless_managed(using=conn)

class _AssertNumQueriesContext(object):
    def __init__(self, test_case, num, connection):
        self.test_case = test_case
        self.num = num
        self.connection = connection

    def __enter__(self):
        self.old_debug_cursor = self.connection.use_debug_cursor
        self.connection.use_debug_cursor = True
        self.starting_queries = len(self.connection.queries)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.connection.use_debug_cursor = self.old_debug_cursor
        if exc_type is not None:
            return

        final_queries = len(self.connection.queries)
        executed = final_queries - self.starting_queries

        self.test_case.assertEqual(
            executed, self.num, "%d queries executed, %d expected" % (
                executed, self.num
            )
        )


class TransactionTestCase(ut2.TestCase):
    # The class we'll use for the test client self.client.
    # Can be overridden in derived classes.
    client_class = Client

    def _pre_setup(self):
        """Performs any pre-test setup. This includes:

            * Flushing the database.
            * If the Test Case class has a 'fixtures' member, installing the
              named fixtures.
            * If the Test Case class has a 'urls' member, replace the
              ROOT_URLCONF with it.
            * Clearing the mail test outbox.
        """
        self._fixture_setup()
        self._urlconf_setup()
        mail.outbox = []

    def _fixture_setup(self):
        # If the test case has a multi_db=True flag, flush all databases.
        # Otherwise, just flush default.
        if getattr(self, 'multi_db', False):
            databases = connections
        else:
            databases = [DEFAULT_DB_ALIAS]
        for db in databases:
            call_command('flush', verbosity=0, interactive=False, database=db)

            if hasattr(self, 'fixtures'):
                # We have to use this slightly awkward syntax due to the fact
                # that we're using *args and **kwargs together.
                call_command('loaddata', *self.fixtures, **{'verbosity': 0, 'database': db})

    def _urlconf_setup(self):
        if hasattr(self, 'urls'):
            self._old_root_urlconf = settings.ROOT_URLCONF
            settings.ROOT_URLCONF = self.urls
            clear_url_caches()

    def __call__(self, result=None):
        """
        Wrapper around default __call__ method to perform common Django test
        set up. This means that user-defined Test Cases aren't required to
        include a call to super().setUp().
        """
        self.client = self.client_class()
        try:
            self._pre_setup()
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception:
            import sys
            result.addError(self, sys.exc_info())
            return
        super(TransactionTestCase, self).__call__(result)
        try:
            self._post_teardown()
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception:
            import sys
            result.addError(self, sys.exc_info())
            return

    def _post_teardown(self):
        """ Performs any post-test things. This includes:

            * Putting back the original ROOT_URLCONF if it was changed.
            * Force closing the connection, so that the next test gets
              a clean cursor.
        """
        self._fixture_teardown()
        self._urlconf_teardown()
        # Some DB cursors include SQL statements as part of cursor
        # creation. If you have a test that does rollback, the effect
        # of these statements is lost, which can effect the operation
        # of tests (e.g., losing a timezone setting causing objects to
        # be created with the wrong time).
        # To make sure this doesn't happen, get a clean connection at the
        # start of every test.
        for connection in connections.all():
            connection.close()

    def _fixture_teardown(self):
        pass

    def _urlconf_teardown(self):
        if hasattr(self, '_old_root_urlconf'):
            settings.ROOT_URLCONF = self._old_root_urlconf
            clear_url_caches()

    def assertRedirects(self, response, expected_url, status_code=302,
                        target_status_code=200, host=None, msg_prefix=''):
        """Asserts that a response redirected to a specific URL, and that the
        redirect URL can be loaded.

        Note that assertRedirects won't work for external links since it uses
        TestClient to do a request.
        """
        if msg_prefix:
            msg_prefix += ": "

        if hasattr(response, 'redirect_chain'):
            # The request was a followed redirect
            self.failUnless(len(response.redirect_chain) > 0,
                msg_prefix + "Response didn't redirect as expected: Response"
                " code was %d (expected %d)" %
                    (response.status_code, status_code))

            self.assertEqual(response.redirect_chain[0][1], status_code,
                msg_prefix + "Initial response didn't redirect as expected:"
                " Response code was %d (expected %d)" %
                    (response.redirect_chain[0][1], status_code))

            url, status_code = response.redirect_chain[-1]

            self.assertEqual(response.status_code, target_status_code,
                msg_prefix + "Response didn't redirect as expected: Final"
                " Response code was %d (expected %d)" %
                    (response.status_code, target_status_code))

        else:
            # Not a followed redirect
            self.assertEqual(response.status_code, status_code,
                msg_prefix + "Response didn't redirect as expected: Response"
                " code was %d (expected %d)" %
                    (response.status_code, status_code))

            url = response['Location']
            scheme, netloc, path, query, fragment = urlsplit(url)

            redirect_response = response.client.get(path, QueryDict(query))

            # Get the redirection page, using the same client that was used
            # to obtain the original response.
            self.assertEqual(redirect_response.status_code, target_status_code,
                msg_prefix + "Couldn't retrieve redirection page '%s':"
                " response code was %d (expected %d)" %
                    (path, redirect_response.status_code, target_status_code))

        e_scheme, e_netloc, e_path, e_query, e_fragment = urlsplit(expected_url)
        if not (e_scheme or e_netloc):
            expected_url = urlunsplit(('http', host or 'testserver', e_path,
                e_query, e_fragment))

        self.assertEqual(url, expected_url,
            msg_prefix + "Response redirected to '%s', expected '%s'" %
                (url, expected_url))

    def assertContains(self, response, text, count=None, status_code=200,
                       msg_prefix=''):
        """
        Asserts that a response indicates that some content was retrieved
        successfully, (i.e., the HTTP status code was as expected), and that
        ``text`` occurs ``count`` times in the content of the response.
        If ``count`` is None, the count doesn't matter - the assertion is true
        if the text occurs at least once in the response.
        """
        if msg_prefix:
            msg_prefix += ": "

        self.assertEqual(response.status_code, status_code,
            msg_prefix + "Couldn't retrieve content: Response code was %d"
            " (expected %d)" % (response.status_code, status_code))
        text = smart_str(text, response._charset)
        real_count = response.content.count(text)
        if count is not None:
            self.assertEqual(real_count, count,
                msg_prefix + "Found %d instances of '%s' in response"
                " (expected %d)" % (real_count, text, count))
        else:
            self.assertTrue(real_count != 0,
                msg_prefix + "Couldn't find '%s' in response" % text)

    def assertNotContains(self, response, text, status_code=200,
                          msg_prefix=''):
        """
        Asserts that a response indicates that some content was retrieved
        successfully, (i.e., the HTTP status code was as expected), and that
        ``text`` doesn't occurs in the content of the response.
        """
        if msg_prefix:
            msg_prefix += ": "

        self.assertEqual(response.status_code, status_code,
            msg_prefix + "Couldn't retrieve content: Response code was %d"
            " (expected %d)" % (response.status_code, status_code))
        text = smart_str(text, response._charset)
        self.assertEqual(response.content.count(text), 0,
            msg_prefix + "Response should not contain '%s'" % text)

    def assertFormError(self, response, form, field, errors, msg_prefix=''):
        """
        Asserts that a form used to render the response has a specific field
        error.
        """
        if msg_prefix:
            msg_prefix += ": "

        # Put context(s) into a list to simplify processing.
        contexts = to_list(response.context)
        if not contexts:
            self.fail(msg_prefix + "Response did not use any contexts to "
                      "render the response")

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
                            msg_prefix + "The field '%s' on form '%s' in"
                            " context %d does not contain the error '%s'"
                            " (actual errors: %s)" %
                                (field, form, i, err, repr(field_errors)))
                    elif field in context[form].fields:
                        self.fail(msg_prefix + "The field '%s' on form '%s'"
                                  " in context %d contains no errors" %
                                      (field, form, i))
                    else:
                        self.fail(msg_prefix + "The form '%s' in context %d"
                                  " does not contain the field '%s'" %
                                      (form, i, field))
                else:
                    non_field_errors = context[form].non_field_errors()
                    self.failUnless(err in non_field_errors,
                        msg_prefix + "The form '%s' in context %d does not"
                        " contain the non-field error '%s'"
                        " (actual errors: %s)" %
                            (form, i, err, non_field_errors))
        if not found_form:
            self.fail(msg_prefix + "The form '%s' was not used to render the"
                      " response" % form)

    def assertTemplateUsed(self, response, template_name, msg_prefix=''):
        """
        Asserts that the template with the provided name was used in rendering
        the response.
        """
        if msg_prefix:
            msg_prefix += ": "

        template_names = [t.name for t in response.templates]
        if not template_names:
            self.fail(msg_prefix + "No templates used to render the response")
        self.failUnless(template_name in template_names,
            msg_prefix + "Template '%s' was not a template used to render"
            " the response. Actual template(s) used: %s" %
                (template_name, u', '.join(template_names)))

    def assertTemplateNotUsed(self, response, template_name, msg_prefix=''):
        """
        Asserts that the template with the provided name was NOT used in
        rendering the response.
        """
        if msg_prefix:
            msg_prefix += ": "

        template_names = [t.name for t in response.templates]
        self.failIf(template_name in template_names,
            msg_prefix + "Template '%s' was used unexpectedly in rendering"
            " the response" % template_name)

    def assertQuerysetEqual(self, qs, values, transform=repr):
        return self.assertEqual(map(transform, qs), values)

    def assertNumQueries(self, num, func=None, *args, **kwargs):
        using = kwargs.pop("using", DEFAULT_DB_ALIAS)
        connection = connections[using]

        context = _AssertNumQueriesContext(self, num, connection)
        if func is None:
            return context

        # Basically emulate the `with` statement here.

        context.__enter__()
        try:
            func(*args, **kwargs)
        except:
            context.__exit__(*sys.exc_info())
            raise
        else:
            context.__exit__(*sys.exc_info())

def connections_support_transactions():
    """
    Returns True if all connections support transactions.  This is messy
    because 2.4 doesn't support any or all.
    """
    return all(conn.features.supports_transactions
        for conn in connections.all())

class TestCase(TransactionTestCase):
    """
    Does basically the same as TransactionTestCase, but surrounds every test
    with a transaction, monkey-patches the real transaction management routines to
    do nothing, and rollsback the test transaction at the end of the test. You have
    to use TransactionTestCase, if you need transaction management inside a test.
    """

    def _fixture_setup(self):
        if not connections_support_transactions():
            return super(TestCase, self)._fixture_setup()

        # If the test case has a multi_db=True flag, setup all databases.
        # Otherwise, just use default.
        if getattr(self, 'multi_db', False):
            databases = connections
        else:
            databases = [DEFAULT_DB_ALIAS]

        for db in databases:
            transaction.enter_transaction_management(using=db)
            transaction.managed(True, using=db)
        disable_transaction_methods()

        from django.contrib.sites.models import Site
        Site.objects.clear_cache()

        for db in databases:
            if hasattr(self, 'fixtures'):
                call_command('loaddata', *self.fixtures, **{
                                                            'verbosity': 0,
                                                            'commit': False,
                                                            'database': db
                                                            })

    def _fixture_teardown(self):
        if not connections_support_transactions():
            return super(TestCase, self)._fixture_teardown()

        # If the test case has a multi_db=True flag, teardown all databases.
        # Otherwise, just teardown default.
        if getattr(self, 'multi_db', False):
            databases = connections
        else:
            databases = [DEFAULT_DB_ALIAS]

        restore_transaction_methods()
        for db in databases:
            transaction.rollback(using=db)
            transaction.leave_transaction_management(using=db)

def _deferredSkip(condition, reason):
    def decorator(test_func):
        if not (isinstance(test_func, type) and issubclass(test_func, TestCase)):
            @wraps(test_func)
            def skip_wrapper(*args, **kwargs):
                if condition():
                    raise ut2.SkipTest(reason)
                return test_func(*args, **kwargs)
            test_item = skip_wrapper
        else:
            test_item = test_func
        test_item.__unittest_skip_why__ = reason
        return test_item
    return decorator

def skipIfDBFeature(feature):
    "Skip a test if a database has the named feature"
    return _deferredSkip(lambda: getattr(connection.features, feature),
                         "Database has feature %s" % feature)

def skipUnlessDBFeature(feature):
    "Skip a test unless a database has the named feature"
    return _deferredSkip(lambda: not getattr(connection.features, feature),
                         "Database doesn't support feature %s" % feature)
