"""
38. Testing using the Test Client

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
from django.test import Client, TestCase

class ClientTest(TestCase):
    fixtures = ['testdata.json']
    
    def test_get_view(self):
        "GET a view"
        response = self.client.get('/test_client/get_view/')
        
        # Check some response details
        self.assertContains(response, 'This is a test')
        self.assertEqual(response.context['var'], 42)
        self.assertEqual(response.template.name, 'GET Template')

    def test_no_template_view(self):
        "Check that template usage assersions work then templates aren't in use"
        response = self.client.get('/test_client/no_template_view/')

        # Check that the no template case doesn't mess with the template assertions
        self.assertTemplateNotUsed(response, 'GET Template')
        
    def test_get_post_view(self):
        "GET a view that normally expects POSTs"
        response = self.client.get('/test_client/post_view/', {})
        
        # Check some response details
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.template.name, 'Empty GET Template')
        self.assertTemplateUsed(response, 'Empty GET Template')
        self.assertTemplateNotUsed(response, 'Empty POST Template')
        
    def test_empty_post(self):
        "POST an empty dictionary to a view"
        response = self.client.post('/test_client/post_view/', {})
        
        # Check some response details
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.template.name, 'Empty POST Template')
        self.assertTemplateNotUsed(response, 'Empty GET Template')
        self.assertTemplateUsed(response, 'Empty POST Template')
        
    def test_post(self):
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
        
    def test_raw_post(self):
        test_doc = """<?xml version="1.0" encoding="utf-8"?><library><book><title>Blink</title><author>Malcolm Gladwell</author></book></library>"""
        response = self.client.post("/test_client/raw_post_view/", test_doc,
                                    content_type="text/xml")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.template.name, "Book template")
        self.assertEqual(response.content, "Blink - Malcolm Gladwell")

    def test_redirect(self):
        "GET a URL that redirects elsewhere"
        response = self.client.get('/test_client/redirect_view/')
        
        # Check that the response was a 302 (redirect)
        self.assertRedirects(response, '/test_client/get_view/')

    def test_valid_form(self):
        "POST valid data to a form"
        post_data = {
            'text': 'Hello World',
            'email': 'foo@example.com',
            'value': 37,
            'single': 'b',
            'multi': ('b','c','e')
        }
        response = self.client.post('/test_client/form_view/', post_data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "Valid POST Template")

    def test_incomplete_data_form(self):
        "POST incomplete data to a form"
        post_data = {
            'text': 'Hello World',
            'value': 37            
        }
        response = self.client.post('/test_client/form_view/', post_data)
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
            'multi': ('b','c','e')
        }
        response = self.client.post('/test_client/form_view/', post_data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "Invalid POST Template")

        self.assertFormError(response, 'form', 'email', 'Enter a valid e-mail address.')

    def test_valid_form_with_template(self):
        "POST valid data to a form using multiple templates"
        post_data = {
            'text': 'Hello World',
            'email': 'foo@example.com',
            'value': 37,
            'single': 'b',
            'multi': ('b','c','e')
        }
        response = self.client.post('/test_client/form_view_with_template/', post_data)
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
        response = self.client.post('/test_client/form_view_with_template/', post_data)
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
            'multi': ('b','c','e')
        }
        response = self.client.post('/test_client/form_view_with_template/', post_data)
        self.assertContains(response, 'POST data has errors')
        self.assertTemplateUsed(response, "form_view.html")
        self.assertTemplateUsed(response, 'base.html')
        self.assertTemplateNotUsed(response, "Invalid POST Template")

        self.assertFormError(response, 'form', 'email', 'Enter a valid e-mail address.')
        
    def test_unknown_page(self):
        "GET an invalid URL"
        response = self.client.get('/test_client/unknown_view/')
        
        # Check that the response was a 404
        self.assertEqual(response.status_code, 404)
        
    def test_view_with_login(self):
        "Request a page that is protected with @login_required"
        
        # Get the page without logging in. Should result in 302.
        response = self.client.get('/test_client/login_protected_view/')
        self.assertRedirects(response, '/accounts/login/')
        
        # Log in
        self.client.login(username='testclient', password='password')

        # Request a page that requires a login
        response = self.client.get('/test_client/login_protected_view/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['user'].username, 'testclient')

    def test_view_with_bad_login(self):
        "Request a page that is protected with @login, but use bad credentials"

        login = self.client.login(username='otheruser', password='nopassword')
        self.failIf(login)

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
