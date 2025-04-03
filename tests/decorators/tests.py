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
from django.utils.decorators import method_decorator, method_decorator_with_args
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


# For testing method_decorator_with_args, a decorator that expects a decorator_factory
# We will get type arguments if there is a mismatch in the number of arguments.
def simple_dec_factory(prefix_value="empty:"):
    def decorator(func):
        @wraps(func)
        def wrapper(arg):
            return func(prefix_value + arg)

        return wrapper

    return decorator


simple_dec_w_args_m = method_decorator_with_args(simple_dec_factory)


# For testing method_decorator_with_args, two decorators that add an attribute to the function
def myattr_dec_factory(value="no value"):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        wrapper.myattr = True
        wrapper.value1 = value
        return wrapper

    return decorator


myattr_dec_with_args_m = method_decorator_with_args(myattr_dec_factory)


def myattr2_dec_factory(value="no value"):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        wrapper.myattr2 = True
        wrapper.value2 = value
        return wrapper

    return decorator


myattr2_dec_with_args_m = method_decorator_with_args(myattr2_dec_factory)


class MethodDecoratorWithArgsTests(SimpleTestCase):
    """
    Tests for method_decorator_with_args
    """

    def test_preserve_signature(self):
        class Test:
            @simple_dec_w_args_m("test:")
            def say(self, arg):
                return arg

            @simple_dec_w_args_m("test again:")
            def say_again(self, arg):
                return arg

        self.assertEqual("test:hello", Test().say("hello"))
        self.assertEqual("test again:hello", Test().say_again("hello"))

    def test_preserve_attributes(self):
        @myattr_dec_factory("func_pass")
        def func():
            pass

        self.assertIs(getattr(func, "myattr", False), True)
        self.assertIs(getattr(func, "value1", ""), "func_pass")

        @myattr2_dec_factory("func_pass_2")
        def func():
            pass

        self.assertIs(getattr(func, "myattr2", False), True)
        self.assertIs(getattr(func, "value2", ""), "func_pass_2")

        @myattr_dec_factory("func_pass_3")
        @myattr2_dec_factory("func_pass_4")
        def func():
            pass

        self.assertIs(getattr(func, "myattr", False), True)
        self.assertIs(getattr(func, "value1", ""), "func_pass_3")
        self.assertIs(getattr(func, "myattr2", False), True)
        self.assertIs(getattr(func, "value2", ""), "func_pass_4")

        class TestPlain:
            @myattr_dec_with_args_m("method_pass_1")
            @myattr2_dec_with_args_m("method_pass_2")
            def method(self):
                "A method"
                pass

        # Decorate using method_decorator() on both the class and the method.
        # The decorators applied to the methods are applied before the ones
        # applied to the class.
        @method_decorator(myattr_dec_with_args_m("method_pass_1"), "method")
        class TestMethodAndClass:
            @method_decorator(myattr2_dec_with_args_m("method_pass_2"))
            def method(self):
                "A method"
                pass

        # Decorate using an iterable of method decorators.
        decorators = (
            myattr_dec_with_args_m("method_pass_1"),
            myattr2_dec_with_args_m("method_pass_2"),
        )

        @method_decorator(decorators, "method")
        class TestMethodIterable:
            def method(self):
                "A method"
                pass

        tests = (
            TestPlain,
            TestMethodAndClass,
            TestMethodIterable,
        )
        for Test in tests:
            with self.subTest(Test=Test):
                self.assertIs(getattr(Test().method, "myattr", False), True)
                self.assertIs(getattr(Test().method, "myattr2", False), True)
                self.assertIs(getattr(Test.method, "myattr", False), True)
                self.assertIs(getattr(Test.method, "myattr2", False), True)
                self.assertIs(getattr(Test().method, "value1", ""), "method_pass_1")
                self.assertIs(getattr(Test().method, "value2", ""), "method_pass_2")
                self.assertIs(getattr(Test.method, "value1", ""), "method_pass_1")
                self.assertIs(getattr(Test.method, "value2", ""), "method_pass_2")
                self.assertEqual(Test.method.__doc__, "A method")
                self.assertEqual(Test.method.__name__, "method")

    def test_new_attribute(self):
        """A decorator that sets a new attribute on the method."""

        def decorator_factory(attr_name=None, attr_value=None):
            def decorator(func):
                @wraps(func)
                def wrapper(*args, **kwargs):
                    return func(*args, **kwargs)

                if attr_name is not None:
                    setattr(wrapper, attr_name, attr_value)
                return wrapper

            return decorator

        decorator_w_args = method_decorator_with_args(decorator_factory)

        class MyClass:
            @decorator_w_args("x", 1)
            def method(self):
                return True

        obj = MyClass()
        self.assertEqual(obj.method.x, 1)
        self.assertIs(obj.method(), True)

    def test_descriptors(self):
        def original_dec_factory(base_value: int):
            def original_dec(wrapped):
                def _wrapped(arg: int):
                    return wrapped(base_value + arg)

                return _wrapped

            return original_dec

        method_dec_with_args = method_decorator_with_args(original_dec_factory)

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
            @method_dec_with_args(5)
            @descriptor_wrapper
            def method(self, arg):
                return arg

        self.assertEqual(Test().method(1), 6)

    def test_class_decoration(self):
        """
        @method_decorator_with_args can be used to decorate a class and its methods.
        """

        def deco_factory(return_value):
            def deco(func):
                def _wrapper(*args, **kwargs):
                    return return_value

                return _wrapper

            return deco

        deco_with_args = method_decorator_with_args(deco_factory, name="method")

        @deco_with_args(True)
        class Test:
            def method(self):
                return False

        @deco_with_args(None)
        class TestAgain:
            def method(self):
                return False

        self.assertTrue(Test().method())
        self.assertIsNone(TestAgain().method())

    def test_invalid_non_callable_attribute_decoration(self):
        """
        method_decorator_with_args on a non-callable attribute raises an error.
        """

        def deco_factory(return_value):
            def deco(func):
                def _wrapper(*args, **kwargs):
                    return return_value

                return _wrapper

            return deco

        deco_with_args = method_decorator_with_args(deco_factory, name="prop")
        msg = (
            "Cannot decorate 'prop' as it isn't a callable attribute of "
            "<class 'Test'> (1)"
        )
        with self.assertRaisesMessage(TypeError, msg):

            @deco_with_args(5)
            class Test:
                prop = 1

                @classmethod
                def __module__(cls):
                    return "tests"

    def test_invalid_method_name_to_decorate(self):
        """
        @method_decorator_with_args on a nonexistent method raises an error.
        """

        def deco_factory(return_value):
            def deco(func):
                def _wrapper(*args, **kwargs):
                    return return_value

                return _wrapper

            return deco

        deco_with_args = method_decorator_with_args(
            deco_factory, name="nonexistent_method"
        )
        msg = (
            "The keyword argument `name` must be the name of a method of the "
            "decorated class: <class 'Test'>. Got 'nonexistent_method' instead"
        )
        with self.assertRaisesMessage(ValueError, msg):

            @deco_with_args(5)
            class Test:
                @classmethod
                def __module__(cls):
                    return "tests"

    def test_wrapper_assignments(self):
        """method_decorator_with_args preserves wrapper assignments."""
        func_name = None
        func_module = None
        arg_value = None

        def decorator_factory(value):
            def decorator(func):
                @wraps(func)
                def inner(*args, **kwargs):
                    nonlocal func_name, func_module, arg_value
                    func_name = getattr(func, "__name__", None)
                    func_module = getattr(func, "__module__", None)
                    arg_value = value
                    return func(*args, **kwargs)

                return inner

            return decorator

        decorator_with_args = method_decorator_with_args(decorator_factory)

        class Test:
            @decorator_with_args(5)
            def method(self):
                return "tests"

        Test().method()
        self.assertEqual(func_name, "method")
        self.assertIsNotNone(func_module)
        self.assertEqual(arg_value, 5)


def async_simple_dec_factory(prefix_text: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            return f"{prefix_text}: {result}"

        return wrapper

    return decorator


async_simple_dec_m_w_args = method_decorator_with_args(async_simple_dec_factory)


class AsyncMethodDecoratorWithArgsTests(SimpleTestCase):
    """
    Tests for async method_decorator_with_args
    """

    async def test_preserve_signature(self):
        class Test:
            @async_simple_dec_m_w_args("result")
            async def say(self, msg):
                return f"Saying {msg}"

            @async_simple_dec_m_w_args("result again")
            async def say_again(self, msg):
                return f"Saying {msg}"

        self.assertEqual(await Test().say("hello"), "result: Saying hello")
        self.assertEqual(await Test().say_again("hello"), "result again: Saying hello")

    def test_preserve_attributes(self):
        def myattr_dec_factory(value="no value"):
            def myattr_dec(func):
                async def wrapper(*args, **kwargs):
                    return await func(*args, **kwargs)

                wrapper.myattr = True
                wrapper.value1 = value
                return wrapper

            return myattr_dec

        def myattr2_dec_factory(value="no value"):
            def myattr2_dec(func):
                async def wrapper(*args, **kwargs):
                    return await func(*args, **kwargs)

                wrapper.myattr2 = True
                wrapper.value2 = value
                return wrapper

            return myattr2_dec

        # sanity check
        async def func(*args, **kwargs):
            await asyncio.sleep(0.01)
            return args, kwargs

        myattr_dec_w_args = myattr_dec_factory("test1")
        func = myattr_dec_w_args(func)
        self.assertIs(getattr(func, "myattr", False), True)
        self.assertIs(getattr(func, "value1", ""), "test1")

        myattr2_dec_w_args = myattr2_dec_factory("test2")
        func = myattr2_dec_w_args(func)
        self.assertIs(getattr(func, "myattr2", False), True)
        self.assertIs(getattr(func, "value2", ""), "test2")

        func = myattr_dec_w_args(myattr2_dec_w_args(func))
        self.assertIs(getattr(func, "myattr", False), True)
        self.assertIs(getattr(func, "myattr2", False), False)
        self.assertIs(getattr(func, "value2", ""), "")
        self.assertIs(getattr(func, "value1", ""), "test1")

        myattr_dec_w_args_m = method_decorator_with_args(
            myattr_dec_factory, name="method"
        )
        myattr2_dec_w_args_m = method_decorator_with_args(
            myattr2_dec_factory, name="method"
        )

        class TestPlain:
            @myattr_dec_w_args_m("test3")
            @myattr2_dec_w_args_m("test4")
            async def method(self):
                "A method"

        # Decorate using method_decorator() on both the class and the method.
        # The decorators applied to the methods are applied before the ones
        # applied to the class.
        @myattr_dec_w_args_m("test3")
        class TestMethodAndClass:
            @myattr2_dec_w_args_m("test4")
            async def method(self):
                "A method"

        tests = (
            TestPlain,
            TestMethodAndClass,
        )
        for Test in tests:
            with self.subTest(Test=Test):
                self.assertIs(getattr(Test().method, "myattr", False), True)
                self.assertIs(getattr(Test().method, "myattr2", False), True)
                self.assertIs(getattr(Test().method, "value1", ""), "test3")
                self.assertIs(getattr(Test().method, "value2", ""), "test4")
                self.assertIs(getattr(Test.method, "myattr", False), True)
                self.assertIs(getattr(Test.method, "myattr2", False), True)
                self.assertIs(getattr(Test.method, "value1", ""), "test3")
                self.assertIs(getattr(Test.method, "value2", ""), "test4")
                self.assertEqual(Test.method.__doc__, "A method")
                self.assertEqual(Test.method.__name__, "method")

    async def test_new_attribute(self):
        """A decorator factory that sets a new attribute on the method."""

        def decorator_factory(attr_name=None, attr_value=None):
            def decorate(func):
                setattr(func, attr_name, attr_value)
                return func

            return decorate

        decorator_w_args = method_decorator_with_args(decorator_factory)

        class MyClass:
            @decorator_w_args("xy", 20)
            async def method(self):
                return True

        obj = MyClass()
        self.assertEqual(obj.method.xy, 20)
        self.assertIs(await obj.method(), True)

    async def test_argumented(self):

        class ClsDecAsync:
            def __init__(self, myattr):
                self.myattr = myattr

            def __call__(self, f):
                async def wrapper():
                    result = await f()
                    return f"{result} appending {self.myattr}"

                return update_wrapper(wrapper, f)

        decorator_w_args = method_decorator_with_args(ClsDecAsync)

        class Test:
            @decorator_w_args(False)
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
            @async_simple_dec_m_w_args("test_descriptors result")
            @descriptor_wrapper
            async def method(self, arg):
                return arg

        self.assertEqual(await Test().method(1), "test_descriptors result: 1")

    async def test_class_decoration(self):
        """
        @method_decorator_with_args can be used to decorate a class and its methods.
        """

        async_simple_dec_m_w_args_class = method_decorator_with_args(
            async_simple_dec_factory, name="method"
        )

        @async_simple_dec_m_w_args_class("test_class_decoration result")
        class Test:
            async def method(self):
                return False

            async def not_method(self):
                return "a string"

        self.assertEqual(await Test().method(), "test_class_decoration result: False")
        self.assertEqual(await Test().not_method(), "a string")

    async def test_wrapper_assignments(self):
        """@method_decorator_with_args preserves wrapper assignments."""
        func_data = {}

        def decorator_factory(name, value):
            def decorator(func):
                @wraps(func)
                async def inner(*args, **kwargs):
                    func_data["func_name"] = getattr(func, "__name__", None)
                    func_data["func_module"] = getattr(func, "__module__", None)
                    func_data[name] = value
                    return await func(*args, **kwargs)

                return inner

            return decorator

        async_decorator_w_args = method_decorator_with_args(decorator_factory)

        class Test:
            @async_decorator_w_args("test_wrapper_assignments", True)
            async def method(self):
                return "tests"

        await Test().method()
        expected = {
            "func_name": "method",
            "func_module": "decorators.tests",
            "test_wrapper_assignments": True,
        }
        self.assertEqual(func_data, expected)

    async def test_markcoroutinefunction_applied(self):
        class Test:
            @async_simple_dec_m_w_args("coroutine_applied")
            async def method(self):
                return "tests"

        method = Test().method
        self.assertIs(iscoroutinefunction(method), True)
        self.assertEqual(await method(), "coroutine_applied: tests")
