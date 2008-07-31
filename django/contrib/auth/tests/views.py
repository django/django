
import re
from django.contrib.auth.models import User
from django.test import TestCase
from django.core import mail

class PasswordResetTest(TestCase):
    fixtures = ['authtestdata.json']
    urls = 'django.contrib.auth.urls'
    
    def test_email_not_found(self):
        "Error is raised if the provided email address isn't currently registered"
        response = self.client.get('/password_reset/')
        self.assertEquals(response.status_code, 200)
        response = self.client.post('/password_reset/', {'email': 'not_a_real_email@email.com'})
        self.assertContains(response, "That e-mail address doesn't have an associated user account")
        self.assertEquals(len(mail.outbox), 0)
    
    def test_email_found(self):
        "Email is sent if a valid email address is provided for password reset"
        response = self.client.post('/password_reset/', {'email': 'staffmember@example.com'})
        self.assertEquals(response.status_code, 302)
        self.assertEquals(len(mail.outbox), 1)
        self.assert_("http://" in mail.outbox[0].body)

    def _test_confirm_start(self):
        # Start by creating the email
        response = self.client.post('/password_reset/', {'email': 'staffmember@example.com'})
        self.assertEquals(response.status_code, 302)
        self.assertEquals(len(mail.outbox), 1)
        return self._read_signup_email(mail.outbox[0])

    def _read_signup_email(self, email):
        urlmatch = re.search(r"https?://[^/]*(/.*reset/\S*)", email.body)
        self.assert_(urlmatch is not None, "No URL found in sent email")
        return urlmatch.group(), urlmatch.groups()[0]

    def test_confirm_valid(self):
        url, path = self._test_confirm_start()
        response = self.client.get(path)
        # redirect to a 'complete' page:
        self.assertEquals(response.status_code, 200) 
        self.assert_("Please enter your new password" in response.content)

    def test_confirm_invalid(self):
        url, path = self._test_confirm_start()
        # Lets munge the token in the path, but keep the same length,
        # in case the URL conf will reject a different length
        path = path[:-5] + ("0"*4) + path[-1]

        response = self.client.get(path)
        self.assertEquals(response.status_code, 200) 
        self.assert_("The password reset link was invalid" in response.content)

    def test_confirm_invalid_post(self):
        # Same as test_confirm_invalid, but trying
        # to do a POST instead.
        url, path = self._test_confirm_start()
        path = path[:-5] + ("0"*4) + path[-1]

        response = self.client.post(path, {'new_password1': 'anewpassword',
                                           'new_password2':' anewpassword'})
        # Check the password has not been changed 
        u = User.objects.get(email='staffmember@example.com')
        self.assert_(not u.check_password("anewpassword"))

    def test_confirm_complete(self):
        url, path = self._test_confirm_start()
        response = self.client.post(path, {'new_password1': 'anewpassword',
                                           'new_password2': 'anewpassword'})
        # It redirects us to a 'complete' page:
        self.assertEquals(response.status_code, 302) 
        # Check the password has been changed 
        u = User.objects.get(email='staffmember@example.com')
        self.assert_(u.check_password("anewpassword"))

        # Check we can't use the link again
        response = self.client.get(path)
        self.assertEquals(response.status_code, 200) 
        self.assert_("The password reset link was invalid" in response.content)

    def test_confirm_different_passwords(self):
        url, path = self._test_confirm_start()
        response = self.client.post(path, {'new_password1': 'anewpassword',
                                           'new_password2':' x'})
        self.assertEquals(response.status_code, 200)
        self.assert_("The two password fields didn't match" in response.content)

