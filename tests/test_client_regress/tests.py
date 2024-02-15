"""
Regression tests for the Test Client, especially the customized assertions.
"""

import itertools
import os

from django.contrib.auth.models import User
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.http import HttpResponse
from django.template import Context, RequestContext, TemplateSyntaxError, engines
from django.template.response import SimpleTemplateResponse
from django.test import (
    Client,
    SimpleTestCase,
    TestCase,
    modify_settings,
    override_settings,
)
from django.test.client import RedirectCycleError, RequestFactory, encode_file
from django.test.utils import ContextList
from django.urls import NoReverseMatch, reverse
from django.utils.translation import gettext_lazy

from .models import CustomUser
from .views import CustomTestException


class TestDataMixin:
    @classmethod
    def setUpTestData(cls):
        cls.u1 = User.objects.create_user(username="testclient", password="password")
        cls.staff = User.objects.create_user(
            username="staff", password="password", is_staff=True
        )


@override_settings(ROOT_URLCONF="test_client_regress.urls")
class AssertContainsTests(SimpleTestCase):
    def test_contains(self):
        "Responses can be inspected for content, including counting repeated substrings"
        response = self.client.get("/no_template_view/")

        self.assertNotContains(response, "never")
        self.assertContains(response, "never", 0)
        self.assertContains(response, "once")
        self.assertContains(response, "once", 1)
        self.assertContains(response, "twice")
        self.assertContains(response, "twice", 2)

        try:
            self.assertContains(response, "text", status_code=999)
        except AssertionError as e:
            self.assertIn(
                "Couldn't retrieve content: Response code was 200 (expected 999)",
                str(e),
            )
        try:
            self.assertContains(response, "text", status_code=999, msg_prefix="abc")
        except AssertionError as e:
            self.assertIn(
                "abc: Couldn't retrieve content: Response code was 200 (expected 999)",
                str(e),
            )

        try:
            self.assertNotContains(response, "text", status_code=999)
        except AssertionError as e:
            self.assertIn(
                "Couldn't retrieve content: Response code was 200 (expected 999)",
                str(e),
            )
        try:
            self.assertNotContains(response, "text", status_code=999, msg_prefix="abc")
        except AssertionError as e:
            self.assertIn(
                "abc: Couldn't retrieve content: Response code was 200 (expected 999)",
                str(e),
            )

        try:
            self.assertNotContains(response, "once")
        except AssertionError as e:
            self.assertIn(
                "'once' unexpectedly found in the following response\n"
                f"{response.content}",
                str(e),
            )
        try:
            self.assertNotContains(response, "once", msg_prefix="abc")
        except AssertionError as e:
            self.assertIn(
                "abc: 'once' unexpectedly found in the following response\n"
                f"{response.content}",
                str(e),
            )

        try:
            self.assertContains(response, "never", 1)
        except AssertionError as e:
            self.assertIn(
                "Found 0 instances of 'never' (expected 1) in the following response\n"
                f"{response.content}",
                str(e),
            )
        try:
            self.assertContains(response, "never", 1, msg_prefix="abc")
        except AssertionError as e:
            self.assertIn(
                "abc: Found 0 instances of 'never' (expected 1) in the following "
                f"response\n{response.content}",
                str(e),
            )

        try:
            self.assertContains(response, "once", 0)
        except AssertionError as e:
            self.assertIn(
                "Found 1 instances of 'once' (expected 0) in the following response\n"
                f"{response.content}",
                str(e),
            )
        try:
            self.assertContains(response, "once", 0, msg_prefix="abc")
        except AssertionError as e:
            self.assertIn(
                "abc: Found 1 instances of 'once' (expected 0) in the following "
                f"response\n{response.content}",
                str(e),
            )

        try:
            self.assertContains(response, "once", 2)
        except AssertionError as e:
            self.assertIn(
                "Found 1 instances of 'once' (expected 2) in the following response\n"
                f"{response.content}",
                str(e),
            )
        try:
            self.assertContains(response, "once", 2, msg_prefix="abc")
        except AssertionError as e:
            self.assertIn(
                "abc: Found 1 instances of 'once' (expected 2) in the following "
                f"response\n{response.content}",
                str(e),
            )

        try:
            self.assertContains(response, "twice", 1)
        except AssertionError as e:
            self.assertIn(
                "Found 2 instances of 'twice' (expected 1) in the following response\n"
                f"{response.content}",
                str(e),
            )
        try:
            self.assertContains(response, "twice", 1, msg_prefix="abc")
        except AssertionError as e:
            self.assertIn(
                "abc: Found 2 instances of 'twice' (expected 1) in the following "
                f"response\n{response.content}",
                str(e),
            )

        try:
            self.assertContains(response, "thrice")
        except AssertionError as e:
            self.assertIn(
                f"Couldn't find 'thrice' in the following response\n{response.content}",
                str(e),
            )
        try:
            self.assertContains(response, "thrice", msg_prefix="abc")
        except AssertionError as e:
            self.assertIn(
                "abc: Couldn't find 'thrice' in the following response\n"
                f"{response.content}",
                str(e),
            )

        try:
            self.assertContains(response, "thrice", 3)
        except AssertionError as e:
            self.assertIn(
                "Found 0 instances of 'thrice' (expected 3) in the following response\n"
                f"{response.content}",
                str(e),
            )
        try:
            self.assertContains(response, "thrice", 3, msg_prefix="abc")
        except AssertionError as e:
            self.assertIn(
                "abc: Found 0 instances of 'thrice' (expected 3) in the following "
                f"response\n{response.content}",
                str(e),
            )

        long_content = (
            b"This is a very very very very very very very very long message which "
            b"exceedes the max limit of truncation."
        )
        response = HttpResponse(long_content)
        msg = f"Couldn't find 'thrice' in the following response\n{long_content}"
        with self.assertRaisesMessage(AssertionError, msg):
            self.assertContains(response, "thrice")

        msg = (
            "Found 1 instances of 'This' (expected 3) in the following response\n"
            f"{long_content}"
        )
        with self.assertRaisesMessage(AssertionError, msg):
            self.assertContains(response, "This", 3)

        msg = f"'very' unexpectedly found in the following response\n{long_content}"
        with self.assertRaisesMessage(AssertionError, msg):
            self.assertNotContains(response, "very")

    def test_unicode_contains(self):
        "Unicode characters can be found in template context"
        # Regression test for #10183
        r = self.client.get("/check_unicode/")
        self.assertContains(r, "さかき")
        self.assertContains(r, b"\xe5\xb3\xa0".decode())

    def test_unicode_not_contains(self):
        "Unicode characters can be searched for, and not found in template context"
        # Regression test for #10183
        r = self.client.get("/check_unicode/")
        self.assertNotContains(r, "はたけ")
        self.assertNotContains(r, b"\xe3\x81\xaf\xe3\x81\x9f\xe3\x81\x91".decode())

    def test_binary_contains(self):
        r = self.client.get("/check_binary/")
        self.assertContains(r, b"%PDF-1.4\r\n%\x93\x8c\x8b\x9e")
        with self.assertRaises(AssertionError):
            self.assertContains(r, b"%PDF-1.4\r\n%\x93\x8c\x8b\x9e", count=2)

    def test_binary_not_contains(self):
        r = self.client.get("/check_binary/")
        self.assertNotContains(r, b"%ODF-1.4\r\n%\x93\x8c\x8b\x9e")
        with self.assertRaises(AssertionError):
            self.assertNotContains(r, b"%PDF-1.4\r\n%\x93\x8c\x8b\x9e")

    def test_nontext_contains(self):
        r = self.client.get("/no_template_view/")
        self.assertContains(r, gettext_lazy("once"))

    def test_nontext_not_contains(self):
        r = self.client.get("/no_template_view/")
        self.assertNotContains(r, gettext_lazy("never"))

    def test_assert_contains_renders_template_response(self):
        """
        An unrendered SimpleTemplateResponse may be used in assertContains().
        """
        template = engines["django"].from_string("Hello")
        response = SimpleTemplateResponse(template)
        self.assertContains(response, "Hello")

    def test_assert_contains_using_non_template_response(self):
        """auto-rendering does not affect responses that aren't
        instances (or subclasses) of SimpleTemplateResponse.
        Refs #15826.
        """
        response = HttpResponse("Hello")
        self.assertContains(response, "Hello")

    def test_assert_not_contains_renders_template_response(self):
        """
        An unrendered SimpleTemplateResponse may be used in assertNotContains().
        """
        template = engines["django"].from_string("Hello")
        response = SimpleTemplateResponse(template)
        self.assertNotContains(response, "Bye")

    def test_assert_not_contains_using_non_template_response(self):
        """
        auto-rendering does not affect responses that aren't instances (or
        subclasses) of SimpleTemplateResponse.
        """
        response = HttpResponse("Hello")
        self.assertNotContains(response, "Bye")


@override_settings(ROOT_URLCONF="test_client_regress.urls")
class AssertTemplateUsedTests(TestDataMixin, TestCase):
    def test_no_context(self):
        "Template usage assertions work then templates aren't in use"
        response = self.client.get("/no_template_view/")

        # The no template case doesn't mess with the template assertions
        self.assertTemplateNotUsed(response, "GET Template")

        try:
            self.assertTemplateUsed(response, "GET Template")
        except AssertionError as e:
            self.assertIn("No templates used to render the response", str(e))

        try:
            self.assertTemplateUsed(response, "GET Template", msg_prefix="abc")
        except AssertionError as e:
            self.assertIn("abc: No templates used to render the response", str(e))

        msg = "No templates used to render the response"
        with self.assertRaisesMessage(AssertionError, msg):
            self.assertTemplateUsed(response, "GET Template", count=2)

    def test_single_context(self):
        "Template assertions work when there is a single context"
        response = self.client.get("/post_view/", {})
        msg = (
            ": Template 'Empty GET Template' was used unexpectedly in "
            "rendering the response"
        )
        with self.assertRaisesMessage(AssertionError, msg):
            self.assertTemplateNotUsed(response, "Empty GET Template")
        with self.assertRaisesMessage(AssertionError, "abc" + msg):
            self.assertTemplateNotUsed(response, "Empty GET Template", msg_prefix="abc")
        msg = (
            ": Template 'Empty POST Template' was not a template used to "
            "render the response. Actual template(s) used: Empty GET Template"
        )
        with self.assertRaisesMessage(AssertionError, msg):
            self.assertTemplateUsed(response, "Empty POST Template")
        with self.assertRaisesMessage(AssertionError, "abc" + msg):
            self.assertTemplateUsed(response, "Empty POST Template", msg_prefix="abc")
        msg = (
            ": Template 'Empty GET Template' was expected to be rendered 2 "
            "time(s) but was actually rendered 1 time(s)."
        )
        with self.assertRaisesMessage(AssertionError, msg):
            self.assertTemplateUsed(response, "Empty GET Template", count=2)
        with self.assertRaisesMessage(AssertionError, "abc" + msg):
            self.assertTemplateUsed(
                response, "Empty GET Template", msg_prefix="abc", count=2
            )

    def test_multiple_context(self):
        "Template assertions work when there are multiple contexts"
        post_data = {
            "text": "Hello World",
            "email": "foo@example.com",
            "value": 37,
            "single": "b",
            "multi": ("b", "c", "e"),
        }
        response = self.client.post("/form_view_with_template/", post_data)
        self.assertContains(response, "POST data OK")
        msg = "Template '%s' was used unexpectedly in rendering the response"
        with self.assertRaisesMessage(AssertionError, msg % "form_view.html"):
            self.assertTemplateNotUsed(response, "form_view.html")
        with self.assertRaisesMessage(AssertionError, msg % "base.html"):
            self.assertTemplateNotUsed(response, "base.html")
        msg = (
            "Template 'Valid POST Template' was not a template used to render "
            "the response. Actual template(s) used: form_view.html, base.html"
        )
        with self.assertRaisesMessage(AssertionError, msg):
            self.assertTemplateUsed(response, "Valid POST Template")
        msg = (
            "Template 'base.html' was expected to be rendered 2 time(s) but "
            "was actually rendered 1 time(s)."
        )
        with self.assertRaisesMessage(AssertionError, msg):
            self.assertTemplateUsed(response, "base.html", count=2)

    def test_template_rendered_multiple_times(self):
        """Template assertions work when a template is rendered multiple times."""
        response = self.client.get("/render_template_multiple_times/")

        self.assertTemplateUsed(response, "base.html", count=2)


@override_settings(ROOT_URLCONF="test_client_regress.urls")
class AssertRedirectsTests(SimpleTestCase):
    def test_redirect_page(self):
        "An assertion is raised if the original page couldn't be retrieved as expected"
        # This page will redirect with code 301, not 302
        response = self.client.get("/permanent_redirect_view/")
        try:
            self.assertRedirects(response, "/get_view/")
        except AssertionError as e:
            self.assertIn(
                "Response didn't redirect as expected: Response code was 301 "
                "(expected 302)",
                str(e),
            )

        try:
            self.assertRedirects(response, "/get_view/", msg_prefix="abc")
        except AssertionError as e:
            self.assertIn(
                "abc: Response didn't redirect as expected: Response code was 301 "
                "(expected 302)",
                str(e),
            )

    def test_lost_query(self):
        """
        An assertion is raised if the redirect location doesn't preserve GET
        parameters.
        """
        response = self.client.get("/redirect_view/", {"var": "value"})
        try:
            self.assertRedirects(response, "/get_view/")
        except AssertionError as e:
            self.assertIn(
                "Response redirected to '/get_view/?var=value', expected '/get_view/'",
                str(e),
            )

        try:
            self.assertRedirects(response, "/get_view/", msg_prefix="abc")
        except AssertionError as e:
            self.assertIn(
                "abc: Response redirected to '/get_view/?var=value', expected "
                "'/get_view/'",
                str(e),
            )

    def test_incorrect_target(self):
        "An assertion is raised if the response redirects to another target"
        response = self.client.get("/permanent_redirect_view/")
        try:
            # Should redirect to get_view
            self.assertRedirects(response, "/some_view/")
        except AssertionError as e:
            self.assertIn(
                "Response didn't redirect as expected: Response code was 301 "
                "(expected 302)",
                str(e),
            )

    def test_target_page(self):
        """
        An assertion is raised if the response redirect target cannot be
        retrieved as expected.
        """
        response = self.client.get("/double_redirect_view/")
        try:
            # The redirect target responds with a 301 code, not 200
            self.assertRedirects(response, "http://testserver/permanent_redirect_view/")
        except AssertionError as e:
            self.assertIn(
                "Couldn't retrieve redirection page '/permanent_redirect_view/': "
                "response code was 301 (expected 200)",
                str(e),
            )

        try:
            # The redirect target responds with a 301 code, not 200
            self.assertRedirects(
                response, "http://testserver/permanent_redirect_view/", msg_prefix="abc"
            )
        except AssertionError as e:
            self.assertIn(
                "abc: Couldn't retrieve redirection page '/permanent_redirect_view/': "
                "response code was 301 (expected 200)",
                str(e),
            )

    def test_redirect_chain(self):
        "You can follow a redirect chain of multiple redirects"
        response = self.client.get("/redirects/further/more/", {}, follow=True)
        self.assertRedirects(
            response, "/no_template_view/", status_code=302, target_status_code=200
        )

        self.assertEqual(len(response.redirect_chain), 1)
        self.assertEqual(response.redirect_chain[0], ("/no_template_view/", 302))

    def test_multiple_redirect_chain(self):
        "You can follow a redirect chain of multiple redirects"
        response = self.client.get("/redirects/", {}, follow=True)
        self.assertRedirects(
            response, "/no_template_view/", status_code=302, target_status_code=200
        )

        self.assertEqual(len(response.redirect_chain), 3)
        self.assertEqual(response.redirect_chain[0], ("/redirects/further/", 302))
        self.assertEqual(response.redirect_chain[1], ("/redirects/further/more/", 302))
        self.assertEqual(response.redirect_chain[2], ("/no_template_view/", 302))

    def test_redirect_chain_to_non_existent(self):
        "You can follow a chain to a nonexistent view."
        response = self.client.get("/redirect_to_non_existent_view2/", {}, follow=True)
        self.assertRedirects(
            response, "/non_existent_view/", status_code=302, target_status_code=404
        )

    def test_redirect_chain_to_self(self):
        "Redirections to self are caught and escaped"
        with self.assertRaises(RedirectCycleError) as context:
            self.client.get("/redirect_to_self/", {}, follow=True)
        response = context.exception.last_response
        # The chain of redirects stops once the cycle is detected.
        self.assertRedirects(
            response, "/redirect_to_self/", status_code=302, target_status_code=302
        )
        self.assertEqual(len(response.redirect_chain), 2)

    def test_redirect_to_self_with_changing_query(self):
        "Redirections don't loop forever even if query is changing"
        with self.assertRaises(RedirectCycleError):
            self.client.get(
                "/redirect_to_self_with_changing_query_view/",
                {"counter": "0"},
                follow=True,
            )

    def test_circular_redirect(self):
        "Circular redirect chains are caught and escaped"
        with self.assertRaises(RedirectCycleError) as context:
            self.client.get("/circular_redirect_1/", {}, follow=True)
        response = context.exception.last_response
        # The chain of redirects will get back to the starting point, but stop there.
        self.assertRedirects(
            response, "/circular_redirect_2/", status_code=302, target_status_code=302
        )
        self.assertEqual(len(response.redirect_chain), 4)

    def test_redirect_chain_post(self):
        "A redirect chain will be followed from an initial POST post"
        response = self.client.post("/redirects/", {"nothing": "to_send"}, follow=True)
        self.assertRedirects(response, "/no_template_view/", 302, 200)
        self.assertEqual(len(response.redirect_chain), 3)

    def test_redirect_chain_head(self):
        "A redirect chain will be followed from an initial HEAD request"
        response = self.client.head("/redirects/", {"nothing": "to_send"}, follow=True)
        self.assertRedirects(response, "/no_template_view/", 302, 200)
        self.assertEqual(len(response.redirect_chain), 3)

    def test_redirect_chain_options(self):
        "A redirect chain will be followed from an initial OPTIONS request"
        response = self.client.options("/redirects/", follow=True)
        self.assertRedirects(response, "/no_template_view/", 302, 200)
        self.assertEqual(len(response.redirect_chain), 3)

    def test_redirect_chain_put(self):
        "A redirect chain will be followed from an initial PUT request"
        response = self.client.put("/redirects/", follow=True)
        self.assertRedirects(response, "/no_template_view/", 302, 200)
        self.assertEqual(len(response.redirect_chain), 3)

    def test_redirect_chain_delete(self):
        "A redirect chain will be followed from an initial DELETE request"
        response = self.client.delete("/redirects/", follow=True)
        self.assertRedirects(response, "/no_template_view/", 302, 200)
        self.assertEqual(len(response.redirect_chain), 3)

    @modify_settings(ALLOWED_HOSTS={"append": "otherserver"})
    def test_redirect_to_different_host(self):
        "The test client will preserve scheme, host and port changes"
        response = self.client.get("/redirect_other_host/", follow=True)
        self.assertRedirects(
            response,
            "https://otherserver:8443/no_template_view/",
            status_code=302,
            target_status_code=200,
        )
        # We can't use is_secure() or get_host()
        # because response.request is a dictionary, not an HttpRequest
        self.assertEqual(response.request.get("wsgi.url_scheme"), "https")
        self.assertEqual(response.request.get("SERVER_NAME"), "otherserver")
        self.assertEqual(response.request.get("SERVER_PORT"), "8443")
        # assertRedirects() can follow redirect to 'otherserver' too.
        response = self.client.get("/redirect_other_host/", follow=False)
        self.assertRedirects(
            response,
            "https://otherserver:8443/no_template_view/",
            status_code=302,
            target_status_code=200,
        )

    def test_redirect_chain_on_non_redirect_page(self):
        """
        An assertion is raised if the original page couldn't be retrieved as
        expected.
        """
        # This page will redirect with code 301, not 302
        response = self.client.get("/get_view/", follow=True)
        try:
            self.assertRedirects(response, "/get_view/")
        except AssertionError as e:
            self.assertIn(
                "Response didn't redirect as expected: Response code was 200 "
                "(expected 302)",
                str(e),
            )

        try:
            self.assertRedirects(response, "/get_view/", msg_prefix="abc")
        except AssertionError as e:
            self.assertIn(
                "abc: Response didn't redirect as expected: Response code was 200 "
                "(expected 302)",
                str(e),
            )

    def test_redirect_on_non_redirect_page(self):
        "An assertion is raised if the original page couldn't be retrieved as expected"
        # This page will redirect with code 301, not 302
        response = self.client.get("/get_view/")
        try:
            self.assertRedirects(response, "/get_view/")
        except AssertionError as e:
            self.assertIn(
                "Response didn't redirect as expected: Response code was 200 "
                "(expected 302)",
                str(e),
            )

        try:
            self.assertRedirects(response, "/get_view/", msg_prefix="abc")
        except AssertionError as e:
            self.assertIn(
                "abc: Response didn't redirect as expected: Response code was 200 "
                "(expected 302)",
                str(e),
            )

    def test_redirect_scheme(self):
        """
        An assertion is raised if the response doesn't have the scheme
        specified in expected_url.
        """

        # For all possible True/False combinations of follow and secure
        for follow, secure in itertools.product([True, False], repeat=2):
            # always redirects to https
            response = self.client.get(
                "/https_redirect_view/", follow=follow, secure=secure
            )
            # the goal scheme is https
            self.assertRedirects(
                response, "https://testserver/secure_view/", status_code=302
            )
            with self.assertRaises(AssertionError):
                self.assertRedirects(
                    response, "http://testserver/secure_view/", status_code=302
                )

    def test_redirect_fetch_redirect_response(self):
        """Preserve extra headers of requests made with django.test.Client."""
        methods = (
            "get",
            "post",
            "head",
            "options",
            "put",
            "patch",
            "delete",
            "trace",
        )
        for method in methods:
            with self.subTest(method=method):
                req_method = getattr(self.client, method)
                # HTTP_REDIRECT in "extra".
                response = req_method(
                    "/redirect_based_on_extra_headers_1/",
                    follow=False,
                    HTTP_REDIRECT="val",
                )
                self.assertRedirects(
                    response,
                    "/redirect_based_on_extra_headers_2/",
                    fetch_redirect_response=True,
                    status_code=302,
                    target_status_code=302,
                )
                # HTTP_REDIRECT in "headers".
                response = req_method(
                    "/redirect_based_on_extra_headers_1/",
                    follow=False,
                    headers={"redirect": "val"},
                )
                self.assertRedirects(
                    response,
                    "/redirect_based_on_extra_headers_2/",
                    fetch_redirect_response=True,
                    status_code=302,
                    target_status_code=302,
                )


@override_settings(ROOT_URLCONF="test_client_regress.urls")
class LoginTests(TestDataMixin, TestCase):
    def test_login_different_client(self):
        "Using a different test client doesn't violate authentication"

        # Create a second client, and log in.
        c = Client()
        login = c.login(username="testclient", password="password")
        self.assertTrue(login, "Could not log in")

        # Get a redirection page with the second client.
        response = c.get("/login_protected_redirect_view/")

        # At this points, the self.client isn't logged in.
        # assertRedirects uses the original client, not the default client.
        self.assertRedirects(response, "/get_view/")


@override_settings(
    SESSION_ENGINE="test_client_regress.session",
    ROOT_URLCONF="test_client_regress.urls",
)
class SessionEngineTests(TestDataMixin, TestCase):
    def test_login(self):
        "A session engine that modifies the session key can be used to log in"
        login = self.client.login(username="testclient", password="password")
        self.assertTrue(login, "Could not log in")

        # Try to access a login protected page.
        response = self.client.get("/login_protected_view/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["user"].username, "testclient")


@override_settings(
    ROOT_URLCONF="test_client_regress.urls",
)
class URLEscapingTests(SimpleTestCase):
    def test_simple_argument_get(self):
        "Get a view that has a simple string argument"
        response = self.client.get(reverse("arg_view", args=["Slartibartfast"]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"Howdy, Slartibartfast")

    def test_argument_with_space_get(self):
        "Get a view that has a string argument that requires escaping"
        response = self.client.get(reverse("arg_view", args=["Arthur Dent"]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"Hi, Arthur")

    def test_simple_argument_post(self):
        "Post for a view that has a simple string argument"
        response = self.client.post(reverse("arg_view", args=["Slartibartfast"]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"Howdy, Slartibartfast")

    def test_argument_with_space_post(self):
        "Post for a view that has a string argument that requires escaping"
        response = self.client.post(reverse("arg_view", args=["Arthur Dent"]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"Hi, Arthur")


@override_settings(ROOT_URLCONF="test_client_regress.urls")
class ExceptionTests(TestDataMixin, TestCase):
    def test_exception_cleared(self):
        "#5836 - A stale user exception isn't re-raised by the test client."

        login = self.client.login(username="testclient", password="password")
        self.assertTrue(login, "Could not log in")
        with self.assertRaises(CustomTestException):
            self.client.get("/staff_only/")

        # At this point, an exception has been raised, and should be cleared.

        # This next operation should be successful; if it isn't we have a problem.
        login = self.client.login(username="staff", password="password")
        self.assertTrue(login, "Could not log in")
        self.client.get("/staff_only/")


@override_settings(ROOT_URLCONF="test_client_regress.urls")
class TemplateExceptionTests(SimpleTestCase):
    @override_settings(
        TEMPLATES=[
            {
                "BACKEND": "django.template.backends.django.DjangoTemplates",
                "DIRS": [os.path.join(os.path.dirname(__file__), "bad_templates")],
            }
        ]
    )
    def test_bad_404_template(self):
        "Errors found when rendering 404 error templates are re-raised"
        with self.assertRaises(TemplateSyntaxError):
            self.client.get("/no_such_view/")


# We need two different tests to check URLconf substitution -  one to check
# it was changed, and another one (without self.urls) to check it was reverted on
# teardown. This pair of tests relies upon the alphabetical ordering of test execution.
@override_settings(ROOT_URLCONF="test_client_regress.urls")
class UrlconfSubstitutionTests(SimpleTestCase):
    def test_urlconf_was_changed(self):
        "TestCase can enforce a custom URLconf on a per-test basis"
        url = reverse("arg_view", args=["somename"])
        self.assertEqual(url, "/arg_view/somename/")


# This test needs to run *after* UrlconfSubstitutionTests; the zz prefix in the
# name is to ensure alphabetical ordering.
class zzUrlconfSubstitutionTests(SimpleTestCase):
    def test_urlconf_was_reverted(self):
        """URLconf is reverted to original value after modification in a TestCase

        This will not find a match as the default ROOT_URLCONF is empty.
        """
        with self.assertRaises(NoReverseMatch):
            reverse("arg_view", args=["somename"])


@override_settings(ROOT_URLCONF="test_client_regress.urls")
class ContextTests(TestDataMixin, TestCase):
    def test_single_context(self):
        "Context variables can be retrieved from a single context"
        response = self.client.get("/request_data/", data={"foo": "whiz"})
        self.assertIsInstance(response.context, RequestContext)
        self.assertIn("get-foo", response.context)
        self.assertEqual(response.context["get-foo"], "whiz")
        self.assertEqual(response.context["data"], "sausage")

        with self.assertRaisesMessage(KeyError, "does-not-exist"):
            response.context["does-not-exist"]

    def test_inherited_context(self):
        "Context variables can be retrieved from a list of contexts"
        response = self.client.get("/request_data_extended/", data={"foo": "whiz"})
        self.assertEqual(response.context.__class__, ContextList)
        self.assertEqual(len(response.context), 2)
        self.assertIn("get-foo", response.context)
        self.assertEqual(response.context["get-foo"], "whiz")
        self.assertEqual(response.context["data"], "bacon")

        with self.assertRaisesMessage(KeyError, "does-not-exist"):
            response.context["does-not-exist"]

    def test_contextlist_keys(self):
        c1 = Context()
        c1.update({"hello": "world", "goodbye": "john"})
        c1.update({"hello": "dolly", "dolly": "parton"})
        c2 = Context()
        c2.update({"goodbye": "world", "python": "rocks"})
        c2.update({"goodbye": "dolly"})

        k = ContextList([c1, c2])
        # None, True and False are builtins of BaseContext, and present
        # in every Context without needing to be added.
        self.assertEqual(
            {"None", "True", "False", "hello", "goodbye", "python", "dolly"}, k.keys()
        )

    def test_contextlist_get(self):
        c1 = Context({"hello": "world", "goodbye": "john"})
        c2 = Context({"goodbye": "world", "python": "rocks"})
        k = ContextList([c1, c2])
        self.assertEqual(k.get("hello"), "world")
        self.assertEqual(k.get("goodbye"), "john")
        self.assertEqual(k.get("python"), "rocks")
        self.assertEqual(k.get("nonexistent", "default"), "default")

    def test_15368(self):
        # Need to insert a context processor that assumes certain things about
        # the request instance. This triggers a bug caused by some ways of
        # copying RequestContext.
        with self.settings(
            TEMPLATES=[
                {
                    "BACKEND": "django.template.backends.django.DjangoTemplates",
                    "APP_DIRS": True,
                    "OPTIONS": {
                        "context_processors": [
                            "test_client_regress.context_processors.special",
                        ],
                    },
                }
            ]
        ):
            response = self.client.get("/request_context_view/")
            self.assertContains(response, "Path: /request_context_view/")

    def test_nested_requests(self):
        """
        response.context is not lost when view call another view.
        """
        response = self.client.get("/nested_view/")
        self.assertIsInstance(response.context, RequestContext)
        self.assertEqual(response.context["nested"], "yes")


@override_settings(ROOT_URLCONF="test_client_regress.urls")
class SessionTests(TestDataMixin, TestCase):
    def test_session(self):
        "The session isn't lost if a user logs in"
        # The session doesn't exist to start.
        response = self.client.get("/check_session/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"NO")

        # This request sets a session variable.
        response = self.client.get("/set_session/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"set_session")

        # The session has been modified
        response = self.client.get("/check_session/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"YES")

        # Log in
        login = self.client.login(username="testclient", password="password")
        self.assertTrue(login, "Could not log in")

        # Session should still contain the modified value
        response = self.client.get("/check_session/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"YES")

    def test_session_initiated(self):
        session = self.client.session
        session["session_var"] = "foo"
        session.save()

        response = self.client.get("/check_session/")
        self.assertEqual(response.content, b"foo")

    def test_logout(self):
        """Logout should work whether the user is logged in or not (#9978)."""
        self.client.logout()
        login = self.client.login(username="testclient", password="password")
        self.assertTrue(login, "Could not log in")
        self.client.logout()
        self.client.logout()

    def test_logout_with_user(self):
        """Logout should send user_logged_out signal if user was logged in."""

        def listener(*args, **kwargs):
            listener.executed = True
            self.assertEqual(kwargs["sender"], User)

        listener.executed = False

        user_logged_out.connect(listener)
        self.client.login(username="testclient", password="password")
        self.client.logout()
        user_logged_out.disconnect(listener)
        self.assertTrue(listener.executed)

    @override_settings(AUTH_USER_MODEL="test_client_regress.CustomUser")
    def test_logout_with_custom_user(self):
        """Logout should send user_logged_out signal if custom user was logged in."""

        def listener(*args, **kwargs):
            self.assertEqual(kwargs["sender"], CustomUser)
            listener.executed = True

        listener.executed = False
        u = CustomUser.custom_objects.create(email="test@test.com")
        u.set_password("password")
        u.save()

        user_logged_out.connect(listener)
        self.client.login(username="test@test.com", password="password")
        self.client.logout()
        user_logged_out.disconnect(listener)
        self.assertTrue(listener.executed)

    @override_settings(
        AUTHENTICATION_BACKENDS=(
            "django.contrib.auth.backends.ModelBackend",
            "test_client_regress.auth_backends.CustomUserBackend",
        )
    )
    def test_logout_with_custom_auth_backend(self):
        "Request a logout after logging in with custom authentication backend"

        def listener(*args, **kwargs):
            self.assertEqual(kwargs["sender"], CustomUser)
            listener.executed = True

        listener.executed = False
        u = CustomUser.custom_objects.create(email="test@test.com")
        u.set_password("password")
        u.save()

        user_logged_out.connect(listener)
        self.client.login(username="test@test.com", password="password")
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
        self.client.login(username="incorrect", password="password")
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
        self.client.login(username="testclient", password="password")
        user_logged_out.disconnect(listener)

        self.assertTrue(listener.executed)

    def test_login_without_signal(self):
        """Login shouldn't send signal if user wasn't logged in"""

        def listener(*args, **kwargs):
            listener.executed = True

        listener.executed = False

        user_logged_in.connect(listener)
        self.client.login(username="incorrect", password="password")
        user_logged_in.disconnect(listener)

        self.assertFalse(listener.executed)


@override_settings(ROOT_URLCONF="test_client_regress.urls")
class RequestMethodTests(SimpleTestCase):
    def test_get(self):
        "Request a view via request method GET"
        response = self.client.get("/request_methods/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"request method: GET")

    def test_post(self):
        "Request a view via request method POST"
        response = self.client.post("/request_methods/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"request method: POST")

    def test_head(self):
        "Request a view via request method HEAD"
        response = self.client.head("/request_methods/")
        self.assertEqual(response.status_code, 200)
        # A HEAD request doesn't return any content.
        self.assertNotEqual(response.content, b"request method: HEAD")
        self.assertEqual(response.content, b"")

    def test_options(self):
        "Request a view via request method OPTIONS"
        response = self.client.options("/request_methods/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"request method: OPTIONS")

    def test_put(self):
        "Request a view via request method PUT"
        response = self.client.put("/request_methods/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"request method: PUT")

    def test_delete(self):
        "Request a view via request method DELETE"
        response = self.client.delete("/request_methods/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"request method: DELETE")

    def test_patch(self):
        "Request a view via request method PATCH"
        response = self.client.patch("/request_methods/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"request method: PATCH")


@override_settings(ROOT_URLCONF="test_client_regress.urls")
class RequestMethodStringDataTests(SimpleTestCase):
    def test_post(self):
        "Request a view with string data via request method POST"
        # Regression test for #11371
        data = '{"test": "json"}'
        response = self.client.post(
            "/request_methods/", data=data, content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"request method: POST")

    def test_put(self):
        "Request a view with string data via request method PUT"
        # Regression test for #11371
        data = '{"test": "json"}'
        response = self.client.put(
            "/request_methods/", data=data, content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"request method: PUT")

    def test_patch(self):
        "Request a view with string data via request method PATCH"
        # Regression test for #17797
        data = '{"test": "json"}'
        response = self.client.patch(
            "/request_methods/", data=data, content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"request method: PATCH")

    def test_empty_string_data(self):
        "Request a view with empty string data via request method GET/POST/HEAD"
        # Regression test for #21740
        response = self.client.get("/body/", data="", content_type="application/json")
        self.assertEqual(response.content, b"")
        response = self.client.post("/body/", data="", content_type="application/json")
        self.assertEqual(response.content, b"")
        response = self.client.head("/body/", data="", content_type="application/json")
        self.assertEqual(response.content, b"")

    def test_json_bytes(self):
        response = self.client.post(
            "/body/", data=b"{'value': 37}", content_type="application/json"
        )
        self.assertEqual(response.content, b"{'value': 37}")

    def test_json(self):
        response = self.client.get("/json_response/")
        self.assertEqual(response.json(), {"key": "value"})

    def test_json_charset(self):
        response = self.client.get("/json_response_latin1/")
        self.assertEqual(response.charset, "latin1")
        self.assertEqual(response.json(), {"a": "Å"})

    def test_json_structured_suffixes(self):
        valid_types = (
            "application/vnd.api+json",
            "application/vnd.api.foo+json",
            "application/json; charset=utf-8",
            "application/activity+json",
            "application/activity+json; charset=utf-8",
        )
        for content_type in valid_types:
            response = self.client.get(
                "/json_response/", {"content_type": content_type}
            )
            self.assertEqual(response.headers["Content-Type"], content_type)
            self.assertEqual(response.json(), {"key": "value"})

    def test_json_multiple_access(self):
        response = self.client.get("/json_response/")
        self.assertIs(response.json(), response.json())

    def test_json_wrong_header(self):
        response = self.client.get("/body/")
        msg = (
            'Content-Type header is "text/html; charset=utf-8", not "application/json"'
        )
        with self.assertRaisesMessage(ValueError, msg):
            self.assertEqual(response.json(), {"key": "value"})


@override_settings(
    ROOT_URLCONF="test_client_regress.urls",
)
class QueryStringTests(SimpleTestCase):
    def test_get_like_requests(self):
        for method_name in ("get", "head"):
            # A GET-like request can pass a query string as data (#10571)
            method = getattr(self.client, method_name)
            response = method("/request_data/", data={"foo": "whiz"})
            self.assertEqual(response.context["get-foo"], "whiz")

            # A GET-like request can pass a query string as part of the URL
            response = method("/request_data/?foo=whiz")
            self.assertEqual(response.context["get-foo"], "whiz")

            # Data provided in the URL to a GET-like request is overridden by
            # actual form data.
            response = method("/request_data/?foo=whiz", data={"foo": "bang"})
            self.assertEqual(response.context["get-foo"], "bang")

            response = method("/request_data/?foo=whiz", data={"bar": "bang"})
            self.assertIsNone(response.context["get-foo"])
            self.assertEqual(response.context["get-bar"], "bang")

    def test_post_like_requests(self):
        # A POST-like request can pass a query string as data
        response = self.client.post("/request_data/", data={"foo": "whiz"})
        self.assertIsNone(response.context["get-foo"])
        self.assertEqual(response.context["post-foo"], "whiz")

        # A POST-like request can pass a query string as part of the URL
        response = self.client.post("/request_data/?foo=whiz")
        self.assertEqual(response.context["get-foo"], "whiz")
        self.assertIsNone(response.context["post-foo"])

        response = self.client.post("/request_data/", query_params={"foo": "whiz"})
        self.assertEqual(response.context["get-foo"], "whiz")
        self.assertIsNone(response.context["post-foo"])

        # POST data provided in the URL augments actual form data
        response = self.client.post("/request_data/?foo=whiz", data={"foo": "bang"})
        self.assertEqual(response.context["get-foo"], "whiz")
        self.assertEqual(response.context["post-foo"], "bang")

        response = self.client.post("/request_data/?foo=whiz", data={"bar": "bang"})
        self.assertEqual(response.context["get-foo"], "whiz")
        self.assertIsNone(response.context["get-bar"])
        self.assertIsNone(response.context["post-foo"])
        self.assertEqual(response.context["post-bar"], "bang")


@override_settings(ROOT_URLCONF="test_client_regress.urls")
class PayloadEncodingTests(SimpleTestCase):
    """Regression tests for #10571."""

    def test_simple_payload(self):
        """A simple ASCII-only text can be POSTed."""
        text = "English: mountain pass"
        response = self.client.post(
            "/parse_encoded_text/", text, content_type="text/plain"
        )
        self.assertEqual(response.content, text.encode())

    def test_utf8_payload(self):
        """Non-ASCII data encoded as UTF-8 can be POSTed."""
        text = "dog: собака"
        response = self.client.post(
            "/parse_encoded_text/", text, content_type="text/plain; charset=utf-8"
        )
        self.assertEqual(response.content, text.encode())

    def test_utf16_payload(self):
        """Non-ASCII data encoded as UTF-16 can be POSTed."""
        text = "dog: собака"
        response = self.client.post(
            "/parse_encoded_text/", text, content_type="text/plain; charset=utf-16"
        )
        self.assertEqual(response.content, text.encode("utf-16"))

    def test_non_utf_payload(self):
        """Non-ASCII data as a non-UTF based encoding can be POSTed."""
        text = "dog: собака"
        response = self.client.post(
            "/parse_encoded_text/", text, content_type="text/plain; charset=koi8-r"
        )
        self.assertEqual(response.content, text.encode("koi8-r"))


class DummyFile:
    def __init__(self, filename):
        self.name = filename

    def read(self):
        return b"TEST_FILE_CONTENT"


class UploadedFileEncodingTest(SimpleTestCase):
    def test_file_encoding(self):
        encoded_file = encode_file(
            "TEST_BOUNDARY", "TEST_KEY", DummyFile("test_name.bin")
        )
        self.assertEqual(b"--TEST_BOUNDARY", encoded_file[0])
        self.assertEqual(
            b'Content-Disposition: form-data; name="TEST_KEY"; '
            b'filename="test_name.bin"',
            encoded_file[1],
        )
        self.assertEqual(b"TEST_FILE_CONTENT", encoded_file[-1])

    def test_guesses_content_type_on_file_encoding(self):
        self.assertEqual(
            b"Content-Type: application/octet-stream",
            encode_file("IGNORE", "IGNORE", DummyFile("file.bin"))[2],
        )
        self.assertEqual(
            b"Content-Type: text/plain",
            encode_file("IGNORE", "IGNORE", DummyFile("file.txt"))[2],
        )
        self.assertIn(
            encode_file("IGNORE", "IGNORE", DummyFile("file.zip"))[2],
            (
                b"Content-Type: application/x-compress",
                b"Content-Type: application/x-zip",
                b"Content-Type: application/x-zip-compressed",
                b"Content-Type: application/zip",
            ),
        )
        self.assertEqual(
            b"Content-Type: application/octet-stream",
            encode_file("IGNORE", "IGNORE", DummyFile("file.unknown"))[2],
        )


@override_settings(
    ROOT_URLCONF="test_client_regress.urls",
)
class RequestHeadersTest(SimpleTestCase):
    def test_client_headers(self):
        "A test client can receive custom headers"
        response = self.client.get(
            "/check_headers/", headers={"x-arg-check": "Testing 123"}
        )
        self.assertEqual(response.content, b"HTTP_X_ARG_CHECK: Testing 123")
        self.assertEqual(response.status_code, 200)

    def test_client_headers_redirect(self):
        "Test client headers are preserved through redirects"
        response = self.client.get(
            "/check_headers_redirect/",
            follow=True,
            headers={"x-arg-check": "Testing 123"},
        )
        self.assertEqual(response.content, b"HTTP_X_ARG_CHECK: Testing 123")
        self.assertRedirects(
            response, "/check_headers/", status_code=302, target_status_code=200
        )


@override_settings(ROOT_URLCONF="test_client_regress.urls")
class ReadLimitedStreamTest(SimpleTestCase):
    """
    HttpRequest.body, HttpRequest.read(), and HttpRequest.read(BUFFER) have
    proper LimitedStream behavior.

    Refs #14753, #15785
    """

    def test_body_from_empty_request(self):
        """HttpRequest.body on a test client GET request should return
        the empty string."""
        self.assertEqual(self.client.get("/body/").content, b"")

    def test_read_from_empty_request(self):
        """HttpRequest.read() on a test client GET request should return the
        empty string."""
        self.assertEqual(self.client.get("/read_all/").content, b"")

    def test_read_numbytes_from_empty_request(self):
        """HttpRequest.read(LARGE_BUFFER) on a test client GET request should
        return the empty string."""
        self.assertEqual(self.client.get("/read_buffer/").content, b"")

    def test_read_from_nonempty_request(self):
        """HttpRequest.read() on a test client PUT request with some payload
        should return that payload."""
        payload = b"foobar"
        self.assertEqual(
            self.client.put(
                "/read_all/", data=payload, content_type="text/plain"
            ).content,
            payload,
        )

    def test_read_numbytes_from_nonempty_request(self):
        """HttpRequest.read(LARGE_BUFFER) on a test client PUT request with
        some payload should return that payload."""
        payload = b"foobar"
        self.assertEqual(
            self.client.put(
                "/read_buffer/", data=payload, content_type="text/plain"
            ).content,
            payload,
        )


@override_settings(ROOT_URLCONF="test_client_regress.urls")
class RequestFactoryStateTest(SimpleTestCase):
    """Regression tests for #15929."""

    # These tests are checking that certain middleware don't change certain
    # global state. Alternatively, from the point of view of a test, they are
    # ensuring test isolation behavior. So, unusually, it doesn't make sense to
    # run the tests individually, and if any are failing it is confusing to run
    # them with any other set of tests.

    def common_test_that_should_always_pass(self):
        request = RequestFactory().get("/")
        request.session = {}
        self.assertFalse(hasattr(request, "user"))

    def test_request(self):
        self.common_test_that_should_always_pass()

    def test_request_after_client(self):
        # apart from the next line the three tests are identical
        self.client.get("/")
        self.common_test_that_should_always_pass()

    def test_request_after_client_2(self):
        # This test is executed after the previous one
        self.common_test_that_should_always_pass()


@override_settings(ROOT_URLCONF="test_client_regress.urls")
class RequestFactoryEnvironmentTests(SimpleTestCase):
    """
    Regression tests for #8551 and #17067: ensure that environment variables
    are set correctly in RequestFactory.
    """

    def test_should_set_correct_env_variables(self):
        request = RequestFactory().get("/path/")

        self.assertEqual(request.META.get("REMOTE_ADDR"), "127.0.0.1")
        self.assertEqual(request.META.get("SERVER_NAME"), "testserver")
        self.assertEqual(request.META.get("SERVER_PORT"), "80")
        self.assertEqual(request.META.get("SERVER_PROTOCOL"), "HTTP/1.1")
        self.assertEqual(
            request.META.get("SCRIPT_NAME") + request.META.get("PATH_INFO"), "/path/"
        )

    def test_cookies(self):
        factory = RequestFactory()
        factory.cookies.load('A="B"; C="D"; Path=/; Version=1')
        request = factory.get("/")
        self.assertEqual(request.META["HTTP_COOKIE"], 'A="B"; C="D"')
