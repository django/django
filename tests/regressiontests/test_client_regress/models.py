"""
Regression tests for the Test Client, especially the customized assertions.

"""
from django.test import Client, TestCase
from django.core import mail

class AssertTemplateUsedTests(TestCase):
    fixtures = ['testdata.json']
    
    def test_no_context(self):
        "Template usage assertions work then templates aren't in use"
        response = self.client.get('/test_client_regress/no_template_view/')

        # Check that the no template case doesn't mess with the template assertions
        self.assertTemplateNotUsed(response, 'GET Template')
        
        try:
            self.assertTemplateUsed(response, 'GET Template')
        except AssertionError, e:
            self.assertEquals(str(e), "No templates used to render the response")

    def test_single_context(self):        
        "Template assertions work when there is a single context"
        response = self.client.get('/test_client/post_view/', {})

        # 
        try:
            self.assertTemplateNotUsed(response, 'Empty GET Template')
        except AssertionError, e:
            self.assertEquals(str(e), "Template 'Empty GET Template' was used unexpectedly in rendering the response")
            
        try:
            self.assertTemplateUsed(response, 'Empty POST Template')        
        except AssertionError, e:
            self.assertEquals(str(e), "Template 'Empty POST Template' was not used to render the response. Actual template was 'Empty GET Template'")
    
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
        except AssertionError, e:
            self.assertEquals(str(e), "Template 'form_view.html' was used unexpectedly in rendering the response")

        try:
            self.assertTemplateNotUsed(response, 'base.html')
        except AssertionError, e:
            self.assertEquals(str(e), "Template 'base.html' was used unexpectedly in rendering the response")

        try:
            self.assertTemplateUsed(response, "Valid POST Template")        
        except AssertionError, e:
            self.assertEquals(str(e), "Template 'Valid POST Template' was not one of the templates used to render the response. Templates used: ['form_view.html', 'base.html']")

class AssertRedirectsTests(TestCase):
    def test_redirect_page(self):
        "An assertion is raised if the original page couldn't be retrieved as expected"        
        # This page will redirect with code 301, not 302
        response = self.client.get('/test_client/permanent_redirect_view/')        
        try:
            self.assertRedirects(response, '/test_client/get_view/')
        except AssertionError, e:
            self.assertEquals(str(e), "Response didn't redirect as expected: Reponse code was 301 (expected 302)")

    def test_incorrect_target(self):
        "An assertion is raised if the response redirects to another target"
        response = self.client.get('/test_client/permanent_redirect_view/')        
        try:
            # Should redirect to get_view
            self.assertRedirects(response, '/test_client/some_view/')
        except AssertionError, e:
            self.assertEquals(str(e), "Response didn't redirect as expected: Reponse code was 301 (expected 302)")
        
    def test_target_page(self):
        "An assertion is raised if the reponse redirect target cannot be retrieved as expected"
        response = self.client.get('/test_client/double_redirect_view/')
        try:
            # The redirect target responds with a 301 code, not 200
            self.assertRedirects(response, '/test_client/permanent_redirect_view/')
        except AssertionError, e:
            self.assertEquals(str(e), "Couldn't retrieve redirection page '/test_client/permanent_redirect_view/': response code was 301 (expected 200)")
            
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
        except AssertionError, e:
            self.assertEqual(str(e), "The form 'wrong_form' was not used to render the response")
        
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
        except AssertionError, e:
            self.assertEqual(str(e), "The form 'form' in context 0 does not contain the field 'some_field'")
        
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
        except AssertionError, e:
            self.assertEqual(str(e), "The field 'value' on form 'form' in context 0 contains no errors")
        
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
        except AssertionError, e:
            self.assertEqual(str(e), "The field 'email' on form 'form' in context 0 does not contain the error 'Some error.' (actual errors: [u'Enter a valid e-mail address.'])")

