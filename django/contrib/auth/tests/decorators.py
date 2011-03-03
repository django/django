from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.tests.views import AuthViewsTestCase

class LoginRequiredTestCase(AuthViewsTestCase):
    """
    Tests the login_required decorators
    """
    urls = 'django.contrib.auth.tests.urls'

    def testCallable(self):
        """
        Check that login_required is assignable to callable objects.
        """
        class CallableView(object):
            def __call__(self, *args, **kwargs):
                pass
        login_required(CallableView())

    def testView(self):
        """
        Check that login_required is assignable to normal views.
        """
        def normal_view(request):
            pass
        login_required(normal_view)

    def testLoginRequired(self, view_url='/login_required/', login_url=settings.LOGIN_URL):
        """
        Check that login_required works on a simple view wrapped in a
        login_required decorator.
        """
        response = self.client.get(view_url)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(login_url in response['Location'])
        self.login()
        response = self.client.get(view_url)
        self.assertEqual(response.status_code, 200)

    def testLoginRequiredNextUrl(self):
        """
        Check that login_required works on a simple view wrapped in a
        login_required decorator with a login_url set.
        """
        self.testLoginRequired(view_url='/login_required_login_url/',
            login_url='/somewhere/')
