from django.contrib.auth.models import User
from django.contrib.auth.tests.forms import PasswordResetForm
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.contrib.auth.views import password_reset, password_reset_done, \
    password_reset_confirm, password_reset_complete, password_change, \
    password_change_done
from django.http import HttpRequest
from django.test import TestCase
from django.utils.http import int_to_base36

class AuthViewsTests(TestCase):

    def create_dummy_user(self):
        username = 'jsmith'
        email = 'jsmith@example.com'
        user = User.objects.create_user(username, email, 'pass')
        return (user, username, email)
    
    def create_dummy_request(self):
        request = HttpRequest()
        request.path = u'/somepath/'
        return request
    
    def test(self):
        from django.contrib.auth import authenticate
        (user, username, email) = self.create_dummy_user()
        user = authenticate(username=username, password='pass')
        data = {'email': email}
        form = PasswordResetForm(data)
        request = self.create_dummy_request()
        
        #password_reset
        response = password_reset(request, post_reset_redirect='dummy/')
        self.assertContains(response, '<title>Password reset</title>')
        self.assertContains(response, '<h1>Password reset</h1>')
        
        #password_reset_done
        response = password_reset_done(request)
        self.assertContains(response, '<title>Password reset successful</title>')
        self.assertContains(response, '<h1>Password reset successful</h1>')
        
        #password_reset_confirm invalid token
        response = password_reset_confirm(request, uidb36='Bad', token='Bad', post_reset_redirect='dummy/')
        self.assertContains(response, '<title>Password reset</title>')
        self.assertContains(response, '<h1>Password reset unsuccessful</h1>')
        
        #password_reset_confirm valid token
        default_token_generator = PasswordResetTokenGenerator()
        token = default_token_generator.make_token(user)
        uidb36 = int_to_base36(user.id)
        response = password_reset_confirm(request, uidb36, token, post_reset_redirect='dummy/')
        self.assertContains(response, '<title>Password reset</title>')
        self.assertContains(response, '<h1>Enter new password</h1>')
        
        #password_reset_complete
        response = password_reset_complete(request)
        self.assertContains(response, '<title>Password reset complete</title>')
        self.assertContains(response, '<h1>Password reset complete</h1>')
        
                
        #password_change
        request = self.create_dummy_request()
        request.user = user        
        response = password_change(request, post_change_redirect='dummy/')
        self.assertContains(response, '<title>Password change</title>')
        self.assertContains(response, '<h1>Password change successful</h1>')
        
        
        #password_change_done
        response = password_change_done(request)
        self.assertContains(response, '<title>Password change successful</title>')
        self.assertContains(response, '<h1>Password change successful</h1>')
        
        
        