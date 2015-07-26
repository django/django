from __future__ import unicode_literals

import difflib
import errno
import json
import os
import posixpath
import re
import socket
import sys
import threading
import unittest
import warnings
from collections import Counter
from copy import copy
from functools import wraps
from unittest import skipIf  # NOQA: Imported here for backward compatibility
from unittest.util import safe_repr

from django.apps import apps
from django.conf import settings
from django.core import mail
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.core.handlers.wsgi import WSGIHandler, get_path_info
from django.core.management import call_command
from django.core.management.color import no_style
from django.core.management.commands import flush
from django.core.servers.basehttp import WSGIRequestHandler, WSGIServer
from django.core.urlresolvers import clear_url_caches, set_urlconf
from django.db import DEFAULT_DB_ALIAS, connection, connections, transaction
from django.forms.fields import CharField
from django.http import QueryDict
from django.test.client import Client
from django.test.html import HTMLParseError, parse_html
from django.test.signals import setting_changed, template_rendered
from django.test.utils import (
    CaptureQueriesContext, ContextList, compare_xml, modify_settings,
    override_settings,
)
from django.utils import six
from django.utils.deprecation import RemovedInDjango110Warning
from django.utils.encoding import force_text
from django.utils.six.moves.urllib.parse import (
    unquote, urlparse, urlsplit, urlunsplit,
)
from django.utils.six.moves.urllib.request import url2pathname
from django.views.static import serve

__all__ = ('TestCase', 'TransactionTestCase',
           'SimpleTestCase', 'skipIfDBFeature', 'skipUnlessDBFeature')


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


def assert_and_parse_html(self, html, user_msg, msg):
    try:
        dom = parse_html(html)
    except HTMLParseError as e:
        standardMsg = '%s\n%s' % (msg, e.msg)
        self.fail(self._formatMessage(user_msg, standardMsg))
    return dom


class _AssertNumQueriesContext(CaptureQueriesContext):
    def __init__(self, test_case, num, connection):
        self.test_case = test_case
        self.num = num
        super(_AssertNumQueriesContext, self).__init__(connection)

    def __exit__(self, exc_type, exc_value, traceback):
        super(_AssertNumQueriesContext, self).__exit__(exc_type, exc_value, traceback)
        if exc_type is not None:
            return
        executed = len(self)
        self.test_case.assertEqual(
            executed, self.num,
            "%d queries executed, %d expected\nCaptured queries were:\n%s" % (
                executed, self.num,
                '\n'.join(
                    query['sql'] for query in self.captured_queries
                )
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


class SimpleTestCase(unittest.TestCase):

    # The class we'll use for the test client self.client.
    # Can be overridden in derived classes.
    client_class = Client
    _overridden_settings = None
    _modified_settings = None

    @classmethod
    def setUpClass(cls):
        super(SimpleTestCase, cls).setUpClass()
        if cls._overridden_settings:
            cls._cls_overridden_context = override_settings(**cls._overridden_settings)
            cls._cls_overridden_context.enable()
        if cls._modified_settings:
            cls._cls_modified_context = modify_settings(cls._modified_settings)
            cls._cls_modified_context.enable()

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, '_cls_modified_context'):
            cls._cls_modified_context.disable()
            delattr(cls, '_cls_modified_context')
        if hasattr(cls, '_cls_overridden_context'):
            cls._cls_overridden_context.disable()
            delattr(cls, '_cls_overridden_context')
        super(SimpleTestCase, cls).tearDownClass()

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
            except Exception:
                result.addError(self, sys.exc_info())
                return
        super(SimpleTestCase, self).__call__(result)
        if not skipped:
            try:
                self._post_teardown()
            except Exception:
                result.addError(self, sys.exc_info())
                return

    def _pre_setup(self):
        """Performs any pre-test setup. This includes:

        * Creating a test client.
        * If the class has a 'urls' attribute, replace ROOT_URLCONF with it.
        * Clearing the mail test outbox.
        """
        self.client = self.client_class()
        self._urlconf_setup()
        mail.outbox = []

    def _urlconf_setup(self):
        if hasattr(self, 'urls'):
            warnings.warn(
                "SimpleTestCase.urls is deprecated and will be removed in "
                "Django 1.10. Use @override_settings(ROOT_URLCONF=...) "
                "in %s instead." % self.__class__.__name__,
                RemovedInDjango110Warning, stacklevel=2)
            set_urlconf(None)
            self._old_root_urlconf = settings.ROOT_URLCONF
            settings.ROOT_URLCONF = self.urls
            clear_url_caches()

    def _post_teardown(self):
        """Performs any post-test things. This includes:

        * Putting back the original ROOT_URLCONF if it was changed.
        """
        self._urlconf_teardown()

    def _urlconf_teardown(self):
        if hasattr(self, '_old_root_urlconf'):
            set_urlconf(None)
            settings.ROOT_URLCONF = self._old_root_urlconf
            clear_url_caches()

    def settings(self, **kwargs):
        """
        A context manager that temporarily sets a setting and reverts to the original value when exiting the context.
        """
        return override_settings(**kwargs)

    def modify_settings(self, **kwargs):
        """
        A context manager that temporarily applies changes a list setting and
        reverts back to the original value when exiting the context.
        """
        return modify_settings(**kwargs)

    def assertRedirects(self, response, expected_url, status_code=302,
                        target_status_code=200, host=None, msg_prefix='',
                        fetch_redirect_response=True):
        """Asserts that a response redirected to a specific URL, and that the
        redirect URL can be loaded.

        Note that assertRedirects won't work for external links since it uses
        TestClient to do a request (use fetch_redirect_response=False to check
        such links without fetching them).
        """
        if msg_prefix:
            msg_prefix += ": "

        e_scheme, e_netloc, e_path, e_query, e_fragment = urlsplit(expected_url)

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
            scheme, netloc, path, query, fragment = urlsplit(url)

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

            if fetch_redirect_response:
                redirect_response = response.client.get(path, QueryDict(query),
                                                        secure=(scheme == 'https'))

                # Get the redirection page, using the same client that was used
                # to obtain the original response.
                self.assertEqual(redirect_response.status_code, target_status_code,
                    msg_prefix + "Couldn't retrieve redirection page '%s':"
                    " response code was %d (expected %d)" %
                        (path, redirect_response.status_code, target_status_code))

        e_scheme = e_scheme if e_scheme else scheme or 'http'
        e_netloc = e_netloc if e_netloc else host or 'testserver'
        expected_url = urlunsplit((e_scheme, e_netloc, e_path, e_query,
            e_fragment))

        self.assertEqual(url, expected_url,
            msg_prefix + "Response redirected to '%s', expected '%s'" %
                (url, expected_url))

    def _assert_contains(self, response, text, status_code, msg_prefix, html):
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

        if response.streaming:
            content = b''.join(response.streaming_content)
        else:
            content = response.content
        if not isinstance(text, bytes) or html:
            text = force_text(text, encoding=response.charset)
            content = content.decode(response.charset)
            text_repr = "'%s'" % text
        else:
            text_repr = repr(text)
        if html:
            content = assert_and_parse_html(self, content, None,
                "Response's content is not valid HTML:")
            text = assert_and_parse_html(self, text, None,
                "Second argument is not valid HTML:")
        real_count = content.count(text)
        return (text_repr, real_count, msg_prefix)

    def assertContains(self, response, text, count=None, status_code=200,
                       msg_prefix='', html=False):
        """
        Asserts that a response indicates that some content was retrieved
        successfully, (i.e., the HTTP status code was as expected), and that
        ``text`` occurs ``count`` times in the content of the response.
        If ``count`` is None, the count doesn't matter - the assertion is true
        if the text occurs at least once in the response.
        """
        text_repr, real_count, msg_prefix = self._assert_contains(
            response, text, status_code, msg_prefix, html)

        if count is not None:
            self.assertEqual(real_count, count,
                msg_prefix + "Found %d instances of %s in response"
                " (expected %d)" % (real_count, text_repr, count))
        else:
            self.assertTrue(real_count != 0,
                msg_prefix + "Couldn't find %s in response" % text_repr)

    def assertNotContains(self, response, text, status_code=200,
                          msg_prefix='', html=False):
        """
        Asserts that a response indicates that some content was retrieved
        successfully, (i.e., the HTTP status code was as expected), and that
        ``text`` doesn't occurs in the content of the response.
        """
        text_repr, real_count, msg_prefix = self._assert_contains(
            response, text, status_code, msg_prefix, html)

        self.assertEqual(real_count, 0,
                msg_prefix + "Response should not contain %s" % text_repr)

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
        for i, context in enumerate(contexts):
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

    def assertFormsetError(self, response, formset, form_index, field, errors,
                           msg_prefix=''):
        """
        Asserts that a formset used to render the response has a specific error.

        For field errors, specify the ``form_index`` and the ``field``.
        For non-field errors, specify the ``form_index`` and the ``field`` as
        None.
        For non-form errors, specify ``form_index`` as None and the ``field``
        as None.
        """
        # Add punctuation to msg_prefix
        if msg_prefix:
            msg_prefix += ": "

        # Put context(s) into a list to simplify processing.
        contexts = to_list(response.context)
        if not contexts:
            self.fail(msg_prefix + 'Response did not use any contexts to '
                      'render the response')

        # Put error(s) into a list to simplify processing.
        errors = to_list(errors)

        # Search all contexts for the error.
        found_formset = False
        for i, context in enumerate(contexts):
            if formset not in context:
                continue
            found_formset = True
            for err in errors:
                if field is not None:
                    if field in context[formset].forms[form_index].errors:
                        field_errors = context[formset].forms[form_index].errors[field]
                        self.assertTrue(err in field_errors,
                                msg_prefix + "The field '%s' on formset '%s', "
                                "form %d in context %d does not contain the "
                                "error '%s' (actual errors: %s)" %
                                (field, formset, form_index, i, err,
                                 repr(field_errors)))
                    elif field in context[formset].forms[form_index].fields:
                        self.fail(msg_prefix + "The field '%s' "
                                  "on formset '%s', form %d in "
                                  "context %d contains no errors" %
                                  (field, formset, form_index, i))
                    else:
                        self.fail(msg_prefix + "The formset '%s', form %d in "
                                  "context %d does not contain the field '%s'" %
                                  (formset, form_index, i, field))
                elif form_index is not None:
                    non_field_errors = context[formset].forms[form_index].non_field_errors()
                    self.assertFalse(len(non_field_errors) == 0,
                                     msg_prefix + "The formset '%s', form %d in "
                                     "context %d does not contain any non-field "
                                     "errors." % (formset, form_index, i))
                    self.assertTrue(err in non_field_errors,
                                    msg_prefix + "The formset '%s', form %d "
                                    "in context %d does not contain the "
                                    "non-field error '%s' "
                                    "(actual errors: %s)" %
                                    (formset, form_index, i, err,
                                     repr(non_field_errors)))
                else:
                    non_form_errors = context[formset].non_form_errors()
                    self.assertFalse(len(non_form_errors) == 0,
                                     msg_prefix + "The formset '%s' in "
                                     "context %d does not contain any "
                                     "non-form errors." % (formset, i))
                    self.assertTrue(err in non_form_errors,
                                    msg_prefix + "The formset '%s' in context "
                                    "%d does not contain the "
                                    "non-form error '%s' (actual errors: %s)" %
                                    (formset, i, err, repr(non_form_errors)))
        if not found_formset:
            self.fail(msg_prefix + "The formset '%s' was not used to render "
                      "the response" % formset)

    def _assert_template_used(self, response, template_name, msg_prefix):

        if response is None and template_name is None:
            raise TypeError('response and/or template_name argument must be provided')

        if msg_prefix:
            msg_prefix += ": "

        if template_name is not None and response is not None and not hasattr(response, 'templates'):
            raise ValueError(
                "assertTemplateUsed() and assertTemplateNotUsed() are only "
                "usable on responses fetched using the Django test Client."
            )

        if not hasattr(response, 'templates') or (response is None and template_name):
            if response:
                template_name = response
                response = None
            # use this template with context manager
            return template_name, None, msg_prefix

        template_names = [t.name for t in response.templates if t.name is not
                          None]
        return None, template_names, msg_prefix

    def assertTemplateUsed(self, response=None, template_name=None, msg_prefix='', count=None):
        """
        Asserts that the template with the provided name was used in rendering
        the response. Also usable as context manager.
        """
        context_mgr_template, template_names, msg_prefix = self._assert_template_used(
            response, template_name, msg_prefix)

        if context_mgr_template:
            # Use assertTemplateUsed as context manager.
            return _AssertTemplateUsedContext(self, context_mgr_template)

        if not template_names:
            self.fail(msg_prefix + "No templates used to render the response")
        self.assertTrue(template_name in template_names,
            msg_prefix + "Template '%s' was not a template used to render"
            " the response. Actual template(s) used: %s" %
                (template_name, ', '.join(template_names)))

        if count is not None:
            self.assertEqual(template_names.count(template_name), count,
                msg_prefix + "Template '%s' was expected to be rendered %d "
                "time(s) but was actually rendered %d time(s)." %
                    (template_name, count, template_names.count(template_name)))

    def assertTemplateNotUsed(self, response=None, template_name=None, msg_prefix=''):
        """
        Asserts that the template with the provided name was NOT used in
        rendering the response. Also usable as context manager.
        """

        context_mgr_template, template_names, msg_prefix = self._assert_template_used(
            response, template_name, msg_prefix)

        if context_mgr_template:
            # Use assertTemplateNotUsed as context manager.
            return _AssertTemplateNotUsedContext(self, context_mgr_template)

        self.assertFalse(template_name in template_names,
            msg_prefix + "Template '%s' was used unexpectedly in rendering"
            " the response" % template_name)

    def assertRaisesMessage(self, expected_exception, expected_message, *args, **kwargs):
        """
        Asserts that the message in a raised exception matches the passed
        value.

        Args:
            expected_exception: Exception class expected to be raised.
            expected_message: expected error message string value.
            args: Function to be called and extra positional args.
            kwargs: Extra kwargs.
        """
        # callable_obj was a documented kwarg in older version of Django, but
        # had to be removed due to a bad fix for http://bugs.python.org/issue24134
        # inadvertently making its way into Python 2.7.10.
        callable_obj = kwargs.pop('callable_obj', None)
        if callable_obj:
            args = (callable_obj,) + args
        return six.assertRaisesRegex(self, expected_exception,
                re.escape(expected_message), *args, **kwargs)

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
            empty_value: the expected clean output for inputs in empty_values

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
        for e in required.empty_values:
            with self.assertRaises(ValidationError) as context_manager:
                required.clean(e)
            self.assertEqual(context_manager.exception.messages,
                             error_required)
            self.assertEqual(optional.clean(e), empty_value)
        # test that max_length and min_length are always accepted
        if issubclass(fieldclass, CharField):
            field_kwargs.update({'min_length': 2, 'max_length': 20})
            self.assertIsInstance(fieldclass(*field_args, **field_kwargs),
                                  fieldclass)

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

    def assertInHTML(self, needle, haystack, count=None, msg_prefix=''):
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
        """
        Asserts that the JSON fragments raw and expected_data are equal.
        Usual JSON non-significant whitespace rules apply as the heavyweight
        is delegated to the json library.
        """
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

    def assertJSONNotEqual(self, raw, expected_data, msg=None):
        """
        Asserts that the JSON fragments raw and expected_data are not equal.
        Usual JSON non-significant whitespace rules apply as the heavyweight
        is delegated to the json library.
        """
        try:
            data = json.loads(raw)
        except ValueError:
            self.fail("First argument is not valid JSON: %r" % raw)
        if isinstance(expected_data, six.string_types):
            try:
                expected_data = json.loads(expected_data)
            except ValueError:
                self.fail("Second argument is not valid JSON: %r" % expected_data)
        self.assertNotEqual(data, expected_data, msg=msg)

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

    # Subclasses can ask for resetting of auto increment sequence before each
    # test case
    reset_sequences = False

    # Subclasses can enable only a subset of apps for faster tests
    available_apps = None

    # Subclasses can define fixtures which will be automatically installed.
    fixtures = None

    # If transactions aren't available, Django will serialize the database
    # contents into a fixture during setup and flush and reload them
    # during teardown (as flush does not restore data from migrations).
    # This can be slow; this flag allows enabling on a per-case basis.
    serialized_rollback = False

    def _pre_setup(self):
        """Performs any pre-test setup. This includes:

        * If the class has an 'available_apps' attribute, restricting the app
          registry to these applications, then firing post_migrate -- it must
          run with the correct set of applications for the test case.
        * If the class has a 'fixtures' attribute, installing these fixtures.
        """
        super(TransactionTestCase, self)._pre_setup()
        if self.available_apps is not None:
            apps.set_available_apps(self.available_apps)
            setting_changed.send(sender=settings._wrapped.__class__,
                                 setting='INSTALLED_APPS',
                                 value=self.available_apps,
                                 enter=True)
            for db_name in self._databases_names(include_mirrors=False):
                flush.Command.emit_post_migrate(verbosity=0, interactive=False, database=db_name)
        try:
            self._fixture_setup()
        except Exception:
            if self.available_apps is not None:
                apps.unset_available_apps()
                setting_changed.send(sender=settings._wrapped.__class__,
                                     setting='INSTALLED_APPS',
                                     value=settings.INSTALLED_APPS,
                                     enter=False)

            raise

    @classmethod
    def _databases_names(cls, include_mirrors=True):
        # If the test case has a multi_db=True flag, act on all databases,
        # including mirrors or not. Otherwise, just on the default DB.
        if getattr(cls, 'multi_db', False):
            return [alias for alias in connections
                    if include_mirrors or not connections[alias].settings_dict['TEST']['MIRROR']]
        else:
            return [DEFAULT_DB_ALIAS]

    def _reset_sequences(self, db_name):
        conn = connections[db_name]
        if conn.features.supports_sequence_reset:
            sql_list = conn.ops.sequence_reset_by_name_sql(
                no_style(), conn.introspection.sequence_list())
            if sql_list:
                with transaction.atomic(using=db_name):
                    cursor = conn.cursor()
                    for sql in sql_list:
                        cursor.execute(sql)

    def _fixture_setup(self):
        for db_name in self._databases_names(include_mirrors=False):
            # Reset sequences
            if self.reset_sequences:
                self._reset_sequences(db_name)

            # If we need to provide replica initial data from migrated apps,
            # then do so.
            if self.serialized_rollback and hasattr(connections[db_name], "_test_serialized_contents"):
                if self.available_apps is not None:
                    apps.unset_available_apps()
                connections[db_name].creation.deserialize_db_from_string(
                    connections[db_name]._test_serialized_contents
                )
                if self.available_apps is not None:
                    apps.set_available_apps(self.available_apps)

            if self.fixtures:
                # We have to use this slightly awkward syntax due to the fact
                # that we're using *args and **kwargs together.
                call_command('loaddata', *self.fixtures,
                             **{'verbosity': 0, 'database': db_name})

    def _should_reload_connections(self):
        return True

    def _post_teardown(self):
        """Performs any post-test things. This includes:

        * Flushing the contents of the database, to leave a clean slate. If
          the class has an 'available_apps' attribute, post_migrate isn't fired.
        * Force-closing the connection, so the next test gets a clean cursor.
        """
        try:
            self._fixture_teardown()
            super(TransactionTestCase, self)._post_teardown()
            if self._should_reload_connections():
                # Some DB cursors include SQL statements as part of cursor
                # creation. If you have a test that does a rollback, the effect
                # of these statements is lost, which can affect the operation of
                # tests (e.g., losing a timezone setting causing objects to be
                # created with the wrong time). To make sure this doesn't
                # happen, get a clean connection at the start of every test.
                for conn in connections.all():
                    conn.close()
        finally:
            if self.available_apps is not None:
                apps.unset_available_apps()
                setting_changed.send(sender=settings._wrapped.__class__,
                                     setting='INSTALLED_APPS',
                                     value=settings.INSTALLED_APPS,
                                     enter=False)

    def _fixture_teardown(self):
        # Allow TRUNCATE ... CASCADE and don't emit the post_migrate signal
        # when flushing only a subset of the apps
        for db_name in self._databases_names(include_mirrors=False):
            # Flush the database
            call_command('flush', verbosity=0, interactive=False,
                         database=db_name, reset_sequences=False,
                         allow_cascade=self.available_apps is not None,
                         inhibit_post_migrate=self.available_apps is not None)

    def assertQuerysetEqual(self, qs, values, transform=repr, ordered=True, msg=None):
        items = six.moves.map(transform, qs)
        if not ordered:
            return self.assertEqual(Counter(items), Counter(values), msg=msg)
        values = list(values)
        # For example qs.iterator() could be passed as qs, but it does not
        # have 'ordered' attribute.
        if len(values) > 1 and hasattr(qs, 'ordered') and not qs.ordered:
            raise ValueError("Trying to compare non-ordered queryset "
                             "against more than one ordered values")
        return self.assertEqual(list(items), values, msg=msg)

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
    Similar to TransactionTestCase, but uses `transaction.atomic()` to achieve
    test isolation.

    In most situation, TestCase should be prefered to TransactionTestCase as
    it allows faster execution. However, there are some situations where using
    TransactionTestCase might be necessary (e.g. testing some transactional
    behavior).

    On database backends with no transaction support, TestCase behaves as
    TransactionTestCase.
    """
    @classmethod
    def _enter_atomics(cls):
        """Helper method to open atomic blocks for multiple databases"""
        atomics = {}
        for db_name in cls._databases_names():
            atomics[db_name] = transaction.atomic(using=db_name)
            atomics[db_name].__enter__()
        return atomics

    @classmethod
    def _rollback_atomics(cls, atomics):
        """Rollback atomic blocks opened through the previous method"""
        for db_name in reversed(cls._databases_names()):
            transaction.set_rollback(True, using=db_name)
            atomics[db_name].__exit__(None, None, None)

    @classmethod
    def setUpClass(cls):
        super(TestCase, cls).setUpClass()
        if not connections_support_transactions():
            return
        cls.cls_atomics = cls._enter_atomics()

        if cls.fixtures:
            for db_name in cls._databases_names(include_mirrors=False):
                    try:
                        call_command('loaddata', *cls.fixtures, **{
                            'verbosity': 0,
                            'commit': False,
                            'database': db_name,
                        })
                    except Exception:
                        cls._rollback_atomics(cls.cls_atomics)
                        raise
        try:
            cls.setUpTestData()
        except Exception:
            cls._rollback_atomics(cls.cls_atomics)
            raise

    @classmethod
    def tearDownClass(cls):
        if connections_support_transactions():
            cls._rollback_atomics(cls.cls_atomics)
            for conn in connections.all():
                conn.close()
        super(TestCase, cls).tearDownClass()

    @classmethod
    def setUpTestData(cls):
        """Load initial data for the TestCase"""
        pass

    def _should_reload_connections(self):
        if connections_support_transactions():
            return False
        return super(TestCase, self)._should_reload_connections()

    def _fixture_setup(self):
        if not connections_support_transactions():
            # If the backend does not support transactions, we should reload
            # class data before each test
            self.setUpTestData()
            return super(TestCase, self)._fixture_setup()

        assert not self.reset_sequences, 'reset_sequences cannot be used on TestCase instances'
        self.atomics = self._enter_atomics()

    def _fixture_teardown(self):
        if not connections_support_transactions():
            return super(TestCase, self)._fixture_teardown()
        self._rollback_atomics(self.atomics)


class CheckCondition(object):
    """Descriptor class for deferred condition checking"""
    def __init__(self, cond_func):
        self.cond_func = cond_func

    def __get__(self, obj, objtype):
        return self.cond_func()


def _deferredSkip(condition, reason):
    def decorator(test_func):
        if not (isinstance(test_func, type) and
                issubclass(test_func, unittest.TestCase)):
            @wraps(test_func)
            def skip_wrapper(*args, **kwargs):
                if condition():
                    raise unittest.SkipTest(reason)
                return test_func(*args, **kwargs)
            test_item = skip_wrapper
        else:
            # Assume a class is decorated
            test_item = test_func
            test_item.__unittest_skip__ = CheckCondition(condition)
        test_item.__unittest_skip_why__ = reason
        return test_item
    return decorator


def skipIfDBFeature(*features):
    """
    Skip a test if a database has at least one of the named features.
    """
    return _deferredSkip(
        lambda: any(getattr(connection.features, feature, False) for feature in features),
        "Database has feature(s) %s" % ", ".join(features)
    )


def skipUnlessDBFeature(*features):
    """
    Skip a test unless a database has all the named features.
    """
    return _deferredSkip(
        lambda: not all(getattr(connection.features, feature, False) for feature in features),
        "Database doesn't support feature(s): %s" % ", ".join(features)
    )


class QuietWSGIRequestHandler(WSGIRequestHandler):
    """
    Just a regular WSGIRequestHandler except it doesn't log to the standard
    output any of the requests received, so as to not clutter the output for
    the tests' results.
    """

    def log_message(*args):
        pass


class FSFilesHandler(WSGIHandler):
    """
    WSGI middleware that intercepts calls to a directory, as defined by one of
    the *_ROOT settings, and serves those files, publishing them under *_URL.
    """
    def __init__(self, application):
        self.application = application
        self.base_url = urlparse(self.get_base_url())
        super(FSFilesHandler, self).__init__()

    def _should_handle(self, path):
        """
        Checks if the path should be handled. Ignores the path if:

        * the host is provided as part of the base_url
        * the request's path isn't under the media path (or equal)
        """
        return path.startswith(self.base_url[2]) and not self.base_url[1]

    def file_path(self, url):
        """
        Returns the relative path to the file on disk for the given URL.
        """
        relative_url = url[len(self.base_url[2]):]
        return url2pathname(relative_url)

    def get_response(self, request):
        from django.http import Http404

        if self._should_handle(request.path):
            try:
                return self.serve(request)
            except Http404:
                pass
        return super(FSFilesHandler, self).get_response(request)

    def serve(self, request):
        os_rel_path = self.file_path(request.path)
        os_rel_path = posixpath.normpath(unquote(os_rel_path))
        # Emulate behavior of django.contrib.staticfiles.views.serve() when it
        # invokes staticfiles' finders functionality.
        # TODO: Modify if/when that internal API is refactored
        final_rel_path = os_rel_path.replace('\\', '/').lstrip('/')
        return serve(request, final_rel_path, document_root=self.get_base_dir())

    def __call__(self, environ, start_response):
        if not self._should_handle(get_path_info(environ)):
            return self.application(environ, start_response)
        return super(FSFilesHandler, self).__call__(environ, start_response)


class _StaticFilesHandler(FSFilesHandler):
    """
    Handler for serving static files. A private class that is meant to be used
    solely as a convenience by LiveServerThread.
    """

    def get_base_dir(self):
        return settings.STATIC_ROOT

    def get_base_url(self):
        return settings.STATIC_URL


class _MediaFilesHandler(FSFilesHandler):
    """
    Handler for serving the media files. A private class that is meant to be
    used solely as a convenience by LiveServerThread.
    """

    def get_base_dir(self):
        return settings.MEDIA_ROOT

    def get_base_url(self):
        return settings.MEDIA_URL


class LiveServerThread(threading.Thread):
    """
    Thread for running a live http server while the tests are running.
    """

    def __init__(self, host, possible_ports, static_handler, connections_override=None):
        self.host = host
        self.port = None
        self.possible_ports = possible_ports
        self.is_ready = threading.Event()
        self.error = None
        self.static_handler = static_handler
        self.connections_override = connections_override
        super(LiveServerThread, self).__init__()

    def run(self):
        """
        Sets up the live server and databases, and then loops over handling
        http requests.
        """
        if self.connections_override:
            # Override this thread's database connections with the ones
            # provided by the main thread.
            for alias, conn in self.connections_override.items():
                connections[alias] = conn
        try:
            # Create the handler for serving static and media files
            handler = self.static_handler(_MediaFilesHandler(WSGIHandler()))

            # Go through the list of possible ports, hoping that we can find
            # one that is free to use for the WSGI server.
            for index, port in enumerate(self.possible_ports):
                try:
                    self.httpd = WSGIServer(
                        (self.host, port), QuietWSGIRequestHandler)
                except socket.error as e:
                    if (index + 1 < len(self.possible_ports) and
                            e.errno == errno.EADDRINUSE):
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

    def terminate(self):
        if hasattr(self, 'httpd'):
            # Stop the WSGI server
            self.httpd.shutdown()
            self.httpd.server_close()


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

    static_handler = _StaticFilesHandler

    @property
    def live_server_url(self):
        return 'http://%s:%s' % (
            self.server_thread.host, self.server_thread.port)

    @classmethod
    def setUpClass(cls):
        super(LiveServerTestCase, cls).setUpClass()
        connections_override = {}
        for conn in connections.all():
            # If using in-memory sqlite databases, pass the connections to
            # the server thread.
            if conn.vendor == 'sqlite' and conn.is_in_memory_db(conn.settings_dict['NAME']):
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
            msg = 'Invalid address ("%s") for live server.' % specified_address
            six.reraise(ImproperlyConfigured, ImproperlyConfigured(msg), sys.exc_info()[2])
        cls.server_thread = LiveServerThread(host, possible_ports,
                                             cls.static_handler,
                                             connections_override=connections_override)
        cls.server_thread.daemon = True
        cls.server_thread.start()

        # Wait for the live server to be ready
        cls.server_thread.is_ready.wait()
        if cls.server_thread.error:
            # Clean up behind ourselves, since tearDownClass won't get called in
            # case of errors.
            cls._tearDownClassInternal()
            raise cls.server_thread.error

    @classmethod
    def _tearDownClassInternal(cls):
        # There may not be a 'server_thread' attribute if setUpClass() for some
        # reasons has raised an exception.
        if hasattr(cls, 'server_thread'):
            # Terminate the live server's thread
            cls.server_thread.terminate()
            cls.server_thread.join()

        # Restore sqlite in-memory database connections' non-shareability
        for conn in connections.all():
            if conn.vendor == 'sqlite' and conn.is_in_memory_db(conn.settings_dict['NAME']):
                conn.allow_thread_sharing = False

    @classmethod
    def tearDownClass(cls):
        cls._tearDownClassInternal()
        super(LiveServerTestCase, cls).tearDownClass()
