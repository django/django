import warnings
from functools import update_wrapper, wraps
from unittest import TestCase

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import (
    login_required, permission_required, user_passes_test,
)
from django.http import HttpRequest, HttpResponse, HttpResponseNotAllowed
from django.middleware.clickjacking import XFrameOptionsMiddleware
from django.utils.decorators import method_decorator
from django.utils.functional import allow_lazy, lazy, memoize
from django.views.decorators.cache import (
    cache_control, cache_page, never_cache,
)
from django.views.decorators.clickjacking import (
    xframe_options_deny, xframe_options_exempt, xframe_options_sameorigin,
)
from django.views.decorators.http import (
    condition, require_GET, require_http_methods, require_POST, require_safe,
)
from django.views.decorators.vary import vary_on_cookie, vary_on_headers


def fully_decorated(request):
    """Expected __doc__"""
    return HttpResponse('<html><body>dummy</body></html>')
fully_decorated.anything = "Expected __dict__"


def compose(*functions):
    # compose(f, g)(*args, **kwargs) == f(g(*args, **kwargs))
    functions = list(reversed(functions))

    def _inner(*args, **kwargs):
        result = functions[0](*args, **kwargs)
        for f in functions[1:]:
            result = f(result)
        return result
    return _inner


full_decorator = compose(
    # django.views.decorators.http
    require_http_methods(["GET"]),
    require_GET,
    require_POST,
    require_safe,
    condition(lambda r: None, lambda r: None),

    # django.views.decorators.vary
    vary_on_headers('Accept-language'),
    vary_on_cookie,

    # django.views.decorators.cache
    cache_page(60 * 15),
    cache_control(private=True),
    never_cache,

    # django.contrib.auth.decorators
    # Apply user_passes_test twice to check #9474
    user_passes_test(lambda u: True),
    login_required,
    permission_required('change_world'),

    # django.contrib.admin.views.decorators
    staff_member_required,

    # django.utils.functional
    allow_lazy,
    lazy,
)

# suppress the deprecation warning of memoize
with warnings.catch_warnings():
    warnings.filterwarnings('ignore')
    fully_decorated = memoize(fully_decorated, {}, 1)

fully_decorated = full_decorator(fully_decorated)


class DecoratorsTest(TestCase):

    def test_attributes(self):
        """
        Tests that django decorators set certain attributes of the wrapped
        function.
        """
        self.assertEqual(fully_decorated.__name__, 'fully_decorated')
        self.assertEqual(fully_decorated.__doc__, 'Expected __doc__')
        self.assertEqual(fully_decorated.__dict__['anything'], 'Expected __dict__')

    def test_user_passes_test_composition(self):
        """
        Test that the user_passes_test decorator can be applied multiple times
        (#9474).
        """
        def test1(user):
            user.decorators_applied.append('test1')
            return True

        def test2(user):
            user.decorators_applied.append('test2')
            return True

        def callback(request):
            return request.user.decorators_applied

        callback = user_passes_test(test1)(callback)
        callback = user_passes_test(test2)(callback)

        class DummyUser(object):
            pass

        class DummyRequest(object):
            pass

        request = DummyRequest()
        request.user = DummyUser()
        request.user.decorators_applied = []
        response = callback(request)

        self.assertEqual(response, ['test2', 'test1'])

    def test_cache_page_new_style(self):
        """
        Test that we can call cache_page the new way
        """
        def my_view(request):
            return "response"
        my_view_cached = cache_page(123)(my_view)
        self.assertEqual(my_view_cached(HttpRequest()), "response")
        my_view_cached2 = cache_page(123, key_prefix="test")(my_view)
        self.assertEqual(my_view_cached2(HttpRequest()), "response")

    def test_require_safe_accepts_only_safe_methods(self):
        """
        Test for the require_safe decorator.
        A view returns either a response or an exception.
        Refs #15637.
        """
        def my_view(request):
            return HttpResponse("OK")
        my_safe_view = require_safe(my_view)
        request = HttpRequest()
        request.method = 'GET'
        self.assertIsInstance(my_safe_view(request), HttpResponse)
        request.method = 'HEAD'
        self.assertIsInstance(my_safe_view(request), HttpResponse)
        request.method = 'POST'
        self.assertIsInstance(my_safe_view(request), HttpResponseNotAllowed)
        request.method = 'PUT'
        self.assertIsInstance(my_safe_view(request), HttpResponseNotAllowed)
        request.method = 'DELETE'
        self.assertIsInstance(my_safe_view(request), HttpResponseNotAllowed)


# For testing method_decorator, a decorator that assumes a single argument.
# We will get type arguments if there is a mismatch in the number of arguments.
def simple_dec(func):
    def wrapper(arg):
        return func("test:" + arg)
    return wraps(func)(wrapper)

simple_dec_m = method_decorator(simple_dec)


# For testing method_decorator, two decorators that add an attribute to the function
def myattr_dec(func):
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    wrapper.myattr = True
    return wraps(func)(wrapper)

myattr_dec_m = method_decorator(myattr_dec)


def myattr2_dec(func):
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    wrapper.myattr2 = True
    return wraps(func)(wrapper)

myattr2_dec_m = method_decorator(myattr2_dec)


class ClsDec(object):
    def __init__(self, myattr):
        self.myattr = myattr

    def __call__(self, f):

        def wrapped():
            return f() and self.myattr
        return update_wrapper(wrapped, f)


class MethodDecoratorTests(TestCase):
    """
    Tests for method_decorator
    """
    def test_preserve_signature(self):
        class Test(object):
            @simple_dec_m
            def say(self, arg):
                return arg

        self.assertEqual("test:hello", Test().say("hello"))

    def test_preserve_attributes(self):
        # Sanity check myattr_dec and myattr2_dec
        @myattr_dec
        @myattr2_dec
        def func():
            pass

        self.assertEqual(getattr(func, 'myattr', False), True)
        self.assertEqual(getattr(func, 'myattr2', False), True)

        # Now check method_decorator
        class Test(object):
            @myattr_dec_m
            @myattr2_dec_m
            def method(self):
                "A method"
                pass

        self.assertEqual(getattr(Test().method, 'myattr', False), True)
        self.assertEqual(getattr(Test().method, 'myattr2', False), True)

        self.assertEqual(getattr(Test.method, 'myattr', False), True)
        self.assertEqual(getattr(Test.method, 'myattr2', False), True)

        self.assertEqual(Test.method.__doc__, 'A method')
        self.assertEqual(Test.method.__name__, 'method')

    # Test for argumented decorator
    def test_argumented(self):
        class Test(object):
            @method_decorator(ClsDec(False))
            def method(self):
                return True

        self.assertEqual(Test().method(), False)

    def test_descriptors(self):

        def original_dec(wrapped):
            def _wrapped(arg):
                return wrapped(arg)

            return _wrapped

        method_dec = method_decorator(original_dec)

        class bound_wrapper(object):
            def __init__(self, wrapped):
                self.wrapped = wrapped
                self.__name__ = wrapped.__name__

            def __call__(self, arg):
                return self.wrapped(arg)

            def __get__(self, instance, owner):
                return self

        class descriptor_wrapper(object):
            def __init__(self, wrapped):
                self.wrapped = wrapped
                self.__name__ = wrapped.__name__

            def __get__(self, instance, owner):
                return bound_wrapper(self.wrapped.__get__(instance, owner))

        class Test(object):
            @method_dec
            @descriptor_wrapper
            def method(self, arg):
                return arg

        self.assertEqual(Test().method(1), 1)


class XFrameOptionsDecoratorsTests(TestCase):
    """
    Tests for the X-Frame-Options decorators.
    """
    def test_deny_decorator(self):
        """
        Ensures @xframe_options_deny properly sets the X-Frame-Options header.
        """
        @xframe_options_deny
        def a_view(request):
            return HttpResponse()
        r = a_view(HttpRequest())
        self.assertEqual(r['X-Frame-Options'], 'DENY')

    def test_sameorigin_decorator(self):
        """
        Ensures @xframe_options_sameorigin properly sets the X-Frame-Options
        header.
        """
        @xframe_options_sameorigin
        def a_view(request):
            return HttpResponse()
        r = a_view(HttpRequest())
        self.assertEqual(r['X-Frame-Options'], 'SAMEORIGIN')

    def test_exempt_decorator(self):
        """
        Ensures @xframe_options_exempt properly instructs the
        XFrameOptionsMiddleware to NOT set the header.
        """
        @xframe_options_exempt
        def a_view(request):
            return HttpResponse()
        req = HttpRequest()
        resp = a_view(req)
        self.assertEqual(resp.get('X-Frame-Options', None), None)
        self.assertTrue(resp.xframe_options_exempt)

        # Since the real purpose of the exempt decorator is to suppress
        # the middleware's functionality, let's make sure it actually works...
        r = XFrameOptionsMiddleware().process_response(req, resp)
        self.assertEqual(r.get('X-Frame-Options', None), None)


class NeverCacheDecoratorTest(TestCase):
    def test_never_cache_decorator(self):
        @never_cache
        def a_view(request):
            return HttpResponse()
        r = a_view(HttpRequest())
        self.assertEqual(
            set(r['Cache-Control'].split(', ')),
            {'max-age=0', 'no-cache', 'no-store', 'must-revalidate'},
        )
