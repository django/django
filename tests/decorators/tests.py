import asyncio
from functools import update_wrapper, wraps
from unittest import TestCase

from asgiref.sync import iscoroutinefunction

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import (
    login_required,
    permission_required,
    user_passes_test,
)
from django.http import HttpResponse
from django.test import SimpleTestCase
from django.utils.decorators import method_decorator
from django.utils.functional import keep_lazy, keep_lazy_text, lazy
from django.utils.safestring import mark_safe
from django.views.decorators.cache import cache_control, cache_page, never_cache
from django.views.decorators.http import (
    condition,
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


def async_simple_dec(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        result = await func(*args, **kwargs)
        return f"returned: {result}"

    return wrapper


async_simple_dec_m = method_decorator(async_simple_dec)


class AsyncMethodDecoratorTests(SimpleTestCase):
    """
    Tests for async method_decorator
    """

    async def test_preserve_signature(self):
        class Test:
            @async_simple_dec_m
            async def say(self, msg):
                return f"Saying {msg}"

        self.assertEqual(await Test().say("hello"), "returned: Saying hello")

    def test_preserve_attributes(self):
        async def func(*args, **kwargs):
            await asyncio.sleep(0.01)
            return args, kwargs

        def myattr_dec(func):
            async def wrapper(*args, **kwargs):
                return await func(*args, **kwargs)

            wrapper.myattr = True
            return wrapper

        def myattr2_dec(func):
            async def wrapper(*args, **kwargs):
                return await func(*args, **kwargs)

            wrapper.myattr2 = True
            return wrapper

        # Sanity check myattr_dec and myattr2_dec
        func = myattr_dec(func)

        self.assertIs(getattr(func, "myattr", False), True)

        func = myattr2_dec(func)
        self.assertIs(getattr(func, "myattr2", False), True)

        func = myattr_dec(myattr2_dec(func))
        self.assertIs(getattr(func, "myattr", False), True)
        self.assertIs(getattr(func, "myattr2", False), False)

        myattr_dec_m = method_decorator(myattr_dec)
        myattr2_dec_m = method_decorator(myattr2_dec)

        # Decorate using method_decorator() on the async method.
        class TestPlain:
            @myattr_dec_m
            @myattr2_dec_m
            async def method(self):
                "A method"

        # Decorate using method_decorator() on both the class and the method.
        # The decorators applied to the methods are applied before the ones
        # applied to the class.
        @method_decorator(myattr_dec_m, "method")
        class TestMethodAndClass:
            @method_decorator(myattr2_dec_m)
            async def method(self):
                "A method"

        # Decorate using an iterable of function decorators.
        @method_decorator((myattr_dec, myattr2_dec), "method")
        class TestFunctionIterable:
            async def method(self):
                "A method"

        # Decorate using an iterable of method decorators.
        @method_decorator((myattr_dec_m, myattr2_dec_m), "method")
        class TestMethodIterable:
            async def method(self):
                "A method"

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

    async def test_new_attribute(self):
        """A decorator that sets a new attribute on the method."""

        def decorate(func):
            func.x = 1
            return func

        class MyClass:
            @method_decorator(decorate)
            async def method(self):
                return True

        obj = MyClass()
        self.assertEqual(obj.method.x, 1)
        self.assertIs(await obj.method(), True)

    def test_bad_iterable(self):
        decorators = {async_simple_dec}
        msg = "'set' object is not subscriptable"
        with self.assertRaisesMessage(TypeError, msg):

            @method_decorator(decorators, "method")
            class TestIterable:
                async def method(self):
                    await asyncio.sleep(0.01)

    async def test_argumented(self):

        class ClsDecAsync:
            def __init__(self, myattr):
                self.myattr = myattr

            def __call__(self, f):
                async def wrapper():
                    result = await f()
                    return f"{result} appending {self.myattr}"

                return update_wrapper(wrapper, f)

        class Test:
            @method_decorator(ClsDecAsync(False))
            async def method(self):
                return True

        self.assertEqual(await Test().method(), "True appending False")

    async def test_descriptors(self):
        class bound_wrapper:
            def __init__(self, wrapped):
                self.wrapped = wrapped
                self.__name__ = wrapped.__name__

            async def __call__(self, *args, **kwargs):
                return await self.wrapped(*args, **kwargs)

            def __get__(self, instance, cls=None):
                return self

        class descriptor_wrapper:
            def __init__(self, wrapped):
                self.wrapped = wrapped
                self.__name__ = wrapped.__name__

            def __get__(self, instance, cls=None):
                return bound_wrapper(self.wrapped.__get__(instance, cls))

        class Test:
            @async_simple_dec_m
            @descriptor_wrapper
            async def method(self, arg):
                return arg

        self.assertEqual(await Test().method(1), "returned: 1")

    async def test_class_decoration(self):
        """
        @method_decorator can be used to decorate a class and its methods.
        """

        @method_decorator(async_simple_dec, name="method")
        class Test:
            async def method(self):
                return False

            async def not_method(self):
                return "a string"

        self.assertEqual(await Test().method(), "returned: False")
        self.assertEqual(await Test().not_method(), "a string")

    async def test_tuple_of_decorators(self):
        """
        @method_decorator can accept a tuple of decorators.
        """

        def add_question_mark(func):
            async def _wrapper(*args, **kwargs):
                await asyncio.sleep(0.01)
                return await func(*args, **kwargs) + "?"

            return _wrapper

        def add_exclamation_mark(func):
            async def _wrapper(*args, **kwargs):
                await asyncio.sleep(0.01)
                return await func(*args, **kwargs) + "!"

            return _wrapper

        decorators = (add_exclamation_mark, add_question_mark)

        @method_decorator(decorators, name="method")
        class TestFirst:
            async def method(self):
                return "hello world"

        class TestSecond:
            @method_decorator(decorators)
            async def method(self):
                return "world hello"

        self.assertEqual(await TestFirst().method(), "hello world?!")
        self.assertEqual(await TestSecond().method(), "world hello?!")

    async def test_wrapper_assignments(self):
        """@method_decorator preserves wrapper assignments."""
        func_data = {}

        def decorator(func):
            @wraps(func)
            async def inner(*args, **kwargs):
                func_data["func_name"] = getattr(func, "__name__", None)
                func_data["func_module"] = getattr(func, "__module__", None)
                return await func(*args, **kwargs)

            return inner

        class Test:
            @method_decorator(decorator)
            async def method(self):
                return "tests"

        await Test().method()
        expected = {"func_name": "method", "func_module": "decorators.tests"}
        self.assertEqual(func_data, expected)

    async def test_markcoroutinefunction_applied(self):
        class Test:
            @async_simple_dec_m
            async def method(self):
                return "tests"

        method = Test().method
        self.assertIs(iscoroutinefunction(method), True)
        self.assertEqual(await method(), "returned: tests")
