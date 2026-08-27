import inspect
import sys
import warnings
from contextlib import contextmanager

from django.test import SimpleTestCase
from django.utils.deprecation import warn_about_implementation
from django.views.decorators import csrf


class WarnAboutImplementationTests(SimpleTestCase):
    @contextmanager
    def assertWarnsAboutLine(self, category, message, *, offset):
        caller_frame = inspect.currentframe().f_back.f_back
        with self.assertWarnsMessage(category, message) as warning:
            yield
        self.assertEqual(warning.filename, caller_frame.f_code.co_filename)
        self.assertEqual(warning.lineno, caller_frame.f_lineno + offset)

    def test_function(self):
        def some_function():
            pass

        with self.assertWarnsAboutLine(Warning, "deprecated", offset=-3):
            warn_about_implementation("deprecated", Warning, some_function)

    def test_class(self):
        class SomeClass:
            pass

        with self.assertWarnsAboutLine(Warning, "deprecated", offset=-3):
            warn_about_implementation("deprecated", Warning, SomeClass)

    def test_class_init(self):
        class SomeClass:
            def __init__(self):
                pass

        with self.assertWarnsAboutLine(Warning, "deprecated", offset=-3):
            warn_about_implementation("deprecated", Warning, SomeClass.__init__)

    def test_method(self):
        class SomeClass:
            def some_method(self):
                pass

        for case, target in [
            ("unbound", SomeClass.some_method),
            ("bound", SomeClass().some_method),
        ]:
            with (
                self.subTest(case),
                self.assertWarnsAboutLine(Warning, "deprecated", offset=-9),
            ):
                warn_about_implementation("deprecated", Warning, target)

    def test_subclass_method(self):
        class BaseClass:
            def some_method(self):
                pass

            def issue_warning(self):
                warn_about_implementation("deprecated", Warning, self.some_method)

        class SubClass(BaseClass):
            def some_method(self):
                pass

        with self.assertWarnsAboutLine(Warning, "deprecated", offset=-3):
            SubClass().issue_warning()

    def test_my_own_method(self):
        with self.assertWarnsAboutLine(Warning, "deprecated", offset=-1):
            warn_about_implementation("deprecated", Warning, self.test_my_own_method)

    def test_classmethod(self):
        class SomeClass:
            @classmethod
            def some_classmethod(cls):
                pass

        for case, target in [
            ("unbound", SomeClass.some_classmethod),
            ("bound", SomeClass().some_classmethod),
        ]:
            with (
                self.subTest(case),
                self.assertWarnsAboutLine(Warning, "deprecated", offset=-10),
            ):
                warn_about_implementation("deprecated", Warning, target)

    def test_staticmethod(self):
        class SomeClass:
            @staticmethod
            def some_staticmethod():
                pass

        with self.assertWarnsAboutLine(Warning, "deprecated", offset=-4):
            warn_about_implementation(
                "deprecated", Warning, SomeClass.some_staticmethod
            )

    def test_property(self):
        class SomeClass:
            @property
            def some_property(self):
                return None

        with self.assertWarnsAboutLine(Warning, "deprecated", offset=-4):
            warn_about_implementation(
                "deprecated",
                Warning,
                inspect.getattr_static(SomeClass(), "some_property"),
            )

    def test_decorated_function(self):
        @csrf.csrf_exempt
        @csrf.ensure_csrf_cookie
        def some_view(request):
            pass

        with self.assertWarnsAboutLine(Warning, "deprecated", offset=-5):
            warn_about_implementation("deprecated", Warning, some_view)

    def test_decorated_method(self):
        class SomeClass:
            @csrf.csrf_exempt
            @csrf.ensure_csrf_cookie
            def some_method(self):
                pass

        for case, target in [
            ("unbound", SomeClass.some_method),
            ("bound", SomeClass().some_method),
        ]:
            with (
                self.subTest(case),
                self.assertWarnsAboutLine(Warning, "deprecated", offset=-11),
            ):
                warn_about_implementation("deprecated", Warning, target)

    def test_decorated_staticmethod(self):
        class SomeClass:
            @staticmethod
            @csrf.csrf_exempt
            @csrf.ensure_csrf_cookie
            def some_staticmethod():
                pass

        with self.assertWarnsAboutLine(Warning, "deprecated", offset=-6):
            warn_about_implementation(
                "deprecated", Warning, SomeClass.some_staticmethod
            )

    def test_no_source_file(self):
        # When the source file can't be determined, falls back to warning about
        # the caller. (Builtins like `dict` have no source file.)
        with self.assertWarnsAboutLine(Warning, "deprecated", offset=1):
            warn_about_implementation("deprecated", Warning, dict)

    def test_rejects_invalid_target(self):
        msg = (
            "target must be a function, class, bound method, or unbound descriptor "
            "(classmethod, staticmethod, or property)."
        )
        for invalid in ["string", object(), 123, None]:
            with self.subTest(target=invalid), self.assertRaisesMessage(TypeError, msg):
                warn_about_implementation("deprecated", Warning, invalid)

    def test_respects_warning_registry(self):
        def some_function():
            pass

        # The "default" action only works correctly when warn_explicit() is
        # called with the correct module and warning registry. (This test must
        # use "default" or "module", not "once". CPython has an undocumented
        # optimization for "once" that uses a global registry.)
        with warnings.catch_warnings(record=True, action="default") as captured:
            warn_about_implementation("deprecated", Warning, some_function)
            self.assertEqual(len(captured), 1)

            captured.clear()
            warn_about_implementation("deprecated", Warning, some_function)
            self.assertEqual(len(captured), 0)

    def test_creates_warning_registry_if_needed(self):
        def some_function():
            pass

        module = sys.modules[some_function.__module__]
        if hasattr(module, "__warningregistry__"):
            old_registry = module.__warningregistry__
            del module.__warningregistry__
        else:
            old_registry = None

        try:
            with warnings.catch_warnings(record=True, action="default") as captured:
                warn_about_implementation("deprecated", Warning, some_function)
                warn_about_implementation("deprecated", Warning, some_function)

            self.assertEqual(len(captured), 1)
            self.assertIsInstance(module.__warningregistry__, dict)
            self.assertNotEqual(module.__warningregistry__, {})
        finally:
            if old_registry is not None:
                module.__warningregistry__ = old_registry
            elif hasattr(module, "__warningregistry__"):
                del module.__warningregistry__

    def test_missing_module(self):
        def some_function():
            pass

        some_function.__module__ = "not_a_module"

        with self.assertWarnsAboutLine(Warning, "deprecated", offset=-5):
            warn_about_implementation("deprecated", Warning, some_function)

    def test_non_standard_module(self):
        sys.modules["sealed_module"] = type("SealedModule", (), {"__slots__": ()})()
        self.addCleanup(sys.modules.pop, "sealed_module")

        def some_function():
            pass

        some_function.__module__ = "sealed_module"

        with self.assertWarnsAboutLine(Warning, "deprecated", offset=2):
            # Module is not inspectable, so the warning is issued generically.
            warn_about_implementation("deprecated", Warning, some_function)
