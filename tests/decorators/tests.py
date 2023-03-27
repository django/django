from functools import update_wrapper, wraps
from io import StringIO
from unittest import TestCase, mock

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import (
    login_required,
    permission_required,
    user_passes_test,
)
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.http import HttpRequest, HttpResponse, HttpResponseNotAllowed
from django.middleware.clickjacking import XFrameOptionsMiddleware
from django.test import SimpleTestCase
from django.utils.datastructures import MultiValueDict
from django.utils.decorators import method_decorator
from django.utils.functional import keep_lazy, keep_lazy_text, lazy
from django.utils.safestring import mark_safe
from django.views import View
from django.views.decorators.cache import cache_control, cache_page, never_cache
from django.views.decorators.clickjacking import (
    xframe_options_deny,
    xframe_options_exempt,
    xframe_options_sameorigin,
)
from django.views.decorators.http import (
    condition,
    require_files,
    require_GET,
    require_http_methods,
    require_POST,
    require_safe,
)
from django.views.decorators.vary import vary_on_cookie, vary_on_headers


def fully_decorated(request):
    """Expected __doc__"""
    return HttpResponse("<html><body>dummy</body></html>")


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
    vary_on_headers("Accept-language"),
    vary_on_cookie,
    # django.views.decorators.cache
    cache_page(60 * 15),
    cache_control(private=True),
    never_cache,
    # django.contrib.auth.decorators
    # Apply user_passes_test twice to check #9474
    user_passes_test(lambda u: True),
    login_required,
    permission_required("change_world"),
    # django.contrib.admin.views.decorators
    staff_member_required,
    # django.utils.functional
    keep_lazy(HttpResponse),
    keep_lazy_text,
    lazy,
    # django.utils.safestring
    mark_safe,
)

fully_decorated = full_decorator(fully_decorated)


class DecoratorsTest(TestCase):
    def test_attributes(self):
        """
        Built-in decorators set certain attributes of the wrapped function.
        """
        self.assertEqual(fully_decorated.__name__, "fully_decorated")
        self.assertEqual(fully_decorated.__doc__, "Expected __doc__")
        self.assertEqual(fully_decorated.__dict__["anything"], "Expected __dict__")

    def test_user_passes_test_composition(self):
        """
        The user_passes_test decorator can be applied multiple times (#9474).
        """

        def test1(user):
            user.decorators_applied.append("test1")
            return True

        def test2(user):
            user.decorators_applied.append("test2")
            return True

        def callback(request):
            return request.user.decorators_applied

        callback = user_passes_test(test1)(callback)
        callback = user_passes_test(test2)(callback)

        class DummyUser:
            pass

        class DummyRequest:
            pass

        request = DummyRequest()
        request.user = DummyUser()
        request.user.decorators_applied = []
        response = callback(request)

        self.assertEqual(response, ["test2", "test1"])

    def test_cache_page(self):
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
        request.method = "GET"
        self.assertIsInstance(my_safe_view(request), HttpResponse)
        request.method = "HEAD"
        self.assertIsInstance(my_safe_view(request), HttpResponse)
        request.method = "POST"
        self.assertIsInstance(my_safe_view(request), HttpResponseNotAllowed)
        request.method = "PUT"
        self.assertIsInstance(my_safe_view(request), HttpResponseNotAllowed)
        request.method = "DELETE"
        self.assertIsInstance(my_safe_view(request), HttpResponseNotAllowed)


# For testing method_decorator, a decorator that assumes a single argument.
# We will get type arguments if there is a mismatch in the number of arguments.
def simple_dec(func):
    @wraps(func)
    def wrapper(arg):
        return func("test:" + arg)

    return wrapper


simple_dec_m = method_decorator(simple_dec)


# For testing method_decorator, two decorators that add an attribute to the function
def myattr_dec(func):
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    wrapper.myattr = True
    return wrapper


myattr_dec_m = method_decorator(myattr_dec)


def myattr2_dec(func):
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    wrapper.myattr2 = True
    return wrapper


myattr2_dec_m = method_decorator(myattr2_dec)


class ClsDec:
    def __init__(self, myattr):
        self.myattr = myattr

    def __call__(self, f):
        def wrapper():
            return f() and self.myattr

        return update_wrapper(wrapper, f)


class MethodDecoratorTests(SimpleTestCase):
    """
    Tests for method_decorator
    """

    def test_preserve_signature(self):
        class Test:
            @simple_dec_m
            def say(self, arg):
                return arg

        self.assertEqual("test:hello", Test().say("hello"))

    def test_preserve_attributes(self):
        # Sanity check myattr_dec and myattr2_dec
        @myattr_dec
        def func():
            pass

        self.assertIs(getattr(func, "myattr", False), True)

        @myattr2_dec
        def func():
            pass

        self.assertIs(getattr(func, "myattr2", False), True)

        @myattr_dec
        @myattr2_dec
        def func():
            pass

        self.assertIs(getattr(func, "myattr", False), True)
        self.assertIs(getattr(func, "myattr2", False), False)

        # Decorate using method_decorator() on the method.
        class TestPlain:
            @myattr_dec_m
            @myattr2_dec_m
            def method(self):
                "A method"
                pass

        # Decorate using method_decorator() on both the class and the method.
        # The decorators applied to the methods are applied before the ones
        # applied to the class.
        @method_decorator(myattr_dec_m, "method")
        class TestMethodAndClass:
            @method_decorator(myattr2_dec_m)
            def method(self):
                "A method"
                pass

        # Decorate using an iterable of function decorators.
        @method_decorator((myattr_dec, myattr2_dec), "method")
        class TestFunctionIterable:
            def method(self):
                "A method"
                pass

        # Decorate using an iterable of method decorators.
        decorators = (myattr_dec_m, myattr2_dec_m)

        @method_decorator(decorators, "method")
        class TestMethodIterable:
            def method(self):
                "A method"
                pass

        tests = (
            TestPlain,
            TestMethodAndClass,
            TestFunctionIterable,
            TestMethodIterable,
        )
        for Test in tests:
            with self.subTest(Test=Test):
                self.assertIs(getattr(Test().method, "myattr", False), True)
                self.assertIs(getattr(Test().method, "myattr2", False), True)
                self.assertIs(getattr(Test.method, "myattr", False), True)
                self.assertIs(getattr(Test.method, "myattr2", False), True)
                self.assertEqual(Test.method.__doc__, "A method")
                self.assertEqual(Test.method.__name__, "method")

    def test_new_attribute(self):
        """A decorator that sets a new attribute on the method."""

        def decorate(func):
            func.x = 1
            return func

        class MyClass:
            @method_decorator(decorate)
            def method(self):
                return True

        obj = MyClass()
        self.assertEqual(obj.method.x, 1)
        self.assertIs(obj.method(), True)

    def test_bad_iterable(self):
        decorators = {myattr_dec_m, myattr2_dec_m}
        msg = "'set' object is not subscriptable"
        with self.assertRaisesMessage(TypeError, msg):

            @method_decorator(decorators, "method")
            class TestIterable:
                def method(self):
                    "A method"
                    pass

    # Test for argumented decorator
    def test_argumented(self):
        class Test:
            @method_decorator(ClsDec(False))
            def method(self):
                return True

        self.assertIs(Test().method(), False)

    def test_descriptors(self):
        def original_dec(wrapped):
            def _wrapped(arg):
                return wrapped(arg)

            return _wrapped

        method_dec = method_decorator(original_dec)

        class bound_wrapper:
            def __init__(self, wrapped):
                self.wrapped = wrapped
                self.__name__ = wrapped.__name__

            def __call__(self, arg):
                return self.wrapped(arg)

            def __get__(self, instance, cls=None):
                return self

        class descriptor_wrapper:
            def __init__(self, wrapped):
                self.wrapped = wrapped
                self.__name__ = wrapped.__name__

            def __get__(self, instance, cls=None):
                return bound_wrapper(self.wrapped.__get__(instance, cls))

        class Test:
            @method_dec
            @descriptor_wrapper
            def method(self, arg):
                return arg

        self.assertEqual(Test().method(1), 1)

    def test_class_decoration(self):
        """
        @method_decorator can be used to decorate a class and its methods.
        """

        def deco(func):
            def _wrapper(*args, **kwargs):
                return True

            return _wrapper

        @method_decorator(deco, name="method")
        class Test:
            def method(self):
                return False

        self.assertTrue(Test().method())

    def test_tuple_of_decorators(self):
        """
        @method_decorator can accept a tuple of decorators.
        """

        def add_question_mark(func):
            def _wrapper(*args, **kwargs):
                return func(*args, **kwargs) + "?"

            return _wrapper

        def add_exclamation_mark(func):
            def _wrapper(*args, **kwargs):
                return func(*args, **kwargs) + "!"

            return _wrapper

        # The order should be consistent with the usual order in which
        # decorators are applied, e.g.
        #    @add_exclamation_mark
        #    @add_question_mark
        #    def func():
        #        ...
        decorators = (add_exclamation_mark, add_question_mark)

        @method_decorator(decorators, name="method")
        class TestFirst:
            def method(self):
                return "hello world"

        class TestSecond:
            @method_decorator(decorators)
            def method(self):
                return "hello world"

        self.assertEqual(TestFirst().method(), "hello world?!")
        self.assertEqual(TestSecond().method(), "hello world?!")

    def test_invalid_non_callable_attribute_decoration(self):
        """
        @method_decorator on a non-callable attribute raises an error.
        """
        msg = (
            "Cannot decorate 'prop' as it isn't a callable attribute of "
            "<class 'Test'> (1)"
        )
        with self.assertRaisesMessage(TypeError, msg):

            @method_decorator(lambda: None, name="prop")
            class Test:
                prop = 1

                @classmethod
                def __module__(cls):
                    return "tests"

    def test_invalid_method_name_to_decorate(self):
        """
        @method_decorator on a nonexistent method raises an error.
        """
        msg = (
            "The keyword argument `name` must be the name of a method of the "
            "decorated class: <class 'Test'>. Got 'nonexistent_method' instead"
        )
        with self.assertRaisesMessage(ValueError, msg):

            @method_decorator(lambda: None, name="nonexistent_method")
            class Test:
                @classmethod
                def __module__(cls):
                    return "tests"

    def test_wrapper_assignments(self):
        """@method_decorator preserves wrapper assignments."""
        func_name = None
        func_module = None

        def decorator(func):
            @wraps(func)
            def inner(*args, **kwargs):
                nonlocal func_name, func_module
                func_name = getattr(func, "__name__", None)
                func_module = getattr(func, "__module__", None)
                return func(*args, **kwargs)

            return inner

        class Test:
            @method_decorator(decorator)
            def method(self):
                return "tests"

        Test().method()
        self.assertEqual(func_name, "method")
        self.assertIsNotNone(func_module)


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
        self.assertEqual(r.headers["X-Frame-Options"], "DENY")

    def test_sameorigin_decorator(self):
        """
        Ensures @xframe_options_sameorigin properly sets the X-Frame-Options
        header.
        """

        @xframe_options_sameorigin
        def a_view(request):
            return HttpResponse()

        r = a_view(HttpRequest())
        self.assertEqual(r.headers["X-Frame-Options"], "SAMEORIGIN")

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
        self.assertIsNone(resp.get("X-Frame-Options", None))
        self.assertTrue(resp.xframe_options_exempt)

        # Since the real purpose of the exempt decorator is to suppress
        # the middleware's functionality, let's make sure it actually works...
        r = XFrameOptionsMiddleware(a_view)(req)
        self.assertIsNone(r.get("X-Frame-Options", None))


class HttpRequestProxy:
    def __init__(self, request):
        self._request = request

    def __getattr__(self, attr):
        """Proxy to the underlying HttpRequest object."""
        return getattr(self._request, attr)


class NeverCacheDecoratorTest(SimpleTestCase):
    @mock.patch("time.time")
    def test_never_cache_decorator_headers(self, mocked_time):
        @never_cache
        def a_view(request):
            return HttpResponse()

        mocked_time.return_value = 1167616461.0
        response = a_view(HttpRequest())
        self.assertEqual(
            response.headers["Expires"],
            "Mon, 01 Jan 2007 01:54:21 GMT",
        )
        self.assertEqual(
            response.headers["Cache-Control"],
            "max-age=0, no-cache, no-store, must-revalidate, private",
        )

    def test_never_cache_decorator_expires_not_overridden(self):
        @never_cache
        def a_view(request):
            return HttpResponse(headers={"Expires": "tomorrow"})

        response = a_view(HttpRequest())
        self.assertEqual(response.headers["Expires"], "tomorrow")

    def test_never_cache_decorator_http_request(self):
        class MyClass:
            @never_cache
            def a_view(self, request):
                return HttpResponse()

        request = HttpRequest()
        msg = (
            "never_cache didn't receive an HttpRequest. If you are decorating "
            "a classmethod, be sure to use @method_decorator."
        )
        with self.assertRaisesMessage(TypeError, msg):
            MyClass().a_view(request)
        with self.assertRaisesMessage(TypeError, msg):
            MyClass().a_view(HttpRequestProxy(request))

    def test_never_cache_decorator_http_request_proxy(self):
        class MyClass:
            @method_decorator(never_cache)
            def a_view(self, request):
                return HttpResponse()

        request = HttpRequest()
        response = MyClass().a_view(HttpRequestProxy(request))
        self.assertIn("Cache-Control", response.headers)
        self.assertIn("Expires", response.headers)


class CacheControlDecoratorTest(SimpleTestCase):
    def test_cache_control_decorator_http_request(self):
        class MyClass:
            @cache_control(a="b")
            def a_view(self, request):
                return HttpResponse()

        msg = (
            "cache_control didn't receive an HttpRequest. If you are "
            "decorating a classmethod, be sure to use @method_decorator."
        )
        request = HttpRequest()
        with self.assertRaisesMessage(TypeError, msg):
            MyClass().a_view(request)
        with self.assertRaisesMessage(TypeError, msg):
            MyClass().a_view(HttpRequestProxy(request))

    def test_cache_control_decorator_http_request_proxy(self):
        class MyClass:
            @method_decorator(cache_control(a="b"))
            def a_view(self, request):
                return HttpResponse()

        request = HttpRequest()
        response = MyClass().a_view(HttpRequestProxy(request))
        self.assertEqual(response.headers["Cache-Control"], "a=b")


class RequireFilesDecoratorTest(TestCase):
    """
    Tests for the require_files decorators.
    """

    def setUp(self):
        self.request = HttpRequest()
        self.request.method = "POST"
        self.txt_file = InMemoryUploadedFile(
            StringIO("1"), "", "test.txt", "text/plain", 1, "utf8"
        )
        self.pdf_file_large = InMemoryUploadedFile(
            StringIO("1"), "", "test.pdf", "text/plain", 100_000_00, "utf8"
        )
        self.file_docx = InMemoryUploadedFile(
            StringIO("1"),
            "",
            "test.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            100_000_00,
            "utf8",
        )

    def run_test_view(
        self,
        extension_list,
        files,
        file_size=0,
        invalid_file_size=False,
        invalid_file_type=False,
        request_method="POST",
    ):
        """
        This method run_test_view will be called on each test scenarios and
        check the file validity.

        Parameters:
            extension_list (list of str): List of file extensions.
            files (list of File objects): List of files to be uploaded.
            file_size (int): Maximum allowed file size in MB.
            invalid_file_type (bool, optional): Whether to test with invalid
            file type. Defaults to False.
            invalid_file_size (bool, optional): Whether to test with invalid
            file size. Defaults to False.
            request_method (http): Request method type (POST or GET etc).
            Defaults to Post.

        Raises:
            TypeError: If an uploaded file has an invalid extension.
            IOError: If an uploaded file size exceeds the limit.
            HttpResponseNotAllowed: This error occurs when the client sends a request
            to the server using an HTTP method that is not allowed.
        """

        # This is a function-based views for testing the decorator.
        @require_files(extension_list, file_size)
        def test_view(request):
            return HttpResponse()

        class MyView(View):
            """
            This is a class-based views for testing the decorator.
            """

            @method_decorator(require_files(extension_list, file_size), name="dispatch")
            def post(self, request, *args, **kwargs):
                return HttpResponse()

            @method_decorator(require_files(extension_list, file_size), name="dispatch")
            def get(self, request, *args, **kwargs):
                return HttpResponse()

        self.request.method = request_method
        self.request.FILES = MultiValueDict({"file": files})

        # This will check if file size is invalid then raise
        # IOError with a message ('This file exceeds the limit')
        if invalid_file_size:
            with self.assertRaises(IOError) as error:
                test_view(self.request)
                MyView().post(self.request)

            self.assertEqual(str(error.exception), "This file exceeds the limit.")

        # This condition will verify that @require_files raises a TypeError
        # with the appropriate error message for invalid file type.
        elif invalid_file_type:
            with self.assertRaises(TypeError) as error:
                test_view(self.request)
                MyView().post(self.request)
            self.assertEqual(str(error.exception), "This file type is not accepted.")

        # This will check if method is not POST, then raise 405 error.
        elif self.request.method != "POST":
            function_response = test_view(self.request)
            class_response = MyView().get(self.request)
            self.assertEqual(function_response.status_code, 405)
            self.assertEqual(class_response.status_code, 405)

        # If no error then check if it return 200 response.
        else:
            function_response = test_view(self.request)
            class_response = MyView().post(self.request)
            self.assertEqual(function_response.status_code, 200)
            self.assertEqual(class_response.status_code, 200)

    def test_valid_file_types(self):
        """
        Uploading a file with an accepted extension and size within the limit.
        """
        self.run_test_view(["txt", "pdf"], [self.pdf_file_large, self.txt_file], 10)

    def test_invalid_file_types(self):
        """
        Uploading a file with an unaccepted extension and size within the limit.
        We are passing invalid_file_type=True as it will raise error.
        """
        self.run_test_view(
            extension_list=["txt"],
            files=[self.pdf_file_large],
            file_size=1,
            invalid_file_type=True,
        )

        self.run_test_view(
            extension_list=["docx"],
            files=[self.pdf_file_large],
            file_size=1,
            invalid_file_type=True,
        )

        self.run_test_view(
            extension_list=["pdf"],
            files=[self.txt_file],
            file_size=1,
            invalid_file_type=True,
        )

    def test_valid_file_size(self):
        """
        Uploads file within 10 MB limit and with valid extension.
        """
        self.run_test_view(["pdf", "txt"], [self.pdf_file_large, self.txt_file], 10)

    def test_invalid_file_size(self):
        """
        Testing with a file of accepted extension but size exceeding the 1MB limit.
        Passing invalid_file_size=True to ensure it will raise IOError.
        """

        self.run_test_view(
            extension_list=["pdf"],
            files=[self.pdf_file_large],
            file_size=1,
            invalid_file_size=True,
        )
        self.run_test_view(
            extension_list=["pdf", "txt"],
            files=[self.txt_file, self.pdf_file_large],
            file_size=1,
            invalid_file_size=True,
        )

    def test_with_no_file_size(self):
        """
        Uploading a file with an accepted extension but without passing size
        in decorator.
        """

        self.run_test_view(
            extension_list=["pdf", "txt"],
            files=[self.txt_file, self.pdf_file_large],
        )
        self.run_test_view(
            extension_list=["docx"],
            files=[self.file_docx],
        )
        self.run_test_view(
            extension_list=["pdf"],
            files=[self.pdf_file_large],
        )

    def test_no_file_in_request(self):
        """
        Testing the empty file list with the decorator to ensure no errors are raised.
        """
        self.run_test_view(extension_list=["pdf", "txt"], files=[], file_size=1)
        self.run_test_view(extension_list=["txt"], files=[], file_size=1)

    def test_no_file_types_in_decorator(self):
        # Not uploading any file types.
        self.run_test_view(extension_list=[], files=[], file_size=2)

        # Need to pass extension_list if files are being passed, else TypeError
        # error will be raised.
        self.run_test_view(
            extension_list=[],
            files=[self.file_docx],
            file_size=5,
            invalid_file_type=True,
        )

    def test_no_filename(self):
        """
        Uploading a file without any name.
        We had passed invalid_file_type=True as file name is empty(invalid),
        so it will raise a TypeError in run_test_view method.
        """
        empty_name_file = InMemoryUploadedFile(
            StringIO("1"), "", " ", "text/plain", 1, "utf8"
        )

        self.run_test_view(
            extension_list=["pdf"],
            files=[empty_name_file],
            file_size=10,
            invalid_file_type=True,
        )

    def test_extension_less_file(self):
        """
        Uploading a file without any extension.
        We had passed invalid_file_type=True as file extension is empty(invalid),
        so it will raise a TypeError.
        """
        self.extension_less_file = InMemoryUploadedFile(
            StringIO("1"), "", "test", "", 100_000_00, "utf8"
        )

        self.run_test_view(
            extension_list=["txt"],
            files=[self.extension_less_file],
            file_size=10,
            invalid_file_type=True,
        )

    def test_post_request(self):
        """
        Uploading a file in POST request.
        In last we are passing request_method="POST" to make sure it doesn't raises
        any error.
        """
        self.run_test_view(
            extension_list=["txt"],
            files=[self.txt_file],
            file_size=20,
            request_method="POST",
        )

    def test_other_requests(self):
        """
        If the request method is not POST and the decorator is applied with
        request_method="GET, PUT, DELETE, etc", a 405 error will be raised.
        """
        self.run_test_view(
            extension_list=["txt"],
            files=[self.txt_file],
            file_size=20,
            request_method="GET",
        )

        self.run_test_view(
            extension_list=["txt"],
            files=[self.txt_file],
            file_size=20,
            request_method="DELETE",
        )

        self.run_test_view(
            extension_list=["txt"],
            files=[self.txt_file],
            file_size=20,
            request_method="PUT",
        )
