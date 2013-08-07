# -*- coding: utf-8 -*-
"""
Regression tests for the Test Client, especially the customized assertions.
"""
from __future__ import unicode_literals

import os

from django.core.urlresolvers import reverse
from django.template import (TemplateSyntaxError,
    Context, Template, loader)
import django.template.context
from django.test import Client, TestCase
from django.test.client import encode_file, RequestFactory
from django.test.utils import ContextList, override_settings, str_prefix
from django.template.response import SimpleTemplateResponse
from django.utils._os import upath
from django.utils.translation import ugettext_lazy
from django.http import HttpResponse
from django.contrib.auth.signals import user_logged_out, user_logged_in
from django.contrib.auth.models import User

from .models import CustomUser
from .views import CustomTestException

@override_settings(
    TEMPLATE_DIRS=(os.path.join(os.path.dirname(upath(__file__)), 'templates'),)
)
class AssertContainsTests(TestCase):
    def test_contains(self):
        "Responses can be inspected for content, including counting repeated substrings"
        response = self.client.get('/test_client_regress/no_template_view/')

        self.assertNotContains(response, 'never')
        self.assertContains(response, 'never', 0)
        self.assertContains(response, 'once')
        self.assertContains(response, 'once', 1)
        self.assertContains(response, 'twice')
        self.assertContains(response, 'twice', 2)

        try:
            self.assertContains(response, 'text', status_code=999)
        except AssertionError as e:
            self.assertIn("Couldn't retrieve content: Response code was 200 (expected 999)", str(e))
        try:
            self.assertContains(response, 'text', status_code=999, msg_prefix='abc')
        except AssertionError as e:
            self.assertIn("abc: Couldn't retrieve content: Response code was 200 (expected 999)", str(e))

        try:
            self.assertNotContains(response, 'text', status_code=999)
        except AssertionError as e:
            self.assertIn("Couldn't retrieve content: Response code was 200 (expected 999)", str(e))
        try:
            self.assertNotContains(response, 'text', status_code=999, msg_prefix='abc')
        except AssertionError as e:
            self.assertIn("abc: Couldn't retrieve content: Response code was 200 (expected 999)", str(e))

        try:
            self.assertNotContains(response, 'once')
        except AssertionError as e:
            self.assertIn("Response should not contain 'once'", str(e))
        try:
            self.assertNotContains(response, 'once', msg_prefix='abc')
        except AssertionError as e:
            self.assertIn("abc: Response should not contain 'once'", str(e))

        try:
            self.assertContains(response, 'never', 1)
        except AssertionError as e:
            self.assertIn("Found 0 instances of 'never' in response (expected 1)", str(e))
        try:
            self.assertContains(response, 'never', 1, msg_prefix='abc')
        except AssertionError as e:
            self.assertIn("abc: Found 0 instances of 'never' in response (expected 1)", str(e))

        try:
            self.assertContains(response, 'once', 0)
        except AssertionError as e:
            self.assertIn("Found 1 instances of 'once' in response (expected 0)", str(e))
        try:
            self.assertContains(response, 'once', 0, msg_prefix='abc')
        except AssertionError as e:
            self.assertIn("abc: Found 1 instances of 'once' in response (expected 0)", str(e))

        try:
            self.assertContains(response, 'once', 2)
        except AssertionError as e:
            self.assertIn("Found 1 instances of 'once' in response (expected 2)", str(e))
        try:
            self.assertContains(response, 'once', 2, msg_prefix='abc')
        except AssertionError as e:
            self.assertIn("abc: Found 1 instances of 'once' in response (expected 2)", str(e))

        try:
            self.assertContains(response, 'twice', 1)
        except AssertionError as e:
            self.assertIn("Found 2 instances of 'twice' in response (expected 1)", str(e))
        try:
            self.assertContains(response, 'twice', 1, msg_prefix='abc')
        except AssertionError as e:
            self.assertIn("abc: Found 2 instances of 'twice' in response (expected 1)", str(e))

        try:
            self.assertContains(response, 'thrice')
        except AssertionError as e:
            self.assertIn("Couldn't find 'thrice' in response", str(e))
        try:
            self.assertContains(response, 'thrice', msg_prefix='abc')
        except AssertionError as e:
            self.assertIn("abc: Couldn't find 'thrice' in response", str(e))

        try:
            self.assertContains(response, 'thrice', 3)
        except AssertionError as e:
            self.assertIn("Found 0 instances of 'thrice' in response (expected 3)", str(e))
        try:
            self.assertContains(response, 'thrice', 3, msg_prefix='abc')
        except AssertionError as e:
            self.assertIn("abc: Found 0 instances of 'thrice' in response (expected 3)", str(e))

    def test_unicode_contains(self):
        "Unicode characters can be found in template context"
        #Regression test for #10183
        r = self.client.get('/test_client_regress/check_unicode/')
        self.assertContains(r, 'さかき')
        self.assertContains(r, b'\xe5\xb3\xa0'.decode('utf-8'))

    def test_unicode_not_contains(self):
        "Unicode characters can be searched for, and not found in template context"
        #Regression test for #10183
        r = self.client.get('/test_client_regress/check_unicode/')
        self.assertNotContains(r, 'はたけ')
        self.assertNotContains(r, b'\xe3\x81\xaf\xe3\x81\x9f\xe3\x81\x91'.decode('utf-8'))

    def test_binary_contains(self):
        r = self.client.get('/test_client_regress/check_binary/')
        self.assertContains(r, b'%PDF-1.4\r\n%\x93\x8c\x8b\x9e')
        with self.assertRaises(AssertionError):
            self.assertContains(r, b'%PDF-1.4\r\n%\x93\x8c\x8b\x9e', count=2)

    def test_binary_not_contains(self):
        r = self.client.get('/test_client_regress/check_binary/')
        self.assertNotContains(r, b'%ODF-1.4\r\n%\x93\x8c\x8b\x9e')
        with self.assertRaises(AssertionError):
            self.assertNotContains(r, b'%PDF-1.4\r\n%\x93\x8c\x8b\x9e')

    def test_nontext_contains(self):
        r = self.client.get('/test_client_regress/no_template_view/')
        self.assertContains(r, ugettext_lazy('once'))

    def test_nontext_not_contains(self):
        r = self.client.get('/test_client_regress/no_template_view/')
        self.assertNotContains(r, ugettext_lazy('never'))

    def test_assert_contains_renders_template_response(self):
        """ Test that we can pass in an unrendered SimpleTemplateReponse
            without throwing an error.
            Refs #15826.
        """
        response = SimpleTemplateResponse(Template('Hello'), status=200)
        self.assertContains(response, 'Hello')

    def test_assert_contains_using_non_template_response(self):
        """ Test that auto-rendering does not affect responses that aren't
            instances (or subclasses) of SimpleTemplateResponse.
            Refs #15826.
        """
        response = HttpResponse('Hello')
        self.assertContains(response, 'Hello')

    def test_assert_not_contains_renders_template_response(self):
        """ Test that we can pass in an unrendered SimpleTemplateReponse
            without throwing an error.
            Refs #15826.
        """
        response = SimpleTemplateResponse(Template('Hello'), status=200)
        self.assertNotContains(response, 'Bye')

    def test_assert_not_contains_using_non_template_response(self):
        """ Test that auto-rendering does not affect responses that aren't
            instances (or subclasses) of SimpleTemplateResponse.
            Refs #15826.
        """
        response = HttpResponse('Hello')
        self.assertNotContains(response, 'Bye')

@override_settings(PASSWORD_HASHERS=('django.contrib.auth.hashers.SHA1PasswordHasher',))
class AssertTemplateUsedTests(TestCase):
    fixtures = ['testdata.json']

    def test_no_context(self):
        "Template usage assertions work then templates aren't in use"
        response = self.client.get('/test_client_regress/no_template_view/')

        # Check that the no template case doesn't mess with the template assertions
        self.assertTemplateNotUsed(response, 'GET Template')

        try:
            self.assertTemplateUsed(response, 'GET Template')
        except AssertionError as e:
            self.assertIn("No templates used to render the response", str(e))

        try:
            self.assertTemplateUsed(response, 'GET Template', msg_prefix='abc')
        except AssertionError as e:
            self.assertIn("abc: No templates used to render the response", str(e))

    def test_single_context(self):
        "Template assertions work when there is a single context"
        response = self.client.get('/test_client/post_view/', {})

        try:
            self.assertTemplateNotUsed(response, 'Empty GET Template')
        except AssertionError as e:
            self.assertIn("Template 'Empty GET Template' was used unexpectedly in rendering the response", str(e))

        try:
            self.assertTemplateNotUsed(response, 'Empty GET Template', msg_prefix='abc')
        except AssertionError as e:
            self.assertIn("abc: Template 'Empty GET Template' was used unexpectedly in rendering the response", str(e))

        try:
            self.assertTemplateUsed(response, 'Empty POST Template')
        except AssertionError as e:
            self.assertIn("Template 'Empty POST Template' was not a template used to render the response. Actual template(s) used: Empty GET Template", str(e))

        try:
            self.assertTemplateUsed(response, 'Empty POST Template', msg_prefix='abc')
        except AssertionError as e:
            self.assertIn("abc: Template 'Empty POST Template' was not a template used to render the response. Actual template(s) used: Empty GET Template", str(e))

    def test_multiple_context(self):
        "Template assertions work when there are multiple contexts"
        post_data = {
            'text': 'Hello World',
            'email': 'foo@example.com',
            'value': 37,
            'single': 'b',
            'multi': ('b','c','e')
        }
        response = self.client.post('/test_client/form_view_with_template/', post_data)
        self.assertContains(response, 'POST data OK')
        try:
            self.assertTemplateNotUsed(response, "form_view.html")
        except AssertionError as e:
            self.assertIn("Template 'form_view.html' was used unexpectedly in rendering the response", str(e))

        try:
            self.assertTemplateNotUsed(response, 'base.html')
        except AssertionError as e:
            self.assertIn("Template 'base.html' was used unexpectedly in rendering the response", str(e))

        try:
            self.assertTemplateUsed(response, "Valid POST Template")
        except AssertionError as e:
            self.assertIn("Template 'Valid POST Template' was not a template used to render the response. Actual template(s) used: form_view.html, base.html", str(e))

class AssertRedirectsTests(TestCase):
    def test_redirect_page(self):
        "An assertion is raised if the original page couldn't be retrieved as expected"
        # This page will redirect with code 301, not 302
        response = self.client.get('/test_client/permanent_redirect_view/')
        try:
            self.assertRedirects(response, '/test_client/get_view/')
        except AssertionError as e:
            self.assertIn("Response didn't redirect as expected: Response code was 301 (expected 302)", str(e))

        try:
            self.assertRedirects(response, '/test_client/get_view/', msg_prefix='abc')
        except AssertionError as e:
            self.assertIn("abc: Response didn't redirect as expected: Response code was 301 (expected 302)", str(e))

    def test_lost_query(self):
        "An assertion is raised if the redirect location doesn't preserve GET parameters"
        response = self.client.get('/test_client/redirect_view/', {'var': 'value'})
        try:
            self.assertRedirects(response, '/test_client/get_view/')
        except AssertionError as e:
            self.assertIn("Response redirected to 'http://testserver/test_client/get_view/?var=value', expected 'http://testserver/test_client/get_view/'", str(e))

        try:
            self.assertRedirects(response, '/test_client/get_view/', msg_prefix='abc')
        except AssertionError as e:
            self.assertIn("abc: Response redirected to 'http://testserver/test_client/get_view/?var=value', expected 'http://testserver/test_client/get_view/'", str(e))

    def test_incorrect_target(self):
        "An assertion is raised if the response redirects to another target"
        response = self.client.get('/test_client/permanent_redirect_view/')
        try:
            # Should redirect to get_view
            self.assertRedirects(response, '/test_client/some_view/')
        except AssertionError as e:
            self.assertIn("Response didn't redirect as expected: Response code was 301 (expected 302)", str(e))

    def test_target_page(self):
        "An assertion is raised if the response redirect target cannot be retrieved as expected"
        response = self.client.get('/test_client/double_redirect_view/')
        try:
            # The redirect target responds with a 301 code, not 200
            self.assertRedirects(response, 'http://testserver/test_client/permanent_redirect_view/')
        except AssertionError as e:
            self.assertIn("Couldn't retrieve redirection page '/test_client/permanent_redirect_view/': response code was 301 (expected 200)", str(e))

        try:
            # The redirect target responds with a 301 code, not 200
            self.assertRedirects(response, 'http://testserver/test_client/permanent_redirect_view/', msg_prefix='abc')
        except AssertionError as e:
            self.assertIn("abc: Couldn't retrieve redirection page '/test_client/permanent_redirect_view/': response code was 301 (expected 200)", str(e))

    def test_redirect_chain(self):
        "You can follow a redirect chain of multiple redirects"
        response = self.client.get('/test_client_regress/redirects/further/more/', {}, follow=True)
        self.assertRedirects(response, '/test_client_regress/no_template_view/',
            status_code=301, target_status_code=200)

        self.assertEqual(len(response.redirect_chain), 1)
        self.assertEqual(response.redirect_chain[0], ('http://testserver/test_client_regress/no_template_view/', 301))

    def test_multiple_redirect_chain(self):
        "You can follow a redirect chain of multiple redirects"
        response = self.client.get('/test_client_regress/redirects/', {}, follow=True)
        self.assertRedirects(response, '/test_client_regress/no_template_view/',
            status_code=301, target_status_code=200)

        self.assertEqual(len(response.redirect_chain), 3)
        self.assertEqual(response.redirect_chain[0], ('http://testserver/test_client_regress/redirects/further/', 301))
        self.assertEqual(response.redirect_chain[1], ('http://testserver/test_client_regress/redirects/further/more/', 301))
        self.assertEqual(response.redirect_chain[2], ('http://testserver/test_client_regress/no_template_view/', 301))

    def test_redirect_chain_to_non_existent(self):
        "You can follow a chain to a non-existent view"
        response = self.client.get('/test_client_regress/redirect_to_non_existent_view2/', {}, follow=True)
        self.assertRedirects(response, '/test_client_regress/non_existent_view/',
            status_code=301, target_status_code=404)

    def test_redirect_chain_to_self(self):
        "Redirections to self are caught and escaped"
        response = self.client.get('/test_client_regress/redirect_to_self/', {}, follow=True)
        # The chain of redirects stops once the cycle is detected.
        self.assertRedirects(response, '/test_client_regress/redirect_to_self/',
            status_code=301, target_status_code=301)
        self.assertEqual(len(response.redirect_chain), 2)

    def test_circular_redirect(self):
        "Circular redirect chains are caught and escaped"
        response = self.client.get('/test_client_regress/circular_redirect_1/', {}, follow=True)
        # The chain of redirects will get back to the starting point, but stop there.
        self.assertRedirects(response, '/test_client_regress/circular_redirect_2/',
            status_code=301, target_status_code=301)
        self.assertEqual(len(response.redirect_chain), 4)

    def test_redirect_chain_post(self):
        "A redirect chain will be followed from an initial POST post"
        response = self.client.post('/test_client_regress/redirects/',
            {'nothing': 'to_send'}, follow=True)
        self.assertRedirects(response,
            '/test_client_regress/no_template_view/', 301, 200)
        self.assertEqual(len(response.redirect_chain), 3)

    def test_redirect_chain_head(self):
        "A redirect chain will be followed from an initial HEAD request"
        response = self.client.head('/test_client_regress/redirects/',
            {'nothing': 'to_send'}, follow=True)
        self.assertRedirects(response,
            '/test_client_regress/no_template_view/', 301, 200)
        self.assertEqual(len(response.redirect_chain), 3)

    def test_redirect_chain_options(self):
        "A redirect chain will be followed from an initial OPTIONS request"
        response = self.client.options('/test_client_regress/redirects/',
            follow=True)
        self.assertRedirects(response,
            '/test_client_regress/no_template_view/', 301, 200)
        self.assertEqual(len(response.redirect_chain), 3)

    def test_redirect_chain_put(self):
        "A redirect chain will be followed from an initial PUT request"
        response = self.client.put('/test_client_regress/redirects/',
            follow=True)
        self.assertRedirects(response,
            '/test_client_regress/no_template_view/', 301, 200)
        self.assertEqual(len(response.redirect_chain), 3)

    def test_redirect_chain_delete(self):
        "A redirect chain will be followed from an initial DELETE request"
        response = self.client.delete('/test_client_regress/redirects/',
            follow=True)
        self.assertRedirects(response,
            '/test_client_regress/no_template_view/', 301, 200)
        self.assertEqual(len(response.redirect_chain), 3)

    def test_redirect_to_different_host(self):
        "The test client will preserve scheme, host and port changes"
        response = self.client.get('/test_client_regress/redirect_other_host/', follow=True)
        self.assertRedirects(response,
            'https://otherserver:8443/test_client_regress/no_template_view/',
            status_code=301, target_status_code=200)
        # We can't use is_secure() or get_host()
        # because response.request is a dictionary, not an HttpRequest
        self.assertEqual(response.request.get('wsgi.url_scheme'), 'https')
        self.assertEqual(response.request.get('SERVER_NAME'), 'otherserver')
        self.assertEqual(response.request.get('SERVER_PORT'), '8443')

    def test_redirect_chain_on_non_redirect_page(self):
        "An assertion is raised if the original page couldn't be retrieved as expected"
        # This page will redirect with code 301, not 302
        response = self.client.get('/test_client/get_view/', follow=True)
        try:
            self.assertRedirects(response, '/test_client/get_view/')
        except AssertionError as e:
            self.assertIn("Response didn't redirect as expected: Response code was 200 (expected 302)", str(e))

        try:
            self.assertRedirects(response, '/test_client/get_view/', msg_prefix='abc')
        except AssertionError as e:
            self.assertIn("abc: Response didn't redirect as expected: Response code was 200 (expected 302)", str(e))

    def test_redirect_on_non_redirect_page(self):
        "An assertion is raised if the original page couldn't be retrieved as expected"
        # This page will redirect with code 301, not 302
        response = self.client.get('/test_client/get_view/')
        try:
            self.assertRedirects(response, '/test_client/get_view/')
        except AssertionError as e:
            self.assertIn("Response didn't redirect as expected: Response code was 200 (expected 302)", str(e))

        try:
            self.assertRedirects(response, '/test_client/get_view/', msg_prefix='abc')
        except AssertionError as e:
            self.assertIn("abc: Response didn't redirect as expected: Response code was 200 (expected 302)", str(e))


class AssertFormErrorTests(TestCase):
    def test_unknown_form(self):
        "An assertion is raised if the form name is unknown"
        post_data = {
            'text': 'Hello World',
            'email': 'not an email address',
            'value': 37,
            'single': 'b',
            'multi': ('b','c','e')
        }
        response = self.client.post('/test_client/form_view/', post_data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "Invalid POST Template")

        try:
            self.assertFormError(response, 'wrong_form', 'some_field', 'Some error.')
        except AssertionError as e:
            self.assertIn("The form 'wrong_form' was not used to render the response", str(e))
        try:
            self.assertFormError(response, 'wrong_form', 'some_field', 'Some error.', msg_prefix='abc')
        except AssertionError as e:
            self.assertIn("abc: The form 'wrong_form' was not used to render the response", str(e))

    def test_unknown_field(self):
        "An assertion is raised if the field name is unknown"
        post_data = {
            'text': 'Hello World',
            'email': 'not an email address',
            'value': 37,
            'single': 'b',
            'multi': ('b','c','e')
        }
        response = self.client.post('/test_client/form_view/', post_data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "Invalid POST Template")

        try:
            self.assertFormError(response, 'form', 'some_field', 'Some error.')
        except AssertionError as e:
            self.assertIn("The form 'form' in context 0 does not contain the field 'some_field'", str(e))
        try:
            self.assertFormError(response, 'form', 'some_field', 'Some error.', msg_prefix='abc')
        except AssertionError as e:
            self.assertIn("abc: The form 'form' in context 0 does not contain the field 'some_field'", str(e))

    def test_noerror_field(self):
        "An assertion is raised if the field doesn't have any errors"
        post_data = {
            'text': 'Hello World',
            'email': 'not an email address',
            'value': 37,
            'single': 'b',
            'multi': ('b','c','e')
        }
        response = self.client.post('/test_client/form_view/', post_data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "Invalid POST Template")

        try:
            self.assertFormError(response, 'form', 'value', 'Some error.')
        except AssertionError as e:
            self.assertIn("The field 'value' on form 'form' in context 0 contains no errors", str(e))
        try:
            self.assertFormError(response, 'form', 'value', 'Some error.', msg_prefix='abc')
        except AssertionError as e:
            self.assertIn("abc: The field 'value' on form 'form' in context 0 contains no errors", str(e))

    def test_unknown_error(self):
        "An assertion is raised if the field doesn't contain the provided error"
        post_data = {
            'text': 'Hello World',
            'email': 'not an email address',
            'value': 37,
            'single': 'b',
            'multi': ('b','c','e')
        }
        response = self.client.post('/test_client/form_view/', post_data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "Invalid POST Template")

        try:
            self.assertFormError(response, 'form', 'email', 'Some error.')
        except AssertionError as e:
            self.assertIn(str_prefix("The field 'email' on form 'form' in context 0 does not contain the error 'Some error.' (actual errors: [%(_)s'Enter a valid email address.'])"), str(e))
        try:
            self.assertFormError(response, 'form', 'email', 'Some error.', msg_prefix='abc')
        except AssertionError as e:
            self.assertIn(str_prefix("abc: The field 'email' on form 'form' in context 0 does not contain the error 'Some error.' (actual errors: [%(_)s'Enter a valid email address.'])"), str(e))

    def test_unknown_nonfield_error(self):
        """
        Checks that an assertion is raised if the form's non field errors
        doesn't contain the provided error.
        """
        post_data = {
            'text': 'Hello World',
            'email': 'not an email address',
            'value': 37,
            'single': 'b',
            'multi': ('b','c','e')
        }
        response = self.client.post('/test_client/form_view/', post_data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "Invalid POST Template")

        try:
            self.assertFormError(response, 'form', None, 'Some error.')
        except AssertionError as e:
            self.assertIn("The form 'form' in context 0 does not contain the non-field error 'Some error.' (actual errors: )", str(e))
        try:
            self.assertFormError(response, 'form', None, 'Some error.', msg_prefix='abc')
        except AssertionError as e:
            self.assertIn("abc: The form 'form' in context 0 does not contain the non-field error 'Some error.' (actual errors: )", str(e))

class AssertFormsetErrorTests(TestCase):
    msg_prefixes = [("", {}), ("abc: ", {"msg_prefix": "abc"})]
    def setUp(self):
        """Makes response object for testing field and non-field errors"""
        # For testing field and non-field errors
        self.response_form_errors = self.getResponse({
            'form-TOTAL_FORMS': '2',
            'form-INITIAL_FORMS': '2',
            'form-0-text': 'Raise non-field error',
            'form-0-email': 'not an email address',
            'form-0-value': 37,
            'form-0-single': 'b',
            'form-0-multi': ('b','c','e'),
            'form-1-text': 'Hello World',
            'form-1-email': 'email@domain.com',
            'form-1-value': 37,
            'form-1-single': 'b',
            'form-1-multi': ('b','c','e'),
        })
        # For testing non-form errors
        self.response_nonform_errors = self.getResponse({
            'form-TOTAL_FORMS': '2',
            'form-INITIAL_FORMS': '2',
            'form-0-text': 'Hello World',
            'form-0-email': 'email@domain.com',
            'form-0-value': 37,
            'form-0-single': 'b',
            'form-0-multi': ('b','c','e'),
            'form-1-text': 'Hello World',
            'form-1-email': 'email@domain.com',
            'form-1-value': 37,
            'form-1-single': 'b',
            'form-1-multi': ('b','c','e'),
        })

    def getResponse(self, post_data):
        response = self.client.post('/test_client/formset_view/', post_data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "Invalid POST Template")
        return response

    def test_unknown_formset(self):
        "An assertion is raised if the formset name is unknown"
        for prefix, kwargs in self.msg_prefixes:
            with self.assertRaises(AssertionError) as cm:
                self.assertFormsetError(self.response_form_errors,
                                        'wrong_formset',
                                        0,
                                        'Some_field',
                                        'Some error.',
                                        **kwargs)
            self.assertIn(prefix + "The formset 'wrong_formset' was not "
                                   "used to render the response",
                          str(cm.exception))

    def test_unknown_field(self):
        "An assertion is raised if the field name is unknown"
        for prefix, kwargs in self.msg_prefixes:
            with self.assertRaises(AssertionError) as cm:
                self.assertFormsetError(self.response_form_errors,
                                        'my_formset',
                                        0,
                                        'Some_field',
                                        'Some error.',
                                        **kwargs)
            self.assertIn(prefix + "The formset 'my_formset', "
                                   "form 0 in context 0 "
                                   "does not contain the field 'Some_field'",
                          str(cm.exception))

    def test_no_error_field(self):
        "An assertion is raised if the field doesn't have any errors"
        for prefix, kwargs in self.msg_prefixes:
            with self.assertRaises(AssertionError) as cm:
                self.assertFormsetError(self.response_form_errors,
                                        'my_formset',
                                        1,
                                        'value',
                                        'Some error.',
                                        **kwargs)
            self.assertIn(prefix + "The field 'value' "
                                   "on formset 'my_formset', form 1 "
                                   "in context 0 contains no errors",
                          str(cm.exception))

    def test_unknown_error(self):
        "An assertion is raised if the field doesn't contain the specified error"
        for prefix, kwargs in self.msg_prefixes:
            with self.assertRaises(AssertionError) as cm:
                self.assertFormsetError(self.response_form_errors,
                                        'my_formset',
                                        0,
                                        'email',
                                        'Some error.',
                                        **kwargs)
            self.assertIn(str_prefix(prefix + "The field 'email' "
                "on formset 'my_formset', form 0 in context 0 does not "
                "contain the error 'Some error.' (actual errors: "
                "[%(_)s'Enter a valid email address.'])"),
                str(cm.exception))

    def test_field_error(self):
        "No assertion is raised if the field contains the provided error"
        for prefix, kwargs in self.msg_prefixes:
            self.assertFormsetError(self.response_form_errors,
                                    'my_formset',
                                    0,
                                    'email',
                                    ['Enter a valid email address.'],
                                    **kwargs)

    def test_no_nonfield_error(self):
        "An assertion is raised if the formsets non-field errors doesn't contain any errors."
        for prefix, kwargs in self.msg_prefixes:
            with self.assertRaises(AssertionError) as cm:
                self.assertFormsetError(self.response_form_errors,
                                        'my_formset',
                                        1,
                                        None,
                                        'Some error.',
                                        **kwargs)
            self.assertIn(prefix + "The formset 'my_formset', form 1 in "
                                   "context 0 does not contain any "
                                   "non-field errors.",
                          str(cm.exception))

    def test_unknown_nonfield_error(self):
        "An assertion is raised if the formsets non-field errors doesn't contain the provided error."
        for prefix, kwargs in self.msg_prefixes:
            with self.assertRaises(AssertionError) as cm:
                self.assertFormsetError(self.response_form_errors,
                                        'my_formset',
                                        0,
                                        None,
                                        'Some error.',
                                        **kwargs)
            self.assertIn(str_prefix(prefix +
                "The formset 'my_formset', form 0 in context 0 does not "
                "contain the non-field error 'Some error.' (actual errors: "
                "[%(_)s'Non-field error.'])"), str(cm.exception))

    def test_nonfield_error(self):
        "No assertion is raised if the formsets non-field errors contains the provided error."
        for prefix, kwargs in self.msg_prefixes:
            self.assertFormsetError(self.response_form_errors,
                                    'my_formset',
                                    0,
                                    None,
                                    'Non-field error.',
                                    **kwargs)

    def test_no_nonform_error(self):
        "An assertion is raised if the formsets non-form errors doesn't contain any errors."
        for prefix, kwargs in self.msg_prefixes:
            with self.assertRaises(AssertionError) as cm:
                self.assertFormsetError(self.response_form_errors,
                                        'my_formset',
                                        None,
                                        None,
                                        'Some error.',
                                        **kwargs)
            self.assertIn(prefix + "The formset 'my_formset' in context 0 "
                                   "does not contain any non-form errors.",
                          str(cm.exception))

    def test_unknown_nonform_error(self):
        "An assertion is raised if the formsets non-form errors doesn't contain the provided error."
        for prefix, kwargs in self.msg_prefixes:
            with self.assertRaises(AssertionError) as cm:
                self.assertFormsetError(self.response_nonform_errors,
                                        'my_formset',
                                        None,
                                        None,
                                        'Some error.',
                                        **kwargs)
            self.assertIn(str_prefix(prefix +
                "The formset 'my_formset' in context 0 does not contain the "
                "non-form error 'Some error.' (actual errors: [%(_)s'Forms "
                "in a set must have distinct email addresses.'])"), str(cm.exception))

    def test_nonform_error(self):
        "No assertion is raised if the formsets non-form errors contains the provided error."
        for prefix, kwargs in self.msg_prefixes:
            self.assertFormsetError(self.response_nonform_errors,
                                    'my_formset',
                                    None,
                                    None,
                                    'Forms in a set must have distinct email '
                                    'addresses.',
                                    **kwargs)

@override_settings(PASSWORD_HASHERS=('django.contrib.auth.hashers.SHA1PasswordHasher',))
class LoginTests(TestCase):
    fixtures = ['testdata']

    def test_login_different_client(self):
        "Check that using a different test client doesn't violate authentication"

        # Create a second client, and log in.
        c = Client()
        login = c.login(username='testclient', password='password')
        self.assertTrue(login, 'Could not log in')

        # Get a redirection page with the second client.
        response = c.get("/test_client_regress/login_protected_redirect_view/")

        # At this points, the self.client isn't logged in.
        # Check that assertRedirects uses the original client, not the
        # default client.
        self.assertRedirects(response, "http://testserver/test_client_regress/get_view/")


@override_settings(
    PASSWORD_HASHERS=('django.contrib.auth.hashers.SHA1PasswordHasher',),
    SESSION_ENGINE='test_client_regress.session'
)
class SessionEngineTests(TestCase):
    fixtures = ['testdata']

    def test_login(self):
        "A session engine that modifies the session key can be used to log in"
        login = self.client.login(username='testclient', password='password')
        self.assertTrue(login, 'Could not log in')

        # Try to access a login protected page.
        response = self.client.get("/test_client/login_protected_view/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['user'].username, 'testclient')


class URLEscapingTests(TestCase):
    def test_simple_argument_get(self):
        "Get a view that has a simple string argument"
        response = self.client.get(reverse('arg_view', args=['Slartibartfast']))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'Howdy, Slartibartfast')

    def test_argument_with_space_get(self):
        "Get a view that has a string argument that requires escaping"
        response = self.client.get(reverse('arg_view', args=['Arthur Dent']))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'Hi, Arthur')

    def test_simple_argument_post(self):
        "Post for a view that has a simple string argument"
        response = self.client.post(reverse('arg_view', args=['Slartibartfast']))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'Howdy, Slartibartfast')

    def test_argument_with_space_post(self):
        "Post for a view that has a string argument that requires escaping"
        response = self.client.post(reverse('arg_view', args=['Arthur Dent']))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'Hi, Arthur')

@override_settings(PASSWORD_HASHERS=('django.contrib.auth.hashers.SHA1PasswordHasher',))
class ExceptionTests(TestCase):
    fixtures = ['testdata.json']

    def test_exception_cleared(self):
        "#5836 - A stale user exception isn't re-raised by the test client."

        login = self.client.login(username='testclient',password='password')
        self.assertTrue(login, 'Could not log in')
        try:
            response = self.client.get("/test_client_regress/staff_only/")
            self.fail("General users should not be able to visit this page")
        except CustomTestException:
            pass

        # At this point, an exception has been raised, and should be cleared.

        # This next operation should be successful; if it isn't we have a problem.
        login = self.client.login(username='staff', password='password')
        self.assertTrue(login, 'Could not log in')
        try:
            self.client.get("/test_client_regress/staff_only/")
        except CustomTestException:
            self.fail("Staff should be able to visit this page")


class TemplateExceptionTests(TestCase):
    def setUp(self):
        # Reset the loaders so they don't try to render cached templates.
        if loader.template_source_loaders is not None:
            for template_loader in loader.template_source_loaders:
                if hasattr(template_loader, 'reset'):
                    template_loader.reset()

    @override_settings(
        TEMPLATE_DIRS=(os.path.join(os.path.dirname(upath(__file__)), 'bad_templates'),)
    )
    def test_bad_404_template(self):
        "Errors found when rendering 404 error templates are re-raised"
        try:
            response = self.client.get("/no_such_view/")
            self.fail("Should get error about syntax error in template")
        except TemplateSyntaxError:
            pass

# We need two different tests to check URLconf substitution -  one to check
# it was changed, and another one (without self.urls) to check it was reverted on
# teardown. This pair of tests relies upon the alphabetical ordering of test execution.
class UrlconfSubstitutionTests(TestCase):
    urls = 'test_client_regress.urls'

    def test_urlconf_was_changed(self):
        "TestCase can enforce a custom URLconf on a per-test basis"
        url = reverse('arg_view', args=['somename'])
        self.assertEqual(url, '/arg_view/somename/')

# This test needs to run *after* UrlconfSubstitutionTests; the zz prefix in the
# name is to ensure alphabetical ordering.
class zzUrlconfSubstitutionTests(TestCase):
    def test_urlconf_was_reverted(self):
        "URLconf is reverted to original value after modification in a TestCase"
        url = reverse('arg_view', args=['somename'])
        self.assertEqual(url, '/test_client_regress/arg_view/somename/')

@override_settings(PASSWORD_HASHERS=('django.contrib.auth.hashers.SHA1PasswordHasher',))
class ContextTests(TestCase):
    fixtures = ['testdata']

    def test_single_context(self):
        "Context variables can be retrieved from a single context"
        response = self.client.get("/test_client_regress/request_data/", data={'foo':'whiz'})
        self.assertEqual(response.context.__class__, Context)
        self.assertTrue('get-foo' in response.context)
        self.assertEqual(response.context['get-foo'], 'whiz')
        self.assertEqual(response.context['request-foo'], 'whiz')
        self.assertEqual(response.context['data'], 'sausage')

        try:
            response.context['does-not-exist']
            self.fail('Should not be able to retrieve non-existent key')
        except KeyError as e:
            self.assertEqual(e.args[0], 'does-not-exist')

    def test_inherited_context(self):
        "Context variables can be retrieved from a list of contexts"
        response = self.client.get("/test_client_regress/request_data_extended/", data={'foo':'whiz'})
        self.assertEqual(response.context.__class__, ContextList)
        self.assertEqual(len(response.context), 2)
        self.assertTrue('get-foo' in response.context)
        self.assertEqual(response.context['get-foo'], 'whiz')
        self.assertEqual(response.context['request-foo'], 'whiz')
        self.assertEqual(response.context['data'], 'bacon')

        try:
            response.context['does-not-exist']
            self.fail('Should not be able to retrieve non-existent key')
        except KeyError as e:
            self.assertEqual(e.args[0], 'does-not-exist')

    def test_contextlist_keys(self):
        c1 = Context()
        c1.update({'hello': 'world', 'goodbye': 'john'})
        c1.update({'hello': 'dolly', 'dolly': 'parton'})
        c2 = Context()
        c2.update({'goodbye': 'world', 'python': 'rocks'})
        c2.update({'goodbye': 'dolly'})

        l = ContextList([c1, c2])
        # None, True and False are builtins of BaseContext, and present
        # in every Context without needing to be added.
        self.assertEqual(set(['None', 'True', 'False', 'hello', 'goodbye',
                              'python', 'dolly']),
                         l.keys())

    def test_15368(self):
        # Need to insert a context processor that assumes certain things about
        # the request instance. This triggers a bug caused by some ways of
        # copying RequestContext.
        try:
            django.template.context._standard_context_processors = (lambda request: {'path': request.special_path},)
            response = self.client.get("/test_client_regress/request_context_view/")
            self.assertContains(response, 'Path: /test_client_regress/request_context_view/')
        finally:
            django.template.context._standard_context_processors = None


@override_settings(PASSWORD_HASHERS=('django.contrib.auth.hashers.SHA1PasswordHasher',))
class SessionTests(TestCase):
    fixtures = ['testdata.json']

    def test_session(self):
        "The session isn't lost if a user logs in"
        # The session doesn't exist to start.
        response = self.client.get('/test_client_regress/check_session/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'NO')

        # This request sets a session variable.
        response = self.client.get('/test_client_regress/set_session/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'set_session')

        # Check that the session has been modified
        response = self.client.get('/test_client_regress/check_session/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'YES')

        # Log in
        login = self.client.login(username='testclient',password='password')
        self.assertTrue(login, 'Could not log in')

        # Session should still contain the modified value
        response = self.client.get('/test_client_regress/check_session/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'YES')

    def test_logout(self):
        """Logout should work whether the user is logged in or not (#9978)."""
        self.client.logout()
        login = self.client.login(username='testclient',password='password')
        self.assertTrue(login, 'Could not log in')
        self.client.logout()
        self.client.logout()

    def test_logout_with_user(self):
        """Logout should send user_logged_out signal if user was logged in."""
        def listener(*args, **kwargs):
            listener.executed = True
            self.assertEqual(kwargs['sender'], User)
        listener.executed = False

        user_logged_out.connect(listener)
        self.client.login(username='testclient', password='password')
        self.client.logout()
        user_logged_out.disconnect(listener)
        self.assertTrue(listener.executed)

    @override_settings(AUTH_USER_MODEL='test_client_regress.CustomUser')
    def test_logout_with_custom_user(self):
        """Logout should send user_logged_out signal if custom user was logged in."""
        def listener(*args, **kwargs):
            self.assertEqual(kwargs['sender'], CustomUser)
            listener.executed = True
        listener.executed = False
        u = CustomUser.custom_objects.create(email='test@test.com')
        u.set_password('password')
        u.save()

        user_logged_out.connect(listener)
        self.client.login(username='test@test.com', password='password')
        self.client.logout()
        user_logged_out.disconnect(listener)
        self.assertTrue(listener.executed)

    def test_logout_without_user(self):
        """Logout should send signal even if user not authenticated."""
        def listener(user, *args, **kwargs):
            listener.user = user
            listener.executed = True
        listener.executed = False

        user_logged_out.connect(listener)
        self.client.login(username='incorrect', password='password')
        self.client.logout()
        user_logged_out.disconnect(listener)

        self.assertTrue(listener.executed)
        self.assertIsNone(listener.user)

    def test_login_with_user(self):
        """Login should send user_logged_in signal on successful login."""
        def listener(*args, **kwargs):
            listener.executed = True
        listener.executed = False

        user_logged_in.connect(listener)
        self.client.login(username='testclient', password='password')
        user_logged_out.disconnect(listener)

        self.assertTrue(listener.executed)

    def test_login_without_signal(self):
        """Login shouldn't send signal if user wasn't logged in"""
        def listener(*args, **kwargs):
            listener.executed = True
        listener.executed = False

        user_logged_in.connect(listener)
        self.client.login(username='incorrect', password='password')
        user_logged_in.disconnect(listener)

        self.assertFalse(listener.executed)


class RequestMethodTests(TestCase):
    def test_get(self):
        "Request a view via request method GET"
        response = self.client.get('/test_client_regress/request_methods/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'request method: GET')

    def test_post(self):
        "Request a view via request method POST"
        response = self.client.post('/test_client_regress/request_methods/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'request method: POST')

    def test_head(self):
        "Request a view via request method HEAD"
        response = self.client.head('/test_client_regress/request_methods/')
        self.assertEqual(response.status_code, 200)
        # A HEAD request doesn't return any content.
        self.assertNotEqual(response.content, b'request method: HEAD')
        self.assertEqual(response.content, b'')

    def test_options(self):
        "Request a view via request method OPTIONS"
        response = self.client.options('/test_client_regress/request_methods/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'request method: OPTIONS')

    def test_put(self):
        "Request a view via request method PUT"
        response = self.client.put('/test_client_regress/request_methods/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'request method: PUT')

    def test_delete(self):
        "Request a view via request method DELETE"
        response = self.client.delete('/test_client_regress/request_methods/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'request method: DELETE')

    def test_patch(self):
        "Request a view via request method PATCH"
        response = self.client.patch('/test_client_regress/request_methods/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'request method: PATCH')


class RequestMethodStringDataTests(TestCase):
    def test_post(self):
        "Request a view with string data via request method POST"
        # Regression test for #11371
        data = '{"test": "json"}'
        response = self.client.post('/test_client_regress/request_methods/', data=data, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'request method: POST')

    def test_put(self):
        "Request a view with string data via request method PUT"
        # Regression test for #11371
        data = '{"test": "json"}'
        response = self.client.put('/test_client_regress/request_methods/', data=data, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'request method: PUT')

    def test_patch(self):
        "Request a view with string data via request method PATCH"
        # Regression test for #17797
        data = '{"test": "json"}'
        response = self.client.patch('/test_client_regress/request_methods/', data=data, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'request method: PATCH')

class QueryStringTests(TestCase):
    def test_get_like_requests(self):
        # See: https://code.djangoproject.com/ticket/10571.
        for method_name in ('get', 'head'):
            # A GET-like request can pass a query string as data
            method = getattr(self.client, method_name)
            response = method("/test_client_regress/request_data/", data={'foo':'whiz'})
            self.assertEqual(response.context['get-foo'], 'whiz')
            self.assertEqual(response.context['request-foo'], 'whiz')

            # A GET-like request can pass a query string as part of the URL
            response = method("/test_client_regress/request_data/?foo=whiz")
            self.assertEqual(response.context['get-foo'], 'whiz')
            self.assertEqual(response.context['request-foo'], 'whiz')

            # Data provided in the URL to a GET-like request is overridden by actual form data
            response = method("/test_client_regress/request_data/?foo=whiz", data={'foo':'bang'})
            self.assertEqual(response.context['get-foo'], 'bang')
            self.assertEqual(response.context['request-foo'], 'bang')

            response = method("/test_client_regress/request_data/?foo=whiz", data={'bar':'bang'})
            self.assertEqual(response.context['get-foo'], None)
            self.assertEqual(response.context['get-bar'], 'bang')
            self.assertEqual(response.context['request-foo'], None)
            self.assertEqual(response.context['request-bar'], 'bang')

    def test_post_like_requests(self):
        # A POST-like request can pass a query string as data
        response = self.client.post("/test_client_regress/request_data/", data={'foo':'whiz'})
        self.assertEqual(response.context['get-foo'], None)
        self.assertEqual(response.context['post-foo'], 'whiz')

        # A POST-like request can pass a query string as part of the URL
        response = self.client.post("/test_client_regress/request_data/?foo=whiz")
        self.assertEqual(response.context['get-foo'], 'whiz')
        self.assertEqual(response.context['post-foo'], None)
        self.assertEqual(response.context['request-foo'], 'whiz')

        # POST data provided in the URL augments actual form data
        response = self.client.post("/test_client_regress/request_data/?foo=whiz", data={'foo':'bang'})
        self.assertEqual(response.context['get-foo'], 'whiz')
        self.assertEqual(response.context['post-foo'], 'bang')
        self.assertEqual(response.context['request-foo'], 'bang')

        response = self.client.post("/test_client_regress/request_data/?foo=whiz", data={'bar':'bang'})
        self.assertEqual(response.context['get-foo'], 'whiz')
        self.assertEqual(response.context['get-bar'], None)
        self.assertEqual(response.context['post-foo'], None)
        self.assertEqual(response.context['post-bar'], 'bang')
        self.assertEqual(response.context['request-foo'], 'whiz')
        self.assertEqual(response.context['request-bar'], 'bang')

class UnicodePayloadTests(TestCase):
    def test_simple_unicode_payload(self):
        "A simple ASCII-only unicode JSON document can be POSTed"
        # Regression test for #10571
        json = '{"english": "mountain pass"}'
        response = self.client.post("/test_client_regress/parse_unicode_json/", json,
                                    content_type="application/json")
        self.assertEqual(response.content, json.encode())

    def test_unicode_payload_utf8(self):
        "A non-ASCII unicode data encoded as UTF-8 can be POSTed"
        # Regression test for #10571
        json = '{"dog": "собака"}'
        response = self.client.post("/test_client_regress/parse_unicode_json/", json,
                                    content_type="application/json; charset=utf-8")
        self.assertEqual(response.content, json.encode('utf-8'))

    def test_unicode_payload_utf16(self):
        "A non-ASCII unicode data encoded as UTF-16 can be POSTed"
        # Regression test for #10571
        json = '{"dog": "собака"}'
        response = self.client.post("/test_client_regress/parse_unicode_json/", json,
                                    content_type="application/json; charset=utf-16")
        self.assertEqual(response.content, json.encode('utf-16'))

    def test_unicode_payload_non_utf(self):
        "A non-ASCII unicode data as a non-UTF based encoding can be POSTed"
        #Regression test for #10571
        json = '{"dog": "собака"}'
        response = self.client.post("/test_client_regress/parse_unicode_json/", json,
                                    content_type="application/json; charset=koi8-r")
        self.assertEqual(response.content, json.encode('koi8-r'))

class DummyFile(object):
    def __init__(self, filename):
        self.name = filename
    def read(self):
        return b'TEST_FILE_CONTENT'

class UploadedFileEncodingTest(TestCase):
    def test_file_encoding(self):
        encoded_file = encode_file('TEST_BOUNDARY', 'TEST_KEY', DummyFile('test_name.bin'))
        self.assertEqual(b'--TEST_BOUNDARY', encoded_file[0])
        self.assertEqual(b'Content-Disposition: form-data; name="TEST_KEY"; filename="test_name.bin"', encoded_file[1])
        self.assertEqual(b'TEST_FILE_CONTENT', encoded_file[-1])

    def test_guesses_content_type_on_file_encoding(self):
        self.assertEqual(b'Content-Type: application/octet-stream',
                         encode_file('IGNORE', 'IGNORE', DummyFile("file.bin"))[2])
        self.assertEqual(b'Content-Type: text/plain',
                         encode_file('IGNORE', 'IGNORE', DummyFile("file.txt"))[2])
        self.assertIn(encode_file('IGNORE', 'IGNORE', DummyFile("file.zip"))[2], (
                        b'Content-Type: application/x-compress',
                        b'Content-Type: application/x-zip',
                        b'Content-Type: application/x-zip-compressed',
                        b'Content-Type: application/zip',))
        self.assertEqual(b'Content-Type: application/octet-stream',
                         encode_file('IGNORE', 'IGNORE', DummyFile("file.unknown"))[2])

class RequestHeadersTest(TestCase):
    def test_client_headers(self):
        "A test client can receive custom headers"
        response = self.client.get("/test_client_regress/check_headers/", HTTP_X_ARG_CHECK='Testing 123')
        self.assertEqual(response.content, b"HTTP_X_ARG_CHECK: Testing 123")
        self.assertEqual(response.status_code, 200)

    def test_client_headers_redirect(self):
        "Test client headers are preserved through redirects"
        response = self.client.get("/test_client_regress/check_headers_redirect/", follow=True, HTTP_X_ARG_CHECK='Testing 123')
        self.assertEqual(response.content, b"HTTP_X_ARG_CHECK: Testing 123")
        self.assertRedirects(response, '/test_client_regress/check_headers/',
            status_code=301, target_status_code=200)


class ReadLimitedStreamTest(TestCase):
    """
    Tests that ensure that HttpRequest.body, HttpRequest.read() and
    HttpRequest.read(BUFFER) have proper LimitedStream behavior.

    Refs #14753, #15785
    """

    def test_body_from_empty_request(self):
        """HttpRequest.body on a test client GET request should return
        the empty string."""
        self.assertEqual(self.client.get("/test_client_regress/body/").content, b'')

    def test_read_from_empty_request(self):
        """HttpRequest.read() on a test client GET request should return the
        empty string."""
        self.assertEqual(self.client.get("/test_client_regress/read_all/").content, b'')

    def test_read_numbytes_from_empty_request(self):
        """HttpRequest.read(LARGE_BUFFER) on a test client GET request should
        return the empty string."""
        self.assertEqual(self.client.get("/test_client_regress/read_buffer/").content, b'')

    def test_read_from_nonempty_request(self):
        """HttpRequest.read() on a test client PUT request with some payload
        should return that payload."""
        payload = b'foobar'
        self.assertEqual(self.client.put("/test_client_regress/read_all/",
                                          data=payload,
                                          content_type='text/plain').content, payload)

    def test_read_numbytes_from_nonempty_request(self):
        """HttpRequest.read(LARGE_BUFFER) on a test client PUT request with
        some payload should return that payload."""
        payload = b'foobar'
        self.assertEqual(self.client.put("/test_client_regress/read_buffer/",
                                          data=payload,
                                          content_type='text/plain').content, payload)


class RequestFactoryStateTest(TestCase):
    """Regression tests for #15929."""
    # These tests are checking that certain middleware don't change certain
    # global state. Alternatively, from the point of view of a test, they are
    # ensuring test isolation behavior. So, unusually, it doesn't make sense to
    # run the tests individually, and if any are failing it is confusing to run
    # them with any other set of tests.

    def common_test_that_should_always_pass(self):
        request = RequestFactory().get('/')
        request.session = {}
        self.assertFalse(hasattr(request, 'user'))

    def test_request(self):
        self.common_test_that_should_always_pass()

    def test_request_after_client(self):
        # apart from the next line the three tests are identical
        self.client.get('/')
        self.common_test_that_should_always_pass()

    def test_request_after_client_2(self):
        # This test is executed after the previous one
        self.common_test_that_should_always_pass()


class RequestFactoryEnvironmentTests(TestCase):
    """
    Regression tests for #8551 and #17067: ensure that environment variables
    are set correctly in RequestFactory.
    """

    def test_should_set_correct_env_variables(self):
        request = RequestFactory().get('/path/')

        self.assertEqual(request.META.get('REMOTE_ADDR'), '127.0.0.1')
        self.assertEqual(request.META.get('SERVER_NAME'), 'testserver')
        self.assertEqual(request.META.get('SERVER_PORT'), '80')
        self.assertEqual(request.META.get('SERVER_PROTOCOL'), 'HTTP/1.1')
        self.assertEqual(request.META.get('SCRIPT_NAME') +
                         request.META.get('PATH_INFO'), '/path/')
