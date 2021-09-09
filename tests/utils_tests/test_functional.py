from unittest import mock

from django.test import SimpleTestCase
from django.test.utils import ignore_warnings
from django.utils.deprecation import RemovedInDjango50Warning
from django.utils.functional import (
    cached_property,
    classproperty,
    keep_lazy,
    lazy,
    lazystr,
    Promise,
)


class FunctionalTests(SimpleTestCase):
    def test_lazy(self):
        t = lazy(lambda: tuple(range(3)), list, tuple)
        for a, b in zip(t(), range(3)):
            self.assertEqual(a, b)

    def test_lazy_base_class(self):
        """lazy also finds base class methods in the proxy object"""
        class Base:
            def base_method(self):
                pass

        class Klazz(Base):
            pass

        t = lazy(lambda: Klazz(), Klazz)()
        self.assertIn('base_method', dir(t))

    def test_lazy_base_class_override(self):
        """lazy finds the correct (overridden) method implementation"""
        class Base:
            def method(self):
                return 'Base'

        class Klazz(Base):
            def method(self):
                return 'Klazz'

        t = lazy(lambda: Klazz(), Base)()
        self.assertEqual(t.method(), 'Klazz')

    def test_lazy_object_to_string(self):

        class Klazz:
            def __str__(self):
                return "Î am ā Ǩlâzz."

            def __bytes__(self):
                return b"\xc3\x8e am \xc4\x81 binary \xc7\xa8l\xc3\xa2zz."

        t = lazy(lambda: Klazz(), Klazz)()
        self.assertEqual(str(t), "Î am ā Ǩlâzz.")
        self.assertEqual(bytes(t), b"\xc3\x8e am \xc4\x81 binary \xc7\xa8l\xc3\xa2zz.")

    def assertCachedPropertyWorks(self, attr, Class):
        with self.subTest(attr=attr):
            def get(source):
                return getattr(source, attr)

            obj = Class()

            class SubClass(Class):
                pass

            subobj = SubClass()
            # Docstring is preserved.
            self.assertEqual(get(Class).__doc__, 'Here is the docstring...')
            self.assertEqual(get(SubClass).__doc__, 'Here is the docstring...')
            # It's cached.
            self.assertEqual(get(obj), get(obj))
            self.assertEqual(get(subobj), get(subobj))
            # The correct value is returned.
            self.assertEqual(get(obj)[0], 1)
            self.assertEqual(get(subobj)[0], 1)
            # State isn't shared between instances.
            obj2 = Class()
            subobj2 = SubClass()
            self.assertNotEqual(get(obj), get(obj2))
            self.assertNotEqual(get(subobj), get(subobj2))
            # It behaves like a property when there's no instance.
            self.assertIsInstance(get(Class), cached_property)
            self.assertIsInstance(get(SubClass), cached_property)
            # 'other_value' doesn't become a property.
            self.assertTrue(callable(obj.other_value))
            self.assertTrue(callable(subobj.other_value))

    def test_cached_property(self):
        """cached_property caches its value and behaves like a property."""
        class Class:
            @cached_property
            def value(self):
                """Here is the docstring..."""
                return 1, object()

            @cached_property
            def __foo__(self):
                """Here is the docstring..."""
                return 1, object()

            def other_value(self):
                """Here is the docstring..."""
                return 1, object()

            other = cached_property(other_value)

        attrs = ['value', 'other', '__foo__']
        for attr in attrs:
            self.assertCachedPropertyWorks(attr, Class)

    @ignore_warnings(category=RemovedInDjango50Warning)
    def test_cached_property_name(self):
        class Class:
            def other_value(self):
                """Here is the docstring..."""
                return 1, object()

            other = cached_property(other_value, name='other')
            other2 = cached_property(other_value, name='different_name')

        self.assertCachedPropertyWorks('other', Class)
        # An explicit name is ignored.
        obj = Class()
        obj.other2
        self.assertFalse(hasattr(obj, 'different_name'))

    def test_cached_property_name_deprecation_warning(self):
        def value(self):
            return 1

        msg = "The name argument is deprecated as it's unnecessary as of Python 3.6."
        with self.assertWarnsMessage(RemovedInDjango50Warning, msg):
            cached_property(value, name='other_name')

    def test_cached_property_auto_name(self):
        """
        cached_property caches its value and behaves like a property
        on mangled methods or when the name kwarg isn't set.
        """
        class Class:
            @cached_property
            def __value(self):
                """Here is the docstring..."""
                return 1, object()

            def other_value(self):
                """Here is the docstring..."""
                return 1, object()

            other = cached_property(other_value)

        attrs = ['_Class__value', 'other']
        for attr in attrs:
            self.assertCachedPropertyWorks(attr, Class)

    def test_cached_property_reuse_different_names(self):
        """Disallow this case because the decorated function wouldn't be cached."""
        with self.assertRaises(RuntimeError) as ctx:
            class ReusedCachedProperty:
                @cached_property
                def a(self):
                    pass

                b = a

        self.assertEqual(
            str(ctx.exception.__context__),
            str(TypeError(
                "Cannot assign the same cached_property to two different "
                "names ('a' and 'b')."
            ))
        )

    def test_cached_property_reuse_same_name(self):
        """
        Reusing a cached_property on different classes under the same name is
        allowed.
        """
        counter = 0

        @cached_property
        def _cp(_self):
            nonlocal counter
            counter += 1
            return counter

        class A:
            cp = _cp

        class B:
            cp = _cp

        a = A()
        b = B()
        self.assertEqual(a.cp, 1)
        self.assertEqual(b.cp, 2)
        self.assertEqual(a.cp, 1)

    def test_cached_property_set_name_not_called(self):
        cp = cached_property(lambda s: None)

        class Foo:
            pass

        Foo.cp = cp
        msg = 'Cannot use cached_property instance without calling __set_name__() on it.'
        with self.assertRaisesMessage(TypeError, msg):
            Foo().cp

    def test_lazy_add(self):
        lazy_4 = lazy(lambda: 4, int)
        lazy_5 = lazy(lambda: 5, int)
        self.assertEqual(lazy_4() + lazy_5(), 9)

    def test_lazy_equality(self):
        """
        == and != work correctly for Promises.
        """
        lazy_a = lazy(lambda: 4, int)
        lazy_b = lazy(lambda: 4, int)
        lazy_c = lazy(lambda: 5, int)

        self.assertEqual(lazy_a(), lazy_b())
        self.assertNotEqual(lazy_b(), lazy_c())

    def test_lazy_repr_text(self):
        original_object = 'Lazy translation text'
        lazy_obj = lazy(lambda: original_object, str)
        self.assertEqual(repr(original_object), repr(lazy_obj()))

    def test_lazy_repr_int(self):
        original_object = 15
        lazy_obj = lazy(lambda: original_object, int)
        self.assertEqual(repr(original_object), repr(lazy_obj()))

    def test_lazy_repr_bytes(self):
        original_object = b'J\xc3\xbcst a str\xc3\xadng'
        lazy_obj = lazy(lambda: original_object, bytes)
        self.assertEqual(repr(original_object), repr(lazy_obj()))

    def test_lazy_class_preparation_caching(self):
        # lazy() should prepare the proxy class only once i.e. the first time
        # it's used.
        lazified = lazy(lambda: 0, int)
        __proxy__ = lazified().__class__
        with mock.patch.object(__proxy__, '__prepare_class__') as mocked:
            lazified()
            mocked.assert_not_called()

    def test_lazy_bytes_and_str_result_classes(self):
        lazy_obj = lazy(lambda: 'test', str, bytes)
        msg = 'Cannot call lazy() with both bytes and text return types.'
        with self.assertRaisesMessage(ValueError, msg):
            lazy_obj()

    def test_classproperty_getter(self):
        class Foo:
            foo_attr = 123

            def __init__(self):
                self.foo_attr = 456

            @classproperty
            def foo(cls):
                return cls.foo_attr

        class Bar:
            bar = classproperty()

            @bar.getter
            def bar(cls):
                return 123

        self.assertEqual(Foo.foo, 123)
        self.assertEqual(Foo().foo, 123)
        self.assertEqual(Bar.bar, 123)
        self.assertEqual(Bar().bar, 123)

    def test_classproperty_override_getter(self):
        class Foo:
            @classproperty
            def foo(cls):
                return 123

            @foo.getter
            def foo(cls):
                return 456

        self.assertEqual(Foo.foo, 456)
        self.assertEqual(Foo().foo, 456)


class KeepLazyExamples:
    def setUp(self):
        super().setUp()

        @keep_lazy(str)
        def keep_lazy_single_argument(value):
            return "single"

        @keep_lazy(str)
        def keep_lazy_multiple_arguments(val1, val2, val3):
            return "multiple"

        @keep_lazy(str)
        def keep_lazy_posargs(*args):
            return "posargs"

        @keep_lazy(str)
        def keep_lazy_kwargs(**kwargs):
            return "kwargs"

        @keep_lazy(str)
        def keep_lazy_multiple_arguments_with_kwonly(arg, *, other):
            return "kwonly"

        @keep_lazy(str)
        def keep_lazy_multiple_arguments_with_poskwargs(arg, /, other, another):
            return "poskwargs"

        self.keep_lazy_single_argument = keep_lazy_single_argument
        self.keep_lazy_multiple_arguments = keep_lazy_multiple_arguments
        self.keep_lazy_posargs = keep_lazy_posargs
        self.keep_lazy_kwargs = keep_lazy_kwargs
        self.keep_lazy_multiple_arguments_with_kwonly = (
            keep_lazy_multiple_arguments_with_kwonly
        )
        self.keep_lazy_multiple_arguments_with_poskwargs = (
            keep_lazy_multiple_arguments_with_poskwargs
        )


class KeepLazyExceptionTests(KeepLazyExamples, SimpleTestCase):
    """
    Wrapping a function with keep_lazy should not cause alterations to the
    exceptions raised when invalid parameters are given.

    keep_lazy generates multiple functions based on the number of arguments
    the underlying function being wrapped expects. At function-wrapping time
    we can't specify the argument names etc, so they're pushed down by passing
    along all *args and **kwargs, expecting the standard python exceptions
    to occur.
    """

    def test_keep_lazy_single_invalid_missing_arguments(self):
        with self.assertRaisesMessage(
            TypeError, "missing 1 required positional argument: 'value'"
        ):
            self.keep_lazy_single_argument()

    def test_keep_lazy_single_invalid_keyword_argument(self):
        with self.assertRaisesMessage(
            TypeError, "got an unexpected keyword argument 'val'"
        ):
            self.keep_lazy_single_argument(val="test")

    def test_keep_lazy_single_argument_given_multiple_positional_arguments(self):
        with self.assertRaisesMessage(
            TypeError, "takes 1 positional argument but 2 were given"
        ):
            self.keep_lazy_single_argument("test", "testing")

    def test_keep_lazy_single_argument_given_multiple_mixed_arguments(self):
        with self.assertRaisesMessage(
            TypeError, "got an unexpected keyword argument 'val'"
        ):
            self.keep_lazy_single_argument("test", val="testing")

    def test_keep_lazy_single_argument_given_multiple_keyword_arguments(self):
        with self.assertRaisesMessage(
            TypeError, "got an unexpected keyword argument 'val'"
        ):
            self.keep_lazy_single_argument(value="test", val="testing")

    def test_keep_lazy_multiple_invalid_missing_arguments(self):
        with self.assertRaisesMessage(
            TypeError,
            "missing 3 required positional arguments: 'val1', 'val2', and 'val3'",
        ):
            self.keep_lazy_multiple_arguments()

    def test_keep_lazy_multiple_invalid_keyword_argument(self):
        with self.assertRaisesMessage(
            TypeError, "got an unexpected keyword argument 'val'"
        ):
            self.keep_lazy_multiple_arguments(val="test")

    def test_keep_lazy_multiple_given_too_few_positional_arguments(self):
        with self.assertRaisesMessage(
            TypeError, "missing 1 required positional argument: 'val3'"
        ):
            self.keep_lazy_multiple_arguments("test", "testing")

    def test_keep_lazy_multiple_given_too_few_keyword_arguments(self):
        with self.assertRaisesMessage(
            TypeError, "missing 1 required positional argument: 'val3'"
        ):
            self.keep_lazy_multiple_arguments(val1="test", val2="testing")

    def test_keep_lazy_multiple_given_too_many_positional_arguments(self):
        with self.assertRaisesMessage(
            TypeError, "takes 3 positional arguments but 4 were given"
        ):
            self.keep_lazy_multiple_arguments("test1", "test2", "test3", "test4")

    def test_keep_lazy_multiple_given_too_many_keyword_arguments(self):
        with self.assertRaisesMessage(
            TypeError, "got an unexpected keyword argument 'val4'"
        ):
            self.keep_lazy_multiple_arguments(
                val1="test1", val2="test2", val3="test3", val4="test4"
            )

    def test_keep_lazy_multiple_posarg_given_as_kwarg(self):
        with self.assertRaisesMessage(
            TypeError,
            "got some positional-only arguments passed as keyword arguments: 'arg'",
        ):
            self.keep_lazy_multiple_arguments_with_poskwargs(arg=1, other=2, another=3)

    def test_keep_lazy_kwonly_missing(self):
        with self.assertRaisesMessage(
            TypeError, "missing 1 required keyword-only argument: 'other'"
        ):
            self.keep_lazy_multiple_arguments_with_kwonly(arg=1)


class KeepLazyMultipleDispatchTests(KeepLazyExamples, SimpleTestCase):
    def test_keep_lazy_returns_expected_value(self):
        self.assertEqual(self.keep_lazy_single_argument(lazystr("s")), "single")
        self.assertEqual(
            self.keep_lazy_single_argument.__code__.co_name,
            "keep_lazy_single_argument_wrapper",
        )

    def test_keep_lazy_single_positional_argument(self):
        s = lazystr("s")
        self.assertIsInstance(self.keep_lazy_single_argument(s), Promise)
        self.assertEqual(self.keep_lazy_single_argument(s), "single")
        self.assertEqual(
            self.keep_lazy_single_argument.__code__.co_name,
            "keep_lazy_single_argument_wrapper",
        )

    def test_keep_lazy_single_keyword_argument(self):
        s = lazystr("s")
        self.assertIsInstance(self.keep_lazy_single_argument(value=s), Promise)
        self.assertEqual(self.keep_lazy_single_argument(value=s), "single")
        self.assertEqual(
            self.keep_lazy_single_argument.__code__.co_name,
            "keep_lazy_single_argument_wrapper",
        )

    def test_keep_lazy_multiple_positional_arguments(self):
        s = lazystr("s")
        self.assertIsInstance(self.keep_lazy_multiple_arguments(1, 2, s), Promise)
        self.assertEqual(self.keep_lazy_multiple_arguments(1, 2, s), "multiple")
        self.assertEqual(
            self.keep_lazy_multiple_arguments.__code__.co_name,
            "keep_lazy_multiple_argument_wrapper",
        )

    def test_keep_lazy_multiple_keyword_arguments(self):
        s = lazystr("s")
        self.assertIsInstance(
            self.keep_lazy_multiple_arguments(val1=1, val2=2, val3=s), Promise
        )
        self.assertEqual(
            self.keep_lazy_multiple_arguments(val1=1, val2=2, val3=s), "multiple"
        )
        self.assertEqual(
            self.keep_lazy_multiple_arguments.__code__.co_name,
            "keep_lazy_multiple_argument_wrapper",
        )

    def test_posargs(self):
        """
        A function which accepts *args must be dispatched to the multiple argument wrapper
        """
        many = lazystr("s")
        self.assertIsInstance(
            self.keep_lazy_posargs("this", "may", "take", many, "arguments"), Promise
        )
        self.assertEqual(
            self.keep_lazy_posargs("this", "may", "take", many, "arguments"), "posargs"
        )
        self.assertEqual(
            self.keep_lazy_posargs.__code__.co_name,
            "keep_lazy_multiple_argument_wrapper",
        )

    def test_kwargs(self):
        """
        A function which accepts **kwargs must be dispatched to the multiple argument wrapper
        """
        many = lazystr("s")
        self.assertIsInstance(
            self.keep_lazy_kwargs(this="may", take=many, arguments="too"), Promise
        )
        self.assertEqual(
            self.keep_lazy_kwargs(this="may", take=many, arguments="too"), "kwargs"
        )
        self.assertEqual(
            self.keep_lazy_kwargs.__code__.co_name,
            "keep_lazy_multiple_argument_wrapper",
        )

    def test_kwonly(self):
        s = lazystr("s")
        self.keep_lazy_multiple_arguments_with_kwonly(1, other=s)
        self.assertIsInstance(
            self.keep_lazy_multiple_arguments_with_kwonly(1, other=s), Promise
        )
        self.assertEqual(
            self.keep_lazy_multiple_arguments_with_kwonly(1, other=s), "kwonly"
        )
        self.assertEqual(
            self.keep_lazy_multiple_arguments_with_kwonly.__code__.co_name,
            "keep_lazy_multiple_argument_wrapper",
        )

    def test_single_complex(self):
        """
        A function which accepts arguments plus *args or **kwargs must be
        dispatched to the multiple argument wrapper
        """
        s = lazystr("s")
        self.assertIsInstance(
            self.keep_lazy_multiple_arguments_with_poskwargs(1, other=s, another=2),
            Promise,
        )
        self.assertEqual(
            self.keep_lazy_multiple_arguments_with_poskwargs(1, other=s, another=2),
            "poskwargs",
        )
        self.assertEqual(
            self.keep_lazy_multiple_arguments_with_poskwargs.__code__.co_name,
            "keep_lazy_multiple_argument_wrapper",
        )
