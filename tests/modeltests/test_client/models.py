"""
39. Testing using the Test Client

The test client is a class that can act like a simple
browser for testing purposes.
  
It allows the user to compose GET and POST requests, and
obtain the response that the server gave to those requests.
The server Response objects are annotated with the details
of the contexts and templates that were rendered during the
process of serving the request.

Client objects are stateful - they will retain cookie (and
thus session) details for the lifetime of the Client instance.

This is not intended as a replacement for Twill,Selenium, or
other browser automation frameworks - it is here to allow 
testing against the contexts and templates produced by a view, 
rather than the HTML rendered to the end-user.

"""
from django.test.client import Client
import unittest

class ClientTest(unittest.TestCase):
    def setUp(self):
        "Set up test environment"
        self.client = Client()
        
    def test_get_view(self):
        "GET a view"
        response = self.client.get('/test_client/get_view/')
        
        # Check some response details
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['var'], 42)
        self.assertEqual(response.template.name, 'GET Template')
        self.failUnless('This is a test.' in response.content)

    def test_get_post_view(self):
        "GET a view that normally expects POSTs"
        response = self.client.get('/test_client/post_view/', {})
        
        # Check some response details
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.template.name, 'Empty POST Template')
        
    def test_empty_post(self):
        "POST an empty dictionary to a view"
        response = self.client.post('/test_client/post_view/', {})
        
        # Check some response details
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.template.name, 'Empty POST Template')
        
    def test_post_view(self):
        "POST some data to a view"
        post_data = {
            'value': 37
        }
        response = self.client.post('/test_client/post_view/', post_data)
        
        # Check some response details
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['data'], '37')
        self.assertEqual(response.template.name, 'POST Template')
        self.failUnless('Data received' in response.content)
        
    def test_redirect(self):
        "GET a URL that redirects elsewhere"
        response = self.client.get('/test_client/redirect_view/')
        
        # Check that the response was a 302 (redirect)
        self.assertEqual(response.status_code, 302)
                
    def test_unknown_page(self):
        "GET an invalid URL"
        response = self.client.get('/test_client/unknown_view/')
        
        # Check that the response was a 404
        self.assertEqual(response.status_code, 404)
        
    def test_view_with_login(self):
        "Request a page that is protected with @login_required"
        
        # Get the page without logging in. Should result in 302.
        response = self.client.get('/test_client/login_protected_view/')
        self.assertEqual(response.status_code, 302)
        
        # Request a page that requires a login
        response = self.client.login('/test_client/login_protected_view/', 'testclient', 'password')
        self.assertTrue(response)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['user'].username, 'testclient')
        self.assertEqual(response.template.name, 'Login Template')

    def test_view_with_bad_login(self):
        "Request a page that is protected with @login, but use bad credentials"

        response = self.client.login('/test_client/login_protected_view/', 'otheruser', 'nopassword')
        self.assertFalse(response)

    def test_session_modifying_view(self):
        "Request a page that modifies the session"
        # Session value isn't set initially
        try:
            self.client.session['tobacconist']
            self.fail("Shouldn't have a session value")
        except KeyError:
            pass
        
        from django.contrib.sessions.models import Session
        response = self.client.post('/test_client/session_view/')
        
        # Check that the session was modified
        self.assertEquals(self.client.session['tobacconist'], 'hovercraft')

    def test_view_with_exception(self):
        "Request a page that is known to throw an error"
        self.assertRaises(KeyError, self.client.get, "/test_client/broken_view/")
        
        #Try the same assertion, a different way
        try:
            self.client.get('/test_client/broken_view/')
            self.fail('Should raise an error')
        except KeyError:
            pass
