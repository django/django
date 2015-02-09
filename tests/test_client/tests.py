# -*- coding: utf-8 -*-
"""
Testing using the Test Client

The test client is a class that can act like a simple
browser for testing purposes.

It allows the user to compose GET and POST requests, and
obtain the response that the server gave to those requests.
The server Response objects are annotated with the details
of the contexts and templates that were rendered during the
process of serving the request.

``Client`` objects are stateful - they will retain cookie (and
thus session) details for the lifetime of the ``Client`` instance.

This is not intended as a replacement for Twill, Selenium, or
other browser automation frameworks - it is here to allow
testing against the contexts and templates produced by a view,
rather than the HTML rendered to the end-user.

"""
from __future__ import unicode_literals

from django.core import mail
from django.http import HttpResponse
from django.test import Client, RequestFactory, TestCase, override_settings

from .views import get_view, post_view, trace_view


@override_settings(PASSWORD_HASHERS=('django.contrib.auth.hashers.SHA1PasswordHasher',),
                   ROOT_URLCONF='test_client.urls',)
class ClientTest(TestCase):
    fixtures = ['testdata.json']

    def test_get_view(self):
        "GET a view"
        # The data is ignored, but let's check it doesn't crash the system
        # anyway.
        data = {'var': '\xf2'}
        response = self.client.get('/get_view/', data)

        # Check some response details
        self.assertContains(response, 'This is a test')
        self.assertEqual(response.context['var'], '\xf2')
        self.assertEqual(response.templates[0].name, 'GET Template')

    def test_get_post_view(self):
        "GET a view that normally expects POSTs"
        response = self.client.get('/post_view/', {})

        # Check some response details
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.templates[0].name, 'Empty GET Template')
        self.assertTemplateUsed(response, 'Empty GET Template')
        self.assertTemplateNotUsed(response, 'Empty POST Template')

    def test_empty_post(self):
        "POST an empty dictionary to a view"
        response = self.client.post('/post_view/', {})

        # Check some response details
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.templates[0].name, 'Empty POST Template')
        self.assertTemplateNotUsed(response, 'Empty GET Template')
        self.assertTemplateUsed(response, 'Empty POST Template')

    def test_post(self):
        "POST some data to a view"
        post_data = {
            'value': 37
        }
        response = self.client.post('/post_view/', post_data)

        # Check some response details
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['data'], '37')
        self.assertEqual(response.templates[0].name, 'POST Template')
        self.assertContains(response, 'Data received')

    def test_trace(self):
        """TRACE a view"""
        response = self.client.trace('/trace_view/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['method'], 'TRACE')
        self.assertEqual(response.templates[0].name, 'TRACE Template')

    def test_response_headers(self):
        "Check the value of HTTP headers returned in a response"
        response = self.client.get("/header_view/")

        self.assertEqual(response['X-DJANGO-TEST'], 'Slartibartfast')

    def test_response_attached_request(self):
        """
        Check that the returned response has a ``request`` attribute with the
        originating environ dict and a ``wsgi_request`` with the originating
        ``WSGIRequest`` instance.
        """
        response = self.client.get("/header_view/")

        self.assertTrue(hasattr(response, 'request'))
        self.assertTrue(hasattr(response, 'wsgi_request'))
        for key, value in response.request.items():
            self.assertIn(key, response.wsgi_request.environ)
            self.assertEqual(response.wsgi_request.environ[key], value)

    def test_response_resolver_match(self):
        """
        The response contains a ResolverMatch instance.
        """
        response = self.client.get('/header_view/')
        self.assertTrue(hasattr(response, 'resolver_match'))

    def test_response_resolver_match_redirect_follow(self):
        """
        The response ResolverMatch instance contains the correct
        information when following redirects.
        """
        response = self.client.get('/redirect_view/', follow=True)
        self.assertEqual(response.resolver_match.url_name, 'get_view')

    def test_response_resolver_match_regular_view(self):
        """
        The response ResolverMatch instance contains the correct
        information when accessing a regular view.
        """
        response = self.client.get('/get_view/')
        self.assertEqual(response.resolver_match.url_name, 'get_view')

    def test_raw_post(self):
        "POST raw data (with a content type) to a view"
        test_doc = """<?xml version="1.0" encoding="utf-8"?><library><book><title>Blink</title><author>Malcolm Gladwell</author></book></library>"""
        response = self.client.post("/raw_post_view/", test_doc,
                                    content_type="text/xml")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.templates[0].name, "Book template")
        self.assertEqual(response.content, b"Blink - Malcolm Gladwell")

    def test_insecure(self):
        "GET a URL through http"
        response = self.client.get('/secure_view/', secure=False)
        self.assertFalse(response.test_was_secure_request)
        self.assertEqual(response.test_server_port, '80')

    def test_secure(self):
        "GET a URL through https"
        response = self.client.get('/secure_view/', secure=True)
        self.assertTrue(response.test_was_secure_request)
        self.assertEqual(response.test_server_port, '443')

    def test_redirect(self):
        "GET a URL that redirects elsewhere"
        response = self.client.get('/redirect_view/')
        # Check that the response was a 302 (redirect) and that
        # assertRedirect() understands to put an implicit http://testserver/ in
        # front of non-absolute URLs.
        self.assertRedirects(response, '/get_view/')

        host = 'django.testserver'
        client_providing_host = Client(HTTP_HOST=host)
        response = client_providing_host.get('/redirect_view/')
        # Check that the response was a 302 (redirect) with absolute URI
        self.assertRedirects(response, '/get_view/', host=host)

    def test_redirect_with_query(self):
        "GET a URL that redirects with given GET parameters"
        response = self.client.get('/redirect_view/', {'var': 'value'})

        # Check if parameters are intact
        self.assertRedirects(response, 'http://testserver/get_view/?var=value')

    def test_permanent_redirect(self):
        "GET a URL that redirects permanently elsewhere"
        response = self.client.get('/permanent_redirect_view/')
        # Check that the response was a 301 (permanent redirect)
        self.assertRedirects(response, 'http://testserver/get_view/', status_code=301)

        client_providing_host = Client(HTTP_HOST='django.testserver')
        response = client_providing_host.get('/permanent_redirect_view/')
        # Check that the response was a 301 (permanent redirect) with absolute URI
        self.assertRedirects(response, 'http://django.testserver/get_view/', status_code=301)

    def test_temporary_redirect(self):
        "GET a URL that does a non-permanent redirect"
        response = self.client.get('/temporary_redirect_view/')
        # Check that the response was a 302 (non-permanent redirect)
        self.assertRedirects(response, 'http://testserver/get_view/', status_code=302)

    def test_redirect_to_strange_location(self):
        "GET a URL that redirects to a non-200 page"
        response = self.client.get('/double_redirect_view/')

        # Check that the response was a 302, and that
        # the attempt to get the redirection location returned 301 when retrieved
        self.assertRedirects(response, 'http://testserver/permanent_redirect_view/', target_status_code=301)

    def test_follow_redirect(self):
        "A URL that redirects can be followed to termination."
        response = self.client.get('/double_redirect_view/', follow=True)
        self.assertRedirects(response, 'http://testserver/get_view/', status_code=302, target_status_code=200)
        self.assertEqual(len(response.redirect_chain), 2)

    def test_redirect_http(self):
        "GET a URL that redirects to an http URI"
        response = self.client.get('/http_redirect_view/', follow=True)
        self.assertFalse(response.test_was_secure_request)

    def test_redirect_https(self):
        "GET a URL that redirects to an https URI"
        response = self.client.get('/https_redirect_view/', follow=True)
        self.assertTrue(response.test_was_secure_request)

    def test_notfound_response(self):
        "GET a URL that responds as '404:Not Found'"
        response = self.client.get('/bad_view/')

        # Check that the response was a 404, and that the content contains MAGIC
        self.assertContains(response, 'MAGIC', status_code=404)

    def test_valid_form(self):
        "POST valid data to a form"
        post_data = {
            'text': 'Hello World',
            'email': 'foo@example.com',
            'value': 37,
            'single': 'b',
            'multi': ('b', 'c', 'e')
        }
        response = self.client.post('/form_view/', post_data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "Valid POST Template")

    def test_valid_form_with_hints(self):
        "GET a form, providing hints in the GET data"
        hints = {
            'text': 'Hello World',
            'multi': ('b', 'c', 'e')
        }
        response = self.client.get('/form_view/', data=hints)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "Form GET Template")
        # Check that the multi-value data has been rolled out ok
        self.assertContains(response, 'Select a valid choice.', 0)

    def test_incomplete_data_form(self):
        "POST incomplete data to a form"
        post_data = {
            'text': 'Hello World',
            'value': 37
        }
        response = self.client.post('/form_view/', post_data)
        self.assertContains(response, 'This field is required.', 3)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "Invalid POST Template")

        self.assertFormError(response, 'form', 'email', 'This field is required.')
        self.assertFormError(response, 'form', 'single', 'This field is required.')
        self.assertFormError(response, 'form', 'multi', 'This field is required.')

    def test_form_error(self):
        "POST erroneous data to a form"
        post_data = {
            'text': 'Hello World',
            'email': 'not an email address',
            'value': 37,
            'single': 'b',
            'multi': ('b', 'c', 'e')
        }
        response = self.client.post('/form_view/', post_data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "Invalid POST Template")

        self.assertFormError(response, 'form', 'email', 'Enter a valid email address.')

    def test_valid_form_with_template(self):
        "POST valid data to a form using multiple templates"
        post_data = {
            'text': 'Hello World',
            'email': 'foo@example.com',
            'value': 37,
            'single': 'b',
            'multi': ('b', 'c', 'e')
        }
        response = self.client.post('/form_view_with_template/', post_data)
        self.assertContains(response, 'POST data OK')
        self.assertTemplateUsed(response, "form_view.html")
        self.assertTemplateUsed(response, 'base.html')
        self.assertTemplateNotUsed(response, "Valid POST Template")

    def test_incomplete_data_form_with_template(self):
        "POST incomplete data to a form using multiple templates"
        post_data = {
            'text': 'Hello World',
            'value': 37
        }
        response = self.client.post('/form_view_with_template/', post_data)
        self.assertContains(response, 'POST data has errors')
        self.assertTemplateUsed(response, 'form_view.html')
        self.assertTemplateUsed(response, 'base.html')
        self.assertTemplateNotUsed(response, "Invalid POST Template")

        self.assertFormError(response, 'form', 'email', 'This field is required.')
        self.assertFormError(response, 'form', 'single', 'This field is required.')
        self.assertFormError(response, 'form', 'multi', 'This field is required.')

    def test_form_error_with_template(self):
        "POST erroneous data to a form using multiple templates"
        post_data = {
            'text': 'Hello World',
            'email': 'not an email address',
            'value': 37,
            'single': 'b',
            'multi': ('b', 'c', 'e')
        }
        response = self.client.post('/form_view_with_template/', post_data)
        self.assertContains(response, 'POST data has errors')
        self.assertTemplateUsed(response, "form_view.html")
        self.assertTemplateUsed(response, 'base.html')
        self.assertTemplateNotUsed(response, "Invalid POST Template")

        self.assertFormError(response, 'form', 'email', 'Enter a valid email address.')

    def test_unknown_page(self):
        "GET an invalid URL"
        response = self.client.get('/unknown_view/')

        # Check that the response was a 404
        self.assertEqual(response.status_code, 404)

    def test_url_parameters(self):
        "Make sure that URL ;-parameters are not stripped."
        response = self.client.get('/unknown_view/;some-parameter')

        # Check that the path in the response includes it (ignore that it's a 404)
        self.assertEqual(response.request['PATH_INFO'], '/unknown_view/;some-parameter')

    def test_view_with_login(self):
        "Request a page that is protected with @login_required"

        # Get the page without logging in. Should result in 302.
        response = self.client.get('/login_protected_view/')
        self.assertRedirects(response, 'http://testserver/accounts/login/?next=/login_protected_view/')

        # Log in
        login = self.client.login(username='testclient', password='password')
        self.assertTrue(login, 'Could not log in')

        # Request a page that requires a login
        response = self.client.get('/login_protected_view/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['user'].username, 'testclient')

    def test_view_with_method_login(self):
        "Request a page that is protected with a @login_required method"

        # Get the page without logging in. Should result in 302.
        response = self.client.get('/login_protected_method_view/')
        self.assertRedirects(response, 'http://testserver/accounts/login/?next=/login_protected_method_view/')

        # Log in
        login = self.client.login(username='testclient', password='password')
        self.assertTrue(login, 'Could not log in')

        # Request a page that requires a login
        response = self.client.get('/login_protected_method_view/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['user'].username, 'testclient')

    def test_view_with_login_and_custom_redirect(self):
        "Request a page that is protected with @login_required(redirect_field_name='redirect_to')"

        # Get the page without logging in. Should result in 302.
        response = self.client.get('/login_protected_view_custom_redirect/')
        self.assertRedirects(response, 'http://testserver/accounts/login/?redirect_to=/login_protected_view_custom_redirect/')

        # Log in
        login = self.client.login(username='testclient', password='password')
        self.assertTrue(login, 'Could not log in')

        # Request a page that requires a login
        response = self.client.get('/login_protected_view_custom_redirect/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['user'].username, 'testclient')

    def test_view_with_bad_login(self):
        "Request a page that is protected with @login, but use bad credentials"

        login = self.client.login(username='otheruser', password='nopassword')
        self.assertFalse(login)

    def test_view_with_inactive_login(self):
        "Request a page that is protected with @login, but use an inactive login"

        login = self.client.login(username='inactive', password='password')
        self.assertFalse(login)

    def test_logout(self):
        "Request a logout after logging in"
        # Log in
        self.client.login(username='testclient', password='password')

        # Request a page that requires a login
        response = self.client.get('/login_protected_view/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['user'].username, 'testclient')

        # Log out
        self.client.logout()

        # Request a page that requires a login
        response = self.client.get('/login_protected_view/')
        self.assertRedirects(response, 'http://testserver/accounts/login/?next=/login_protected_view/')

    @override_settings(SESSION_ENGINE="django.contrib.sessions.backends.signed_cookies")
    def test_logout_cookie_sessions(self):
        self.test_logout()

    def test_view_with_permissions(self):
        "Request a page that is protected with @permission_required"

        # Get the page without logging in. Should result in 302.
        response = self.client.get('/permission_protected_view/')
        self.assertRedirects(response, 'http://testserver/accounts/login/?next=/permission_protected_view/')

        # Log in
        login = self.client.login(username='testclient', password='password')
        self.assertTrue(login, 'Could not log in')

        # Log in with wrong permissions. Should result in 302.
        response = self.client.get('/permission_protected_view/')
        self.assertRedirects(response, 'http://testserver/accounts/login/?next=/permission_protected_view/')

        # TODO: Log in with right permissions and request the page again

    def test_view_with_permissions_exception(self):
        "Request a page that is protected with @permission_required but raises an exception"

        # Get the page without logging in. Should result in 403.
        response = self.client.get('/permission_protected_view_exception/')
        self.assertEqual(response.status_code, 403)

        # Log in
        login = self.client.login(username='testclient', password='password')
        self.assertTrue(login, 'Could not log in')

        # Log in with wrong permissions. Should result in 403.
        response = self.client.get('/permission_protected_view_exception/')
        self.assertEqual(response.status_code, 403)

    def test_view_with_method_permissions(self):
        "Request a page that is protected with a @permission_required method"

        # Get the page without logging in. Should result in 302.
        response = self.client.get('/permission_protected_method_view/')
        self.assertRedirects(response, 'http://testserver/accounts/login/?next=/permission_protected_method_view/')

        # Log in
        login = self.client.login(username='testclient', password='password')
        self.assertTrue(login, 'Could not log in')

        # Log in with wrong permissions. Should result in 302.
        response = self.client.get('/permission_protected_method_view/')
        self.assertRedirects(response, 'http://testserver/accounts/login/?next=/permission_protected_method_view/')

        # TODO: Log in with right permissions and request the page again

    def test_external_redirect(self):
        response = self.client.get('/django_project_redirect/')
        self.assertRedirects(response, 'https://www.djangoproject.com/', fetch_redirect_response=False)

    def test_session_modifying_view(self):
        "Request a page that modifies the session"
        # Session value isn't set initially
        try:
            self.client.session['tobacconist']
            self.fail("Shouldn't have a session value")
        except KeyError:
            pass

        self.client.post('/session_view/')

        # Check that the session was modified
        self.assertEqual(self.client.session['tobacconist'], 'hovercraft')

    def test_view_with_exception(self):
        "Request a page that is known to throw an error"
        self.assertRaises(KeyError, self.client.get, "/broken_view/")

        # Try the same assertion, a different way
        try:
            self.client.get('/broken_view/')
            self.fail('Should raise an error')
        except KeyError:
            pass

    def test_mail_sending(self):
        "Test that mail is redirected to a dummy outbox during test setup"

        response = self.client.get('/mail_sending_view/')
        self.assertEqual(response.status_code, 200)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, 'Test message')
        self.assertEqual(mail.outbox[0].body, 'This is a test email')
        self.assertEqual(mail.outbox[0].from_email, 'from@example.com')
        self.assertEqual(mail.outbox[0].to[0], 'first@example.com')
        self.assertEqual(mail.outbox[0].to[1], 'second@example.com')

    def test_mass_mail_sending(self):
        "Test that mass mail is redirected to a dummy outbox during test setup"

        response = self.client.get('/mass_mail_sending_view/')
        self.assertEqual(response.status_code, 200)

        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(mail.outbox[0].subject, 'First Test message')
        self.assertEqual(mail.outbox[0].body, 'This is the first test email')
        self.assertEqual(mail.outbox[0].from_email, 'from@example.com')
        self.assertEqual(mail.outbox[0].to[0], 'first@example.com')
        self.assertEqual(mail.outbox[0].to[1], 'second@example.com')

        self.assertEqual(mail.outbox[1].subject, 'Second Test message')
        self.assertEqual(mail.outbox[1].body, 'This is the second test email')
        self.assertEqual(mail.outbox[1].from_email, 'from@example.com')
        self.assertEqual(mail.outbox[1].to[0], 'second@example.com')
        self.assertEqual(mail.outbox[1].to[1], 'third@example.com')


@override_settings(
    MIDDLEWARE_CLASSES=('django.middleware.csrf.CsrfViewMiddleware',),
    ROOT_URLCONF='test_client.urls',
)
class CSRFEnabledClientTests(TestCase):

    def test_csrf_enabled_client(self):
        "A client can be instantiated with CSRF checks enabled"
        csrf_client = Client(enforce_csrf_checks=True)

        # The normal client allows the post
        response = self.client.post('/post_view/', {})
        self.assertEqual(response.status_code, 200)

        # The CSRF-enabled client rejects it
        response = csrf_client.post('/post_view/', {})
        self.assertEqual(response.status_code, 403)


class CustomTestClient(Client):
    i_am_customized = "Yes"


class CustomTestClientTest(TestCase):
    client_class = CustomTestClient

    def test_custom_test_client(self):
        """A test case can specify a custom class for self.client."""
        self.assertEqual(hasattr(self.client, "i_am_customized"), True)


_generic_view = lambda request: HttpResponse(status=200)


@override_settings(ROOT_URLCONF='test_client.urls')
class RequestFactoryTest(TestCase):
    """Tests for the request factory."""

    # A mapping between names of HTTP/1.1 methods and their test views.
    http_methods_and_views = (
        ('get', get_view),
        ('post', post_view),
        ('put', _generic_view),
        ('patch', _generic_view),
        ('delete', _generic_view),
        ('head', _generic_view),
        ('options', _generic_view),
        ('trace', trace_view),
    )

    def setUp(self):
        self.request_factory = RequestFactory()

    def test_request_factory(self):
        """The request factory implements all the HTTP/1.1 methods."""
        for method_name, view in self.http_methods_and_views:
            method = getattr(self.request_factory, method_name)
            request = method('/somewhere/')
            response = view(request)

            self.assertEqual(response.status_code, 200)

    def test_get_request_from_factory(self):
        """
        The request factory returns a templated response for a GET request.
        """
        request = self.request_factory.get('/somewhere/')
        response = get_view(request)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'This is a test')

    def test_trace_request_from_factory(self):
        """The request factory returns an echo response for a TRACE request."""
        url_path = '/somewhere/'
        request = self.request_factory.trace(url_path)
        response = trace_view(request)
        protocol = request.META["SERVER_PROTOCOL"]
        echoed_request_line = "TRACE {} {}".format(url_path, protocol)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, echoed_request_line)
