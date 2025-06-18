import inspect

from django.test import SimpleTestCase
from django.utils.deprecation import RemovedAfterNextVersionWarning, deprecate_posargs


class DeprecatePosargsTests(SimpleTestCase):
    def test_all_keyword_only_params(self):
        @deprecate_posargs(RemovedAfterNextVersionWarning, moved=["a", "b"])
        def some_func(*, a=1, b=2):
            return a, b

        with self.assertWarnsMessage(
            RemovedAfterNextVersionWarning,
            "Use of positional arguments is deprecated."
            " Change to `some_func(a=..., b=...)`.",
        ):
            result = some_func(10, 20)
        self.assertEqual(result, (10, 20))

    def test_some_keyword_only_params(self):
        @deprecate_posargs(RemovedAfterNextVersionWarning, moved=["b"])
        def some_func(a, *, b=1):
            return a, b

        with self.assertWarnsMessage(
            RemovedAfterNextVersionWarning,
            "Use of some positional arguments is deprecated."
            " Change to `some_func(..., b=...)`.",
        ):
            result = some_func(10, 20)
        self.assertEqual(result, (10, 20))

    def test_no_warning_when_not_needed(self):
        @deprecate_posargs(RemovedAfterNextVersionWarning, moved=["b"])
        def some_func(a=0, *, b=1):
            return a, b

        with self.subTest("All arguments supplied"):
            with self.assertNoLogs(level="WARNING"):
                result = some_func(10, b=20)
            self.assertEqual(result, (10, 20))

        with self.subTest("All default arguments"):
            with self.assertNoLogs(level="WARNING"):
                result = some_func()
            self.assertEqual(result, (0, 1))

        with self.subTest("Partial arguments supplied"):
            with self.assertNoLogs(level="WARNING"):
                result = some_func(10)
            self.assertEqual(result, (10, 1))

    def test_change_to_variations(self):
        """The "change to" recommendation reflects how the function is called."""

        @deprecate_posargs(RemovedAfterNextVersionWarning, moved=["a", "b"])
        def some_func(*, a=1, b=2):
            return a, b

        @deprecate_posargs(RemovedAfterNextVersionWarning, moved=["b"])
        def other_func(a=1, *, b=2, c=3):
            return a, b, c

        with self.subTest("Lists arguments requiring change"):
            with self.assertWarnsMessage(
                RemovedAfterNextVersionWarning,
                "Change to `some_func(a=..., b=...)`.",
            ):
                result = some_func(10, 20)
            self.assertEqual(result, (10, 20))

        with self.subTest("Omits unused arguments"):
            with self.assertWarnsMessage(
                RemovedAfterNextVersionWarning,
                "Change to `some_func(a=...)`.",
            ):
                result = some_func(10)
            self.assertEqual(result, (10, 2))

        with self.subTest("Elides trailing arguments not requiring change"):
            with self.assertWarnsMessage(
                RemovedAfterNextVersionWarning,
                "Change to `some_func(a=..., ...)`.",
            ):
                result = some_func(10, b=20)
            self.assertEqual(result, (10, 20))

        with self.subTest("Elides leading arguments not requiring change"):
            with self.assertWarnsMessage(
                RemovedAfterNextVersionWarning,
                "Change to `other_func(..., b=...)`.",
            ):
                result = other_func(10, 20)
            self.assertEqual(result, (10, 20, 3))

        with self.subTest("Elides leading and trailing arguments not requiring change"):
            with self.assertWarnsMessage(
                RemovedAfterNextVersionWarning,
                "Change to `other_func(..., b=..., ...)`.",
            ):
                result = other_func(10, 20, c=30)
            self.assertEqual(result, (10, 20, 30))

    def test_allows_reordering_keyword_only_params(self):
        """
        Because `moved` reflects the original positional argument order,
        keyword-only params can be freely added and rearranged.
        """

        # Original signature: some_func(b=2, a=1)
        @deprecate_posargs(RemovedAfterNextVersionWarning, moved=["b", "a"])
        def some_func(*, aa_new=0, a=1, b=2):
            return aa_new, a, b

        with self.assertWarnsMessage(
            RemovedAfterNextVersionWarning,
            "Change to `some_func(b=..., a=...)`.",
        ):
            result = some_func(20, 10)
        self.assertEqual(result, (0, 10, 20))

    def test_detects_duplicate_arguments(self):
        @deprecate_posargs(RemovedAfterNextVersionWarning, moved=["b", "c"])
        def func(a, *, b=1, c=2):
            return a, b, c

        with self.subTest("One duplicate"):
            with self.assertRaisesMessage(
                TypeError,
                "func() got both deprecated positional"
                " and keyword argument values for 'b'",
            ):
                func(0, 10, b=12)

        with self.subTest("Multiple duplicates"):
            with self.assertRaisesMessage(
                TypeError,
                "func() got both deprecated positional"
                " and keyword argument values for 'b', 'c'",
            ):
                func(0, 10, 20, b=12, c=22)

    def test_detects_extra_positional_arguments(self):
        @deprecate_posargs(RemovedAfterNextVersionWarning, moved=["b"])
        def func(a, *, b=1):
            return a, b

        with self.assertRaisesMessage(
            TypeError,
            "func() takes at most 2 positional argument(s)"
            " (including 1 deprecated) but 3 were given.",
        ):
            func(10, 20, 30)

    def test_avoids_remapping_to_new_keyword_arguments(self):
        # Only 'b' is moving; 'c' was added later.
        @deprecate_posargs(RemovedAfterNextVersionWarning, moved=["b"])
        def func(a, *, b=1, c=2):
            return a, b, c

        with self.assertRaisesMessage(
            TypeError,
            "func() takes at most 2 positional argument(s)"
            " (including 1 deprecated) but 3 were given.",
        ):
            func(10, 20, 30)

    def test_variable_kwargs(self):
        """Works with **kwargs."""

        @deprecate_posargs(RemovedAfterNextVersionWarning, moved=["b"])
        def some_func(a, *, b=1, **kwargs):
            return a, b, kwargs

        with self.subTest("Called with additional kwargs"):
            with self.assertWarnsMessage(
                RemovedAfterNextVersionWarning,
                "Use of some positional arguments is deprecated."
                " Change to `some_func(..., b=..., ...)`.",
            ):
                result = some_func(10, 20, c=30)
            self.assertEqual(result, (10, 20, {"c": 30}))

        with self.subTest("Called without additional kwargs"):
            with self.assertWarnsMessage(
                RemovedAfterNextVersionWarning,
                "Use of some positional arguments is deprecated."
                " Change to `some_func(..., b=...)`.",
            ):
                result = some_func(10, 20)
            self.assertEqual(result, (10, 20, {}))

        with self.subTest("Called with too many positional arguments"):
            # Similar to test_detects_extra_positional_arguments() above,
            # but verifying logic is not confused by variable **kwargs.
            with self.assertRaisesMessage(
                TypeError,
                "some_func() takes at most 2 positional argument(s)"
                " (including 1 deprecated) but 3 were given.",
            ):
                some_func(10, 20, 30)

        with self.subTest("No warning needed"):
            result = some_func(10, b=20, c=30)
            self.assertEqual(result, (10, 20, {"c": 30}))

    def test_positional_only_params(self):
        @deprecate_posargs(RemovedAfterNextVersionWarning, moved=["c"])
        def some_func(a, /, b, *, c=3):
            return a, b, c

        with self.assertWarnsMessage(
            RemovedAfterNextVersionWarning,
            "Use of some positional arguments is deprecated."
            " Change to `some_func(..., c=...)`.",
        ):
            result = some_func(10, 20, 30)
        self.assertEqual(result, (10, 20, 30))

    def test_class_methods(self):
        """
        Deprecations for class methods should be bound properly and should
        omit the `self` or `cls` argument from the suggested replacement.
        """

        class SomeClass:
            @deprecate_posargs(RemovedAfterNextVersionWarning, moved=["a", "b"])
            def __init__(self, *, a=0, b=1):
                self.a = a
                self.b = b

            @deprecate_posargs(RemovedAfterNextVersionWarning, moved=["a", "b"])
            def some_method(self, *, a, b=1):
                return self.a, self.b, a, b

            @staticmethod
            @deprecate_posargs(RemovedAfterNextVersionWarning, moved=["a", "b"])
            def some_static_method(*, a, b=1):
                return a, b

            @classmethod
            @deprecate_posargs(RemovedAfterNextVersionWarning, moved=["a", "b"])
            def some_class_method(cls, *, a, b=1):
                return cls.__name__, a, b

        with self.subTest("Constructor"):
            # Warning should use the class name, not `__init__()`.
            with self.assertWarnsMessage(
                RemovedAfterNextVersionWarning,
                "Use of positional arguments is deprecated."
                " Change to `SomeClass(a=..., b=...)`.",
            ):
                instance = SomeClass(10, 20)
            self.assertEqual(instance.a, 10)
            self.assertEqual(instance.b, 20)

        with self.subTest("Instance method"):
            instance = SomeClass()
            with self.assertWarnsMessage(
                RemovedAfterNextVersionWarning,
                "Use of positional arguments is deprecated."
                " Change to `some_method(a=..., b=...)`.",
            ):
                result = instance.some_method(10, 20)
            self.assertEqual(result, (0, 1, 10, 20))

        with self.subTest("Static method on instance"):
            instance = SomeClass()
            with self.assertWarnsMessage(
                RemovedAfterNextVersionWarning,
                "Use of positional arguments is deprecated."
                " Change to `some_static_method(a=..., b=...)`.",
            ):
                result = instance.some_static_method(10, 20)
            self.assertEqual(result, (10, 20))

        with self.subTest("Static method on class"):
            with self.assertWarnsMessage(
                RemovedAfterNextVersionWarning,
                "Use of positional arguments is deprecated."
                " Change to `some_static_method(a=..., b=...)`.",
            ):
                result = SomeClass.some_static_method(10, 20)
            self.assertEqual(result, (10, 20))

        with self.subTest("Class method on instance"):
            instance = SomeClass()
            with self.assertWarnsMessage(
                RemovedAfterNextVersionWarning,
                "Use of positional arguments is deprecated."
                " Change to `some_class_method(a=..., b=...)`.",
            ):
                result = instance.some_class_method(10, 20)
            self.assertEqual(result, ("SomeClass", 10, 20))

        with self.subTest("Class method on class"):
            with self.assertWarnsMessage(
                RemovedAfterNextVersionWarning,
                "Use of positional arguments is deprecated."
                " Change to `some_class_method(a=..., b=...)`.",
            ):
                result = SomeClass.some_class_method(10, 20)
            self.assertEqual(result, ("SomeClass", 10, 20))

    def test_incorrect_classmethod_order(self):
        """Catch classmethod applied in wrong order."""
        with self.assertRaisesMessage(
            TypeError, "Apply @classmethod before @deprecate_posargs."
        ):

            class SomeClass:
                @deprecate_posargs(RemovedAfterNextVersionWarning, moved=["a"])
                @classmethod
                def some_class_method(cls, *, a):
                    pass

    def test_incorrect_staticmethod_order(self):
        """Catch staticmethod applied in wrong order."""
        with self.assertRaisesMessage(
            TypeError, "Apply @staticmethod before @deprecate_posargs."
        ):

            class SomeClass:
                @deprecate_posargs(RemovedAfterNextVersionWarning, moved=["a"])
                @staticmethod
                def some_static_method(*, a):
                    pass

    async def test_async(self):
        """A decorated async function is still async."""

        @deprecate_posargs(RemovedAfterNextVersionWarning, moved=["a", "b"])
        async def some_func(*, a, b=1):
            return a, b

        self.assertTrue(inspect.iscoroutinefunction(some_func.__wrapped__))
        self.assertTrue(inspect.iscoroutinefunction(some_func))

        with self.subTest("With deprecation warning"):
            with self.assertWarnsMessage(
                RemovedAfterNextVersionWarning,
                "Use of positional arguments is deprecated."
                " Change to `some_func(a=..., b=...)`.",
            ):
                result = await some_func(10, 20)
            self.assertEqual(result, (10, 20))

        with self.subTest("Without deprecation warning"):
            with self.assertNoLogs(level="WARNING"):
                result = await some_func(a=10, b=20)
            self.assertEqual(result, (10, 20))

    def test_applied_to_lambda(self):
        """
        Please don't try to deprecate lambda args! What does that even mean?!
        (But if it happens, the decorator should do something reasonable.)
        """
        lambda_func = deprecate_posargs(RemovedAfterNextVersionWarning, moved=["b"])(
            lambda a, *, b=1: (a, b)
        )
        with self.assertWarnsMessage(
            RemovedAfterNextVersionWarning,
            "Use of some positional arguments is deprecated."
            " Change to `<lambda>(..., b=...)`.",
        ):
            result = lambda_func(10, 20)
        self.assertEqual(result, (10, 20))

    def test_bare_init(self):
        """Can't replace '__init__' with class name if not in a class."""

        @deprecate_posargs(RemovedAfterNextVersionWarning, moved=["a"])
        def __init__(*, a):
            pass

        with self.assertWarnsMessage(
            RemovedAfterNextVersionWarning,
            "Use of positional arguments is deprecated."
            " Change to `__init__(a=...)`.",
        ):
            __init__(10)

    def test_warning_stacklevel(self):
        """The warning points to caller, not the decorator implementation."""

        @deprecate_posargs(RemovedAfterNextVersionWarning, moved="a")
        def some_func(*, a):
            return a

        with self.assertWarns(RemovedAfterNextVersionWarning) as cm:
            some_func(10)
        self.assertEqual(cm.filename, __file__)
        self.assertEqual(cm.lineno, inspect.currentframe().f_lineno - 2)

    def test_decorator_requires_keyword_only_params(self):
        with self.assertRaisesMessage(
            TypeError,
            "@deprecate_posargs() requires at least one keyword-only parameter"
            " (after a `*` entry in the parameters list).",
        ):

            @deprecate_posargs(RemovedAfterNextVersionWarning, moved=["b"])
            def func(a, b=1):
                return a, b

    def test_decorator_rejects_var_positional_param(self):
        with self.assertRaisesMessage(
            TypeError,
            "@deprecate_posargs() cannot be used with variable positional `*args`.",
        ):

            @deprecate_posargs(RemovedAfterNextVersionWarning, moved=["b"])
            def func(*args, b=1):
                return args, b

    def test_decorator_does_not_apply_to_class(self):
        with self.assertRaisesMessage(
            TypeError,
            "@deprecate_posargs cannot be applied to a class."
            " (Apply it to the __init__ method.)",
        ):

            @deprecate_posargs(RemovedAfterNextVersionWarning, moved=["b"])
            class NotThisClass:
                pass

    def test_decorator_requires_moved_be_keyword_only(self):
        with self.assertRaisesMessage(
            TypeError,
            "@deprecate_posargs() `moved` names must all be keyword-only parameters.",
        ):

            @deprecate_posargs(RemovedAfterNextVersionWarning, moved=["a", "b"])
            def func(a, *, b=1):
                return a, b

    def test_decorator_requires_moved_be_named(self):
        with self.assertRaisesMessage(
            TypeError,
            "@deprecate_posargs() `moved` names must all be keyword-only parameters.",
        ):

            @deprecate_posargs(RemovedAfterNextVersionWarning, moved=["b", "c"])
            def func(a, *, b=1, **kwargs):
                return a, b, kwargs

    def test_decorator_preserves_metadata(self):
        """
        The decorated function has the same signature and metadata as the original.
        This may be important for certain coding tools (e.g., IDE autocompletion).
        """

        def original(a, b=1, *, c=2):
            """Docstring."""
            return a, b, c

        decorated = deprecate_posargs(RemovedAfterNextVersionWarning, moved=["c"])(
            original
        )
        self.assertEqual(original.__name__, decorated.__name__)
        self.assertEqual(original.__qualname__, decorated.__qualname__)
        self.assertEqual(original.__doc__, decorated.__doc__)
        self.assertEqual(inspect.signature(original), inspect.signature(decorated))
