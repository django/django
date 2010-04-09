from unittest import TestCase

from django.contrib.auth.decorators import login_required


class LoginRequiredTestCase(TestCase):
    """
    Tests the login_required decorators
    """
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