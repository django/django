import inspect

from django.test import SimpleTestCase
from django.utils.deprecation import RemovedAfterNextVersionWarning, deprecate_posargs


class DeprecatePosargsTests(SimpleTestCase):
    # Note: these tests use the generic RemovedAfterNextVersionWarning so they
    # don't need to be updated each release. In actual use, you must substitute
    # a specific RemovedInDjangoXXWarning.

    def assertDeprecated(self, params, name):
        msg = (
            "Passing positional argument(s) {0} to {1}() is deprecated. Use keyword "
            "arguments instead."
        )
        return self.assertWarnsMessage(
            RemovedAfterNextVersionWarning, msg.format(params, name)
        )

    def test_all_keyword_only_params(self):
        """All positional arguments are remapped to keyword-only arguments."""

        @deprecate_posargs(RemovedAfterNextVersionWarning, ["a", "b"])
        def some_func(*, a=1, b=2):
            return a, b

        with (
            self.subTest("Multiple affected args"),
            self.assertDeprecated("'a', 'b'", "some_func"),
        ):
            result = some_func(10, 20)
            self.assertEqual(result, (10, 20))

        with (
            self.subTest("One affected arg"),
            self.assertDeprecated("'a'", "some_func"),
        ):
            result = some_func(10)
            self.assertEqual(result, (10, 2))

    def test_some_keyword_only_params(self):
        """Works when keeping some params as positional-or-keyword."""

        @deprecate_posargs(RemovedAfterNextVersionWarning, ["b"])
        def some_func(a, *, b=1):
            return a, b

        with self.assertDeprecated("'b'", "some_func"):
            result = some_func(10, 20)
        self.assertEqual(result, (10, 20))

    def test_no_warning_when_not_needed(self):
        @deprecate_posargs(RemovedAfterNextVersionWarning, ["b"])
        def some_func(a=0, *, b=1):
            return a, b

        with self.subTest("All arguments supplied"), self.assertNoLogs(level="WARNING"):
            result = some_func(10, b=20)
            self.assertEqual(result, (10, 20))

        with self.subTest("All default arguments"), self.assertNoLogs(level="WARNING"):
            result = some_func()
            self.assertEqual(result, (0, 1))

        with (
            self.subTest("Partial arguments supplied"),
            self.assertNoLogs(level="WARNING"),
        ):
            result = some_func(10)
            self.assertEqual(result, (10, 1))

    def test_allows_reordering_keyword_only_params(self):
        """Keyword-only params can be freely added and rearranged."""

        # Original signature: some_func(b=2, a=1), and remappable_names
        # reflects the original positional argument order.
        @deprecate_posargs(RemovedAfterNextVersionWarning, ["b", "a"])
        def some_func(*, aa_new=0, a=1, b=2):
            return aa_new, a, b

        with self.assertDeprecated("'b', 'a'", "some_func"):
            result = some_func(20, 10)
        self.assertEqual(result, (0, 10, 20))

    def test_detects_duplicate_arguments(self):
        @deprecate_posargs(RemovedAfterNextVersionWarning, ["b", "c"])
        def func(a, *, b=1, c=2):
            return a, b, c

        msg = (
            "func() got both deprecated positional and keyword argument values for {0}"
        )
        with (
            self.subTest("One duplicate"),
            self.assertRaisesMessage(TypeError, msg.format("'b'")),
        ):
            func(0, 10, b=12)

        with (
            self.subTest("Multiple duplicates"),
            self.assertRaisesMessage(TypeError, msg.format("'b', 'c'")),
        ):
            func(0, 10, 20, b=12, c=22)

        with (
            self.subTest("No false positives for valid kwargs"),
            # Deprecation warning for 'b', not TypeError for duplicate 'c'.
            self.assertDeprecated("'b'", "func"),
        ):
            result = func(0, 11, c=22)
            self.assertEqual(result, (0, 11, 22))

    def test_detects_extra_positional_arguments(self):
        @deprecate_posargs(RemovedAfterNextVersionWarning, ["b"])
        def func(a, *, b=1):
            return a, b

        with self.assertRaisesMessage(
            TypeError,
            "func() takes at most 2 positional argument(s) (including 1 deprecated) "
            "but 3 were given.",
        ):
            func(10, 20, 30)

    def test_avoids_remapping_to_new_keyword_arguments(self):
        # Only 'b' is moving; 'c' was added later.
        @deprecate_posargs(RemovedAfterNextVersionWarning, ["b"])
        def func(a, *, b=1, c=2):
            return a, b, c

        with self.assertRaisesMessage(
            TypeError,
            "func() takes at most 2 positional argument(s) (including 1 deprecated) "
            "but 3 were given.",
        ):
            func(10, 20, 30)

    def test_variable_kwargs(self):
        """Works with **kwargs."""

        @deprecate_posargs(RemovedAfterNextVersionWarning, ["b"])
        def some_func(a, *, b=1, **kwargs):
            return a, b, kwargs

        with (
            self.subTest("Called with additional kwargs"),
            self.assertDeprecated("'b'", "some_func"),
        ):
            result = some_func(10, 20, c=30)
            self.assertEqual(result, (10, 20, {"c": 30}))

        with (
            self.subTest("Called without additional kwargs"),
            self.assertDeprecated("'b'", "some_func"),
        ):
            result = some_func(10, 20)
            self.assertEqual(result, (10, 20, {}))

        with (
            self.subTest("Called with too many positional arguments"),
            # Similar to test_detects_extra_positional_arguments() above,
            # but verifying logic is not confused by variable **kwargs.
            self.assertRaisesMessage(
                TypeError,
                "some_func() takes at most 2 positional argument(s) (including 1 "
                "deprecated) but 3 were given.",
            ),
        ):
            some_func(10, 20, 30)

        with self.subTest("No warning needed"):
            result = some_func(10, b=20, c=30)
            self.assertEqual(result, (10, 20, {"c": 30}))

    def test_positional_only_params(self):
        @deprecate_posargs(RemovedAfterNextVersionWarning, ["c"])
        def some_func(a, /, b, *, c=3):
            return a, b, c

        with self.assertDeprecated("'c'", "some_func"):
            result = some_func(10, 20, 30)
        self.assertEqual(result, (10, 20, 30))

    def test_class_methods(self):
        """
        Deprecations for class methods should be bound properly and should
        omit the `self` or `cls` argument from the suggested replacement.
        """

        class SomeClass:
            @deprecate_posargs(RemovedAfterNextVersionWarning, ["a", "b"])
            def __init__(self, *, a=0, b=1):
                self.a = a
                self.b = b

            @deprecate_posargs(RemovedAfterNextVersionWarning, ["a", "b"])
            def some_method(self, *, a, b=1):
                return self.a, self.b, a, b

            @staticmethod
            @deprecate_posargs(RemovedAfterNextVersionWarning, ["a", "b"])
            def some_static_method(*, a, b=1):
                return a, b

            @classmethod
            @deprecate_posargs(RemovedAfterNextVersionWarning, ["a", "b"])
            def some_class_method(cls, *, a, b=1):
                return cls.__name__, a, b

        with (
            self.subTest("Constructor"),
            # Warning should use the class name, not `__init__()`.
            self.assertDeprecated("'a', 'b'", "SomeClass"),
        ):
            instance = SomeClass(10, 20)
            self.assertEqual(instance.a, 10)
            self.assertEqual(instance.b, 20)

        with (
            self.subTest("Instance method"),
            self.assertDeprecated("'a', 'b'", "some_method"),
        ):
            result = SomeClass().some_method(10, 20)
            self.assertEqual(result, (0, 1, 10, 20))

        with (
            self.subTest("Static method on instance"),
            self.assertDeprecated("'a', 'b'", "some_static_method"),
        ):
            result = SomeClass().some_static_method(10, 20)
            self.assertEqual(result, (10, 20))

        with (
            self.subTest("Static method on class"),
            self.assertDeprecated("'a', 'b'", "some_static_method"),
        ):
            result = SomeClass.some_static_method(10, 20)
            self.assertEqual(result, (10, 20))

        with (
            self.subTest("Class method on instance"),
            self.assertDeprecated("'a', 'b'", "some_class_method"),
        ):
            result = SomeClass().some_class_method(10, 20)
            self.assertEqual(result, ("SomeClass", 10, 20))

        with (
            self.subTest("Class method on class"),
            self.assertDeprecated("'a', 'b'", "some_class_method"),
        ):
            result = SomeClass.some_class_method(10, 20)
            self.assertEqual(result, ("SomeClass", 10, 20))

    def test_incorrect_classmethod_order(self):
        """Catch classmethod applied in wrong order."""
        with self.assertRaisesMessage(
            TypeError, "Apply @classmethod before @deprecate_posargs."
        ):

            class SomeClass:
                @deprecate_posargs(RemovedAfterNextVersionWarning, ["a"])
                @classmethod
                def some_class_method(cls, *, a):
                    pass

    def test_incorrect_staticmethod_order(self):
        """Catch staticmethod applied in wrong order."""
        with self.assertRaisesMessage(
            TypeError, "Apply @staticmethod before @deprecate_posargs."
        ):

            class SomeClass:
                @deprecate_posargs(RemovedAfterNextVersionWarning, ["a"])
                @staticmethod
                def some_static_method(*, a):
                    pass

    async def test_async(self):
        """A decorated async function is still async."""

        @deprecate_posargs(RemovedAfterNextVersionWarning, ["a", "b"])
        async def some_func(*, a, b=1):
            return a, b

        self.assertTrue(inspect.iscoroutinefunction(some_func.__wrapped__))
        self.assertTrue(inspect.iscoroutinefunction(some_func))

        with (
            self.subTest("With deprecation warning"),
            self.assertDeprecated("'a', 'b'", "some_func"),
        ):
            result = await some_func(10, 20)
            self.assertEqual(result, (10, 20))

        with (
            self.subTest("Without deprecation warning"),
            self.assertNoLogs(level="WARNING"),
        ):
            result = await some_func(a=10, b=20)
            self.assertEqual(result, (10, 20))

    def test_applied_to_lambda(self):
        """
        Please don't try to deprecate lambda args! What does that even mean?!
        (But if it happens, the decorator should do something reasonable.)
        """
        lambda_func = deprecate_posargs(RemovedAfterNextVersionWarning, ["b"])(
            lambda a, *, b=1: (a, b)
        )
        with self.assertDeprecated("'b'", "<lambda>"):
            result = lambda_func(10, 20)
        self.assertEqual(result, (10, 20))

    def test_bare_init(self):
        """Can't replace '__init__' with class name if not in a class."""

        @deprecate_posargs(RemovedAfterNextVersionWarning, ["a"])
        def __init__(*, a):
            pass

        with self.assertDeprecated("'a'", "__init__"):
            __init__(10)

    def test_warning_source_location(self):
        """The warning points to caller, not the decorator implementation."""

        @deprecate_posargs(RemovedAfterNextVersionWarning, "a")
        def some_func(*, a):
            return a

        with self.assertWarns(RemovedAfterNextVersionWarning) as cm:
            some_func(10)
        self.assertEqual(cm.filename, __file__)
        self.assertEqual(cm.lineno, inspect.currentframe().f_lineno - 2)

    def test_decorator_requires_keyword_only_params(self):
        with self.assertRaisesMessage(
            TypeError,
            "@deprecate_posargs() requires at least one keyword-only parameter "
            "(after a `*` entry in the parameters list).",
        ):

            @deprecate_posargs(RemovedAfterNextVersionWarning, ["b"])
            def func(a, b=1):
                return a, b

    def test_decorator_rejects_var_positional_param(self):
        with self.assertRaisesMessage(
            TypeError,
            "@deprecate_posargs() cannot be used with variable positional `*args`.",
        ):

            @deprecate_posargs(RemovedAfterNextVersionWarning, ["b"])
            def func(*args, b=1):
                return args, b

    def test_decorator_does_not_apply_to_class(self):
        with self.assertRaisesMessage(
            TypeError,
            "@deprecate_posargs cannot be applied to a class. (Apply it to the "
            "__init__ method.)",
        ):

            @deprecate_posargs(RemovedAfterNextVersionWarning, ["b"])
            class NotThisClass:
                pass

    def test_decorator_requires_remappable_names_be_keyword_only(self):
        """remappable_names cannot refer to positional-or-keyword params."""
        with self.assertRaisesMessage(
            TypeError,
            "@deprecate_posargs() requires all remappable_names to be keyword-only "
            "parameters.",
        ):

            @deprecate_posargs(RemovedAfterNextVersionWarning, ["a", "b"])
            def func(a, *, b=1):
                return a, b

    def test_decorator_requires_remappable_names_exist(self):
        """remappable_names cannot refer to variable kwargs."""
        with self.assertRaisesMessage(
            TypeError,
            "@deprecate_posargs() requires all remappable_names to be keyword-only "
            "parameters.",
        ):

            @deprecate_posargs(RemovedAfterNextVersionWarning, ["b", "c"])
            def func(a, *, b=1, **kwargs):
                c = kwargs.get("c")
                return a, b, c

    def test_decorator_preserves_signature_and_metadata(self):

        def original(a, b=1, *, c=2):
            """Docstring."""
            return a, b, c

        decorated = deprecate_posargs(RemovedAfterNextVersionWarning, ["c"])(original)
        self.assertEqual(original.__name__, decorated.__name__)
        self.assertEqual(original.__qualname__, decorated.__qualname__)
        self.assertEqual(original.__doc__, decorated.__doc__)
        self.assertEqual(inspect.signature(original), inspect.signature(decorated))
