from __future__ import unicode_literals

from copy import copy
import difflib
import errno
from functools import wraps
import json
import os
import re
import sys
try:
    from urllib.parse import urlsplit, urlunsplit
except ImportError:     # Python 2
    from urlparse import urlsplit, urlunsplit
import select
import socket
import threading
import warnings

from django.conf import settings
from django.contrib.staticfiles.handlers import StaticFilesHandler
from django.core import mail
from django.core.exceptions import ValidationError, ImproperlyConfigured
from django.core.handlers.wsgi import WSGIHandler
from django.core.management import call_command
from django.core.management.color import no_style
from django.core.signals import request_started
from django.core.servers.basehttp import (WSGIRequestHandler, WSGIServer,
    WSGIServerException)
from django.core.urlresolvers import clear_url_caches
from django.core.validators import EMPTY_VALUES
from django.db import (transaction, connection, connections, DEFAULT_DB_ALIAS,
    reset_queries)
from django.forms.fields import CharField
from django.http import QueryDict
from django.test import _doctest as doctest
from django.test.client import Client
from django.test.html import HTMLParseError, parse_html
from django.test.signals import template_rendered
from django.test.utils import (override_settings, compare_xml, strip_quotes)
from django.test.utils import ContextList
from django.utils import unittest as ut2
from django.utils.encoding import force_text
from django.utils import six
from django.utils.unittest.util import safe_repr
from django.utils.unittest import skipIf
from django.views.static import serve

__all__ = ('DocTestRunner', 'OutputChecker', 'TestCase', 'TransactionTestCase',
           'SimpleTestCase', 'skipIfDBFeature', 'skipUnlessDBFeature')

normalize_long_ints = lambda s: re.sub(r'(?<![\w])(\d+)L(?![\w])', '\\1', s)
normalize_decimals = lambda s: re.sub(r"Decimal\('(\d+(\.\d*)?)'\)",
                                lambda m: "Decimal(\"%s\")" % m.groups()[0], s)


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
real_abort = transaction.abort

def nop(*args, **kwargs):
    return

def disable_transaction_methods():
    transaction.commit = nop
    transaction.rollback = nop
    transaction.enter_transaction_management = nop
    transaction.leave_transaction_management = nop
    transaction.managed = nop
    transaction.abort = nop

def restore_transaction_methods():
    transaction.commit = real_commit
    transaction.rollback = real_rollback
    transaction.enter_transaction_management = real_enter_transaction_management
    transaction.leave_transaction_management = real_leave_transaction_management
    transaction.managed = real_managed
    transaction.abort = real_abort


def assert_and_parse_html(self, html, user_msg, msg):
    try:
        dom = parse_html(html)
    except HTMLParseError as e:
        standardMsg = '%s\n%s' % (msg, e.msg)
        self.fail(self._formatMessage(user_msg, standardMsg))
    return dom


class OutputChecker(doctest.OutputChecker):
    def check_output(self, want, got, optionflags):
        """
        The entry method for doctest output checking. Defers to a sequence of
        child checkers
        """
        checks = (self.check_output_default,
                  self.check_output_numeric,
                  self.check_output_xml,
                  self.check_output_json)
        for check in checks:
            if check(want, got, optionflags):
                return True
        return False

    def check_output_default(self, want, got, optionflags):
        """
        The default comparator provided by doctest - not perfect, but good for
        most purposes
        """
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
        try:
            return compare_xml(want, got)
        except Exception:
            return False

    def check_output_json(self, want, got, optionsflags):
        """
        Tries to compare want and got as if they were JSON-encoded data
        """
        want, got = strip_quotes(want, got)
        try:
            want_json = json.loads(want)
            got_json = json.loads(got)
        except Exception:
            return False
        return want_json == got_json


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
        request_started.disconnect(reset_queries)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.connection.use_debug_cursor = self.old_debug_cursor
        request_started.connect(reset_queries)
        if exc_type is not None:
            return

        final_queries = len(self.connection.queries)
        executed = final_queries - self.starting_queries

        self.test_case.assertEqual(
            executed, self.num, "%d queries executed, %d expected" % (
                executed, self.num
            )
        )


class _AssertTemplateUsedContext(object):
    def __init__(self, test_case, template_name):
        self.test_case = test_case
        self.template_name = template_name
        self.rendered_templates = []
        self.rendered_template_names = []
        self.context = ContextList()

    def on_template_render(self, sender, signal, template, context, **kwargs):
        self.rendered_templates.append(template)
        self.rendered_template_names.append(template.name)
        self.context.append(copy(context))

    def test(self):
        return self.template_name in self.rendered_template_names

    def message(self):
        return '%s was not rendered.' % self.template_name

    def __enter__(self):
        template_rendered.connect(self.on_template_render)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        template_rendered.disconnect(self.on_template_render)
        if exc_type is not None:
            return

        if not self.test():
            message = self.message()
            if len(self.rendered_templates) == 0:
                message += ' No template was rendered.'
            else:
                message += ' Following templates were rendered: %s' % (
                    ', '.join(self.rendered_template_names))
            self.test_case.fail(message)


class _AssertTemplateNotUsedContext(_AssertTemplateUsedContext):
    def test(self):
        return self.template_name not in self.rendered_template_names

    def message(self):
        return '%s was rendered.' % self.template_name


class SimpleTestCase(ut2.TestCase):

    _warn_txt = ("save_warnings_state/restore_warnings_state "
        "django.test.*TestCase methods are deprecated. Use Python's "
        "warnings.catch_warnings context manager instead.")

    def __call__(self, result=None):
        """
        Wrapper around default __call__ method to perform common Django test
        set up. This means that user-defined Test Cases aren't required to
        include a call to super().setUp().
        """
        testMethod = getattr(self, self._testMethodName)
        skipped = (getattr(self.__class__, "__unittest_skip__", False) or
            getattr(testMethod, "__unittest_skip__", False))

        if not skipped:
            try:
                self._pre_setup()
            except (KeyboardInterrupt, SystemExit):
                raise
            except Exception:
                result.addError(self, sys.exc_info())
                return
        super(SimpleTestCase, self).__call__(result)
        if not skipped:
            try:
                self._post_teardown()
            except (KeyboardInterrupt, SystemExit):
                raise
            except Exception:
                result.addError(self, sys.exc_info())
                return

    def _pre_setup(self):
        pass

    def _post_teardown(self):
        pass

    def save_warnings_state(self):
        """
        Saves the state of the warnings module
        """
        warnings.warn(self._warn_txt, DeprecationWarning, stacklevel=2)
        self._warnings_state = warnings.filters[:]

    def restore_warnings_state(self):
        """
        Restores the state of the warnings module to the state
        saved by save_warnings_state()
        """
        warnings.warn(self._warn_txt, DeprecationWarning, stacklevel=2)
        warnings.filters = self._warnings_state[:]

    def settings(self, **kwargs):
        """
        A context manager that temporarily sets a setting and reverts
        back to the original value when exiting the context.
        """
        return override_settings(**kwargs)

    def assertRaisesMessage(self, expected_exception, expected_message,
                           callable_obj=None, *args, **kwargs):
        """
        Asserts that the message in a raised exception matches the passed
        value.

        Args:
            expected_exception: Exception class expected to be raised.
            expected_message: expected error message string value.
            callable_obj: Function to be called.
            args: Extra args.
            kwargs: Extra kwargs.
        """
        return six.assertRaisesRegex(self, expected_exception,
                re.escape(expected_message), callable_obj, *args, **kwargs)

    def assertFieldOutput(self, fieldclass, valid, invalid, field_args=None,
            field_kwargs=None, empty_value=''):
        """
        Asserts that a form field behaves correctly with various inputs.

        Args:
            fieldclass: the class of the field to be tested.
            valid: a dictionary mapping valid inputs to their expected
                    cleaned values.
            invalid: a dictionary mapping invalid inputs to one or more
                    raised error messages.
            field_args: the args passed to instantiate the field
            field_kwargs: the kwargs passed to instantiate the field
            empty_value: the expected clean output for inputs in EMPTY_VALUES

        """
        if field_args is None:
            field_args = []
        if field_kwargs is None:
            field_kwargs = {}
        required = fieldclass(*field_args, **field_kwargs)
        optional = fieldclass(*field_args,
                              **dict(field_kwargs, required=False))
        # test valid inputs
        for input, output in valid.items():
            self.assertEqual(required.clean(input), output)
            self.assertEqual(optional.clean(input), output)
        # test invalid inputs
        for input, errors in invalid.items():
            with self.assertRaises(ValidationError) as context_manager:
                required.clean(input)
            self.assertEqual(context_manager.exception.messages, errors)

            with self.assertRaises(ValidationError) as context_manager:
                optional.clean(input)
            self.assertEqual(context_manager.exception.messages, errors)
        # test required inputs
        error_required = [force_text(required.error_messages['required'])]
        for e in EMPTY_VALUES:
            with self.assertRaises(ValidationError) as context_manager:
                required.clean(e)
            self.assertEqual(context_manager.exception.messages,
                             error_required)
            self.assertEqual(optional.clean(e), empty_value)
        # test that max_length and min_length are always accepted
        if issubclass(fieldclass, CharField):
            field_kwargs.update({'min_length':2, 'max_length':20})
            self.assertTrue(isinstance(fieldclass(*field_args, **field_kwargs),
                                       fieldclass))

    def assertHTMLEqual(self, html1, html2, msg=None):
        """
        Asserts that two HTML snippets are semantically the same.
        Whitespace in most cases is ignored, and attribute ordering is not
        significant. The passed-in arguments must be valid HTML.
        """
        dom1 = assert_and_parse_html(self, html1, msg,
            'First argument is not valid HTML:')
        dom2 = assert_and_parse_html(self, html2, msg,
            'Second argument is not valid HTML:')

        if dom1 != dom2:
            standardMsg = '%s != %s' % (
                safe_repr(dom1, True), safe_repr(dom2, True))
            diff = ('\n' + '\n'.join(difflib.ndiff(
                           six.text_type(dom1).splitlines(),
                           six.text_type(dom2).splitlines())))
            standardMsg = self._truncateMessage(standardMsg, diff)
            self.fail(self._formatMessage(msg, standardMsg))

    def assertHTMLNotEqual(self, html1, html2, msg=None):
        """Asserts that two HTML snippets are not semantically equivalent."""
        dom1 = assert_and_parse_html(self, html1, msg,
            'First argument is not valid HTML:')
        dom2 = assert_and_parse_html(self, html2, msg,
            'Second argument is not valid HTML:')

        if dom1 == dom2:
            standardMsg = '%s == %s' % (
                safe_repr(dom1, True), safe_repr(dom2, True))
            self.fail(self._formatMessage(msg, standardMsg))

    def assertInHTML(self, needle, haystack, count = None, msg_prefix=''):
        needle = assert_and_parse_html(self, needle, None,
            'First argument is not valid HTML:')
        haystack = assert_and_parse_html(self, haystack, None,
            'Second argument is not valid HTML:')
        real_count = haystack.count(needle)
        if count is not None:
            self.assertEqual(real_count, count,
                msg_prefix + "Found %d instances of '%s' in response"
                " (expected %d)" % (real_count, needle, count))
        else:
            self.assertTrue(real_count != 0,
                msg_prefix + "Couldn't find '%s' in response" % needle)

    def assertJSONEqual(self, raw, expected_data, msg=None):
        try:
            data = json.loads(raw)
        except ValueError:
            self.fail("First argument is not valid JSON: %r" % raw)
        if isinstance(expected_data, six.string_types):
            try:
                expected_data = json.loads(expected_data)
            except ValueError:
                self.fail("Second argument is not valid JSON: %r" % expected_data)
        self.assertEqual(data, expected_data, msg=msg)

    def assertXMLEqual(self, xml1, xml2, msg=None):
        """
        Asserts that two XML snippets are semantically the same.
        Whitespace in most cases is ignored, and attribute ordering is not
        significant. The passed-in arguments must be valid XML.
        """
        try:
            result = compare_xml(xml1, xml2)
        except Exception as e:
            standardMsg = 'First or second argument is not valid XML\n%s' % e
            self.fail(self._formatMessage(msg, standardMsg))
        else:
            if not result:
                standardMsg = '%s != %s' % (safe_repr(xml1, True), safe_repr(xml2, True))
                self.fail(self._formatMessage(msg, standardMsg))

    def assertXMLNotEqual(self, xml1, xml2, msg=None):
        """
        Asserts that two XML snippets are not semantically equivalent.
        Whitespace in most cases is ignored, and attribute ordering is not
        significant. The passed-in arguments must be valid XML.
        """
        try:
            result = compare_xml(xml1, xml2)
        except Exception as e:
            standardMsg = 'First or second argument is not valid XML\n%s' % e
            self.fail(self._formatMessage(msg, standardMsg))
        else:
            if result:
                standardMsg = '%s == %s' % (safe_repr(xml1, True), safe_repr(xml2, True))
                self.fail(self._formatMessage(msg, standardMsg))


class TransactionTestCase(SimpleTestCase):

    # The class we'll use for the test client self.client.
    # Can be overridden in derived classes.
    client_class = Client

    # Subclasses can ask for resetting of auto increment sequence before each
    # test case
    reset_sequences = False

    def _pre_setup(self):
        """Performs any pre-test setup. This includes:

            * Flushing the database.
            * If the Test Case class has a 'fixtures' member, installing the
              named fixtures.
            * If the Test Case class has a 'urls' member, replace the
              ROOT_URLCONF with it.
            * Clearing the mail test outbox.
        """
        self.client = self.client_class()
        self._fixture_setup()
        self._urlconf_setup()
        mail.outbox = []

    def _databases_names(self, include_mirrors=True):
        # If the test case has a multi_db=True flag, act on all databases,
        # including mirrors or not. Otherwise, just on the default DB.
        if getattr(self, 'multi_db', False):
            return [alias for alias in connections
                    if include_mirrors or not connections[alias].settings_dict['TEST_MIRROR']]
        else:
            return [DEFAULT_DB_ALIAS]

    def _reset_sequences(self, db_name):
        conn = connections[db_name]
        if conn.features.supports_sequence_reset:
            sql_list = \
                conn.ops.sequence_reset_by_name_sql(no_style(),
                                                    conn.introspection.sequence_list())
            if sql_list:
                try:
                    cursor = conn.cursor()
                    for sql in sql_list:
                        cursor.execute(sql)
                except Exception:
                    transaction.rollback_unless_managed(using=db_name)
                    raise
                transaction.commit_unless_managed(using=db_name)

    def _fixture_setup(self):
        for db_name in self._databases_names(include_mirrors=False):
            # Reset sequences
            if self.reset_sequences:
                self._reset_sequences(db_name)

            if hasattr(self, 'fixtures'):
                # We have to use this slightly awkward syntax due to the fact
                # that we're using *args and **kwargs together.
                call_command('loaddata', *self.fixtures,
                             **{'verbosity': 0, 'database': db_name, 'skip_validation': True})

    def _urlconf_setup(self):
        if hasattr(self, 'urls'):
            self._old_root_urlconf = settings.ROOT_URLCONF
            settings.ROOT_URLCONF = self.urls
            clear_url_caches()

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
        for conn in connections.all():
            conn.close()

    def _fixture_teardown(self):
        # Roll back any pending transactions in order to avoid a deadlock
        # during flush when TEST_MIRROR is used (#18984).
        for conn in connections.all():
            conn.rollback_unless_managed()

        for db in self._databases_names(include_mirrors=False):
            call_command('flush', verbosity=0, interactive=False, database=db,
                         skip_validation=True, reset_sequences=False)

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
            self.assertTrue(len(response.redirect_chain) > 0,
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

            url = response.url
            scheme, netloc, path, query, fragment = urlsplit(url)

            redirect_response = response.client.get(path, QueryDict(query))

            # Get the redirection page, using the same client that was used
            # to obtain the original response.
            self.assertEqual(redirect_response.status_code, target_status_code,
                msg_prefix + "Couldn't retrieve redirection page '%s':"
                " response code was %d (expected %d)" %
                    (path, redirect_response.status_code, target_status_code))

        e_scheme, e_netloc, e_path, e_query, e_fragment = urlsplit(
                                                              expected_url)
        if not (e_scheme or e_netloc):
            expected_url = urlunsplit(('http', host or 'testserver', e_path,
                e_query, e_fragment))

        self.assertEqual(url, expected_url,
            msg_prefix + "Response redirected to '%s', expected '%s'" %
                (url, expected_url))

    def assertContains(self, response, text, count=None, status_code=200,
                       msg_prefix='', html=False):
        """
        Asserts that a response indicates that some content was retrieved
        successfully, (i.e., the HTTP status code was as expected), and that
        ``text`` occurs ``count`` times in the content of the response.
        If ``count`` is None, the count doesn't matter - the assertion is true
        if the text occurs at least once in the response.
        """

        # If the response supports deferred rendering and hasn't been rendered
        # yet, then ensure that it does get rendered before proceeding further.
        if (hasattr(response, 'render') and callable(response.render)
            and not response.is_rendered):
            response.render()

        if msg_prefix:
            msg_prefix += ": "

        self.assertEqual(response.status_code, status_code,
            msg_prefix + "Couldn't retrieve content: Response code was %d"
            " (expected %d)" % (response.status_code, status_code))
        text = force_text(text, encoding=response._charset)
        if response.streaming:
            content = b''.join(response.streaming_content)
        else:
            content = response.content
        content = content.decode(response._charset)
        if html:
            content = assert_and_parse_html(self, content, None,
                "Response's content is not valid HTML:")
            text = assert_and_parse_html(self, text, None,
                "Second argument is not valid HTML:")
        real_count = content.count(text)
        if count is not None:
            self.assertEqual(real_count, count,
                msg_prefix + "Found %d instances of '%s' in response"
                " (expected %d)" % (real_count, text, count))
        else:
            self.assertTrue(real_count != 0,
                msg_prefix + "Couldn't find '%s' in response" % text)

    def assertNotContains(self, response, text, status_code=200,
                          msg_prefix='', html=False):
        """
        Asserts that a response indicates that some content was retrieved
        successfully, (i.e., the HTTP status code was as expected), and that
        ``text`` doesn't occurs in the content of the response.
        """

        # If the response supports deferred rendering and hasn't been rendered
        # yet, then ensure that it does get rendered before proceeding further.
        if (hasattr(response, 'render') and callable(response.render)
            and not response.is_rendered):
            response.render()

        if msg_prefix:
            msg_prefix += ": "

        self.assertEqual(response.status_code, status_code,
            msg_prefix + "Couldn't retrieve content: Response code was %d"
            " (expected %d)" % (response.status_code, status_code))
        text = force_text(text, encoding=response._charset)
        content = response.content.decode(response._charset)
        if html:
            content = assert_and_parse_html(self, content, None,
                'Response\'s content is not valid HTML:')
            text = assert_and_parse_html(self, text, None,
                'Second argument is not valid HTML:')
        self.assertEqual(content.count(text), 0,
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
                        self.assertTrue(err in field_errors,
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
                    self.assertTrue(err in non_field_errors,
                        msg_prefix + "The form '%s' in context %d does not"
                        " contain the non-field error '%s'"
                        " (actual errors: %s)" %
                            (form, i, err, non_field_errors))
        if not found_form:
            self.fail(msg_prefix + "The form '%s' was not used to render the"
                      " response" % form)

    def assertTemplateUsed(self, response=None, template_name=None, msg_prefix=''):
        """
        Asserts that the template with the provided name was used in rendering
        the response. Also usable as context manager.
        """
        if response is None and template_name is None:
            raise TypeError('response and/or template_name argument must be provided')

        if msg_prefix:
            msg_prefix += ": "

        # Use assertTemplateUsed as context manager.
        if not hasattr(response, 'templates') or (response is None and template_name):
            if response:
                template_name = response
                response = None
            context = _AssertTemplateUsedContext(self, template_name)
            return context

        template_names = [t.name for t in response.templates]
        if not template_names:
            self.fail(msg_prefix + "No templates used to render the response")
        self.assertTrue(template_name in template_names,
            msg_prefix + "Template '%s' was not a template used to render"
            " the response. Actual template(s) used: %s" %
                (template_name, ', '.join(template_names)))

    def assertTemplateNotUsed(self, response=None, template_name=None, msg_prefix=''):
        """
        Asserts that the template with the provided name was NOT used in
        rendering the response. Also usable as context manager.
        """
        if response is None and template_name is None:
            raise TypeError('response and/or template_name argument must be provided')

        if msg_prefix:
            msg_prefix += ": "

        # Use assertTemplateUsed as context manager.
        if not hasattr(response, 'templates') or (response is None and template_name):
            if response:
                template_name = response
                response = None
            context = _AssertTemplateNotUsedContext(self, template_name)
            return context

        template_names = [t.name for t in response.templates]
        self.assertFalse(template_name in template_names,
            msg_prefix + "Template '%s' was used unexpectedly in rendering"
            " the response" % template_name)

    def assertQuerysetEqual(self, qs, values, transform=repr, ordered=True):
        items = six.moves.map(transform, qs)
        if not ordered:
            return self.assertEqual(set(items), set(values))
        values = list(values)
        # For example qs.iterator() could be passed as qs, but it does not
        # have 'ordered' attribute.
        if len(values) > 1 and hasattr(qs, 'ordered') and not qs.ordered:
            raise ValueError("Trying to compare non-ordered queryset "
                             "against more than one ordered values")
        return self.assertEqual(list(items), values)

    def assertNumQueries(self, num, func=None, *args, **kwargs):
        using = kwargs.pop("using", DEFAULT_DB_ALIAS)
        conn = connections[using]

        context = _AssertNumQueriesContext(self, num, conn)
        if func is None:
            return context

        with context:
            func(*args, **kwargs)


def connections_support_transactions():
    """
    Returns True if all connections support transactions.
    """
    return all(conn.features.supports_transactions
               for conn in connections.all())


class TestCase(TransactionTestCase):
    """
    Does basically the same as TransactionTestCase, but surrounds every test
    with a transaction, monkey-patches the real transaction management routines
    to do nothing, and rollsback the test transaction at the end of the test.
    You have to use TransactionTestCase, if you need transaction management
    inside a test.
    """

    def _fixture_setup(self):
        if not connections_support_transactions():
            return super(TestCase, self)._fixture_setup()

        assert not self.reset_sequences, 'reset_sequences cannot be used on TestCase instances'

        for db_name in self._databases_names():
            transaction.enter_transaction_management(using=db_name)
            transaction.managed(True, using=db_name)
        disable_transaction_methods()

        from django.contrib.sites.models import Site
        Site.objects.clear_cache()

        for db in self._databases_names(include_mirrors=False):
            if hasattr(self, 'fixtures'):
                call_command('loaddata', *self.fixtures,
                             **{
                                'verbosity': 0,
                                'commit': False,
                                'database': db,
                                'skip_validation': True,
                             })

    def _fixture_teardown(self):
        if not connections_support_transactions():
            return super(TestCase, self)._fixture_teardown()

        restore_transaction_methods()
        for db in self._databases_names():
            transaction.rollback(using=db)
            transaction.leave_transaction_management(using=db)


def _deferredSkip(condition, reason):
    def decorator(test_func):
        if not (isinstance(test_func, type) and
                issubclass(test_func, TestCase)):
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
    """
    Skip a test if a database has the named feature
    """
    return _deferredSkip(lambda: getattr(connection.features, feature),
                         "Database has feature %s" % feature)


def skipUnlessDBFeature(feature):
    """
    Skip a test unless a database has the named feature
    """
    return _deferredSkip(lambda: not getattr(connection.features, feature),
                         "Database doesn't support feature %s" % feature)


class QuietWSGIRequestHandler(WSGIRequestHandler):
    """
    Just a regular WSGIRequestHandler except it doesn't log to the standard
    output any of the requests received, so as to not clutter the output for
    the tests' results.
    """

    def log_message(*args):
        pass


if sys.version_info >= (3, 3, 0):
    _ImprovedEvent = threading.Event
elif sys.version_info >= (2, 7, 0):
    _ImprovedEvent = threading._Event
else:
    class _ImprovedEvent(threading._Event):
        """
        Does the same as `threading.Event` except it overrides the wait() method
        with some code borrowed from Python 2.7 to return the set state of the
        event (see: http://hg.python.org/cpython/rev/b5aa8aa78c0f/). This allows
        to know whether the wait() method exited normally or because of the
        timeout. This class can be removed when Django supports only Python >= 2.7.
        """

        def wait(self, timeout=None):
            self._Event__cond.acquire()
            try:
                if not self._Event__flag:
                    self._Event__cond.wait(timeout)
                return self._Event__flag
            finally:
                self._Event__cond.release()


class StoppableWSGIServer(WSGIServer):
    """
    The code in this class is borrowed from the `SocketServer.BaseServer` class
    in Python 2.6. The important functionality here is that the server is non-
    blocking and that it can be shut down at any moment. This is made possible
    by the server regularly polling the socket and checking if it has been
    asked to stop.
    Note for the future: Once Django stops supporting Python 2.6, this class
    can be removed as `WSGIServer` will have this ability to shutdown on
    demand and will not require the use of the _ImprovedEvent class whose code
    is borrowed from Python 2.7.
    """

    def __init__(self, *args, **kwargs):
        super(StoppableWSGIServer, self).__init__(*args, **kwargs)
        self.__is_shut_down = _ImprovedEvent()
        self.__serving = False

    def serve_forever(self, poll_interval=0.5):
        """
        Handle one request at a time until shutdown.

        Polls for shutdown every poll_interval seconds.
        """
        self.__serving = True
        self.__is_shut_down.clear()
        while self.__serving:
            r, w, e = select.select([self], [], [], poll_interval)
            if r:
                self._handle_request_noblock()
        self.__is_shut_down.set()

    def shutdown(self):
        """
        Stops the serve_forever loop.

        Blocks until the loop has finished. This must be called while
        serve_forever() is running in another thread, or it will
        deadlock.
        """
        self.__serving = False
        if not self.__is_shut_down.wait(2):
            raise RuntimeError(
                "Failed to shutdown the live test server in 2 seconds. The "
                "server might be stuck or generating a slow response.")

    def handle_request(self):
        """Handle one request, possibly blocking.
        """
        fd_sets = select.select([self], [], [], None)
        if not fd_sets[0]:
            return
        self._handle_request_noblock()

    def _handle_request_noblock(self):
        """
        Handle one request, without blocking.

        I assume that select.select has returned that the socket is
        readable before this function was called, so there should be
        no risk of blocking in get_request().
        """
        try:
            request, client_address = self.get_request()
        except socket.error:
            return
        if self.verify_request(request, client_address):
            try:
                self.process_request(request, client_address)
            except Exception:
                self.handle_error(request, client_address)
                self.close_request(request)


class _MediaFilesHandler(StaticFilesHandler):
    """
    Handler for serving the media files. This is a private class that is
    meant to be used solely as a convenience by LiveServerThread.
    """

    def get_base_dir(self):
        return settings.MEDIA_ROOT

    def get_base_url(self):
        return settings.MEDIA_URL

    def serve(self, request):
        relative_url = request.path[len(self.base_url[2]):]
        return serve(request, relative_url, document_root=self.get_base_dir())


class LiveServerThread(threading.Thread):
    """
    Thread for running a live http server while the tests are running.
    """

    def __init__(self, host, possible_ports, connections_override=None):
        self.host = host
        self.port = None
        self.possible_ports = possible_ports
        self.is_ready = threading.Event()
        self.error = None
        self.connections_override = connections_override
        super(LiveServerThread, self).__init__()

    def run(self):
        """
        Sets up the live server and databases, and then loops over handling
        http requests.
        """
        if self.connections_override:
            from django.db import connections
            # Override this thread's database connections with the ones
            # provided by the main thread.
            for alias, conn in self.connections_override.items():
                connections[alias] = conn
        try:
            # Create the handler for serving static and media files
            handler = StaticFilesHandler(_MediaFilesHandler(WSGIHandler()))

            # Go through the list of possible ports, hoping that we can find
            # one that is free to use for the WSGI server.
            for index, port in enumerate(self.possible_ports):
                try:
                    self.httpd = StoppableWSGIServer(
                        (self.host, port), QuietWSGIRequestHandler)
                except WSGIServerException as e:
                    if (index + 1 < len(self.possible_ports) and
                        hasattr(e.args[0], 'errno') and
                        e.args[0].errno == errno.EADDRINUSE):
                        # This port is already in use, so we go on and try with
                        # the next one in the list.
                        continue
                    else:
                        # Either none of the given ports are free or the error
                        # is something else than "Address already in use". So
                        # we let that error bubble up to the main thread.
                        raise
                else:
                    # A free port was found.
                    self.port = port
                    break

            self.httpd.set_app(handler)
            self.is_ready.set()
            self.httpd.serve_forever()
        except Exception as e:
            self.error = e
            self.is_ready.set()

    def join(self, timeout=None):
        if hasattr(self, 'httpd'):
            # Stop the WSGI server
            self.httpd.shutdown()
            self.httpd.server_close()
        super(LiveServerThread, self).join(timeout)


class LiveServerTestCase(TransactionTestCase):
    """
    Does basically the same as TransactionTestCase but also launches a live
    http server in a separate thread so that the tests may use another testing
    framework, such as Selenium for example, instead of the built-in dummy
    client.
    Note that it inherits from TransactionTestCase instead of TestCase because
    the threads do not share the same transactions (unless if using in-memory
    sqlite) and each thread needs to commit all their transactions so that the
    other thread can see the changes.
    """

    @property
    def live_server_url(self):
        return 'http://%s:%s' % (
            self.server_thread.host, self.server_thread.port)

    @classmethod
    def setUpClass(cls):
        connections_override = {}
        for conn in connections.all():
            # If using in-memory sqlite databases, pass the connections to
            # the server thread.
            if (conn.settings_dict['ENGINE'].rsplit('.', 1)[-1] in ('sqlite3', 'spatialite')
                and conn.settings_dict['NAME'] == ':memory:'):
                # Explicitly enable thread-shareability for this connection
                conn.allow_thread_sharing = True
                connections_override[conn.alias] = conn

        # Launch the live server's thread
        specified_address = os.environ.get(
            'DJANGO_LIVE_TEST_SERVER_ADDRESS', 'localhost:8081')

        # The specified ports may be of the form '8000-8010,8080,9200-9300'
        # i.e. a comma-separated list of ports or ranges of ports, so we break
        # it down into a detailed list of all possible ports.
        possible_ports = []
        try:
            host, port_ranges = specified_address.split(':')
            for port_range in port_ranges.split(','):
                # A port range can be of either form: '8000' or '8000-8010'.
                extremes = list(map(int, port_range.split('-')))
                assert len(extremes) in [1, 2]
                if len(extremes) == 1:
                    # Port range of the form '8000'
                    possible_ports.append(extremes[0])
                else:
                    # Port range of the form '8000-8010'
                    for port in range(extremes[0], extremes[1] + 1):
                        possible_ports.append(port)
        except Exception:
            raise ImproperlyConfigured('Invalid address ("%s") for live '
                'server.' % specified_address)
        cls.server_thread = LiveServerThread(
            host, possible_ports, connections_override)
        cls.server_thread.daemon = True
        cls.server_thread.start()

        # Wait for the live server to be ready
        cls.server_thread.is_ready.wait()
        if cls.server_thread.error:
            raise cls.server_thread.error

        super(LiveServerTestCase, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        # There may not be a 'server_thread' attribute if setUpClass() for some
        # reasons has raised an exception.
        if hasattr(cls, 'server_thread'):
            # Terminate the live server's thread
            cls.server_thread.join()

        # Restore sqlite connections' non-sharability
        for conn in connections.all():
            if (conn.settings_dict['ENGINE'].rsplit('.', 1)[-1] in ('sqlite3', 'spatialite')
                and conn.settings_dict['NAME'] == ':memory:'):
                conn.allow_thread_sharing = False

        super(LiveServerTestCase, cls).tearDownClass()
