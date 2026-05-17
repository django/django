import inspect
import sys
import warnings
from contextlib import contextmanager

from django.test import SimpleTestCase
from django.utils.deprecation import RemovedInNextVersionWarning

from . import internal


class WarnAboutExternalUseTests(SimpleTestCase):
    @contextmanager
    def assertNotWarns(self, category, **kwargs):
        with warnings.catch_warnings(record=True) as caught_warnings:
            warnings.filterwarnings("always", category=category, **kwargs)
            yield caught_warnings
        self.assertEqual([str(warning) for warning in caught_warnings], [])

    def assertWarningPointsHere(self, warning, *, offset=-1):
        caller_frame = inspect.currentframe().f_back
        self.assertEqual(warning.filename, caller_frame.f_code.co_filename)
        self.assertEqual(warning.lineno, caller_frame.f_lineno + offset)

    def test_external_use_warns(self):
        msg = "This is deprecated."
        with self.assertWarnsMessage(RemovedInNextVersionWarning, msg) as warning:
            internal.deprecated_function(msg, RemovedInNextVersionWarning)
        self.assertWarningPointsHere(warning)

    def test_internal_use_does_not_warn(self):
        with self.assertNotWarns(RemovedInNextVersionWarning):
            internal.one_indirection("This is deprecated.", RemovedInNextVersionWarning)

    def test_external_skip_frames_warns(self):
        with self.assertWarnsMessage(RemovedInNextVersionWarning, "Message") as warning:
            internal.one_indirection(skip_frames=1)
        self.assertWarningPointsHere(warning)

    def test_internal_skip_frames_does_not_warn(self):
        with self.assertNotWarns(RemovedInNextVersionWarning):
            internal.two_indirections(skip_frames=1)

    def test_internal_skip_multiple_frames_does_not_warn(self):
        with self.assertNotWarns(RemovedInNextVersionWarning):
            internal.three_indirections(skip_frames=2)

    def test_external_skip_module_name_warns(self):
        with self.assertWarnsMessage(RemovedInNextVersionWarning, "Message") as warning:
            internal.two_indirections(skip_name_prefixes=internal.__name__)
        self.assertWarningPointsHere(warning)

    def test_internal_skip_module_name_does_not_warn(self):
        # Treat only the current test module as "internal" for this test.
        with self.assertNotWarns(RemovedInNextVersionWarning):
            internal.two_indirections(
                skip_name_prefixes=internal.__name__,
                internal_modules=(__name__,),
            )

    def test_skip_fully_qualified_name(self):
        fqname = f"{internal.__name__}.Class"
        instance = internal.Class()
        for case in ("deprecated_method", "one_indirection", "two_indirections"):
            method = getattr(instance, case)
            with self.subTest(use="external warns", case=case):
                with self.assertWarnsMessage(
                    RemovedInNextVersionWarning, "Message"
                ) as warning:
                    method(skip_name_prefixes=fqname)
                self.assertWarningPointsHere(warning)
            with (
                self.subTest(use="internal does not warn", case=case),
                self.assertNotWarns(RemovedInNextVersionWarning),
            ):
                # Treat only the current test module as "internal".
                method(skip_name_prefixes=fqname, internal_modules=(__name__,))

    def test_skip_name_prefixes_tuple(self):
        prefixes = (
            internal.__name__,
            "django.utils.deprecation.deprecate_posargs",
        )
        with self.assertWarnsMessage(RemovedInNextVersionWarning, "Message") as warning:
            internal.call_decorated(skip_name_prefixes=prefixes)
        self.assertWarningPointsHere(warning)

    def test_skip_name_prefixes_is_applied_before_skip_frames(self):
        with self.assertWarnsMessage(RemovedInNextVersionWarning, "Message") as warning:
            # Stack frames:
            # - deprecated_function()
            # - one_indirection() -- ignored by skip_name_prefixes
            # - two_indirections() -- ignored by skip_frames=1
            # - this test case -- effective caller, is external
            internal.two_indirections(
                skip_name_prefixes=f"{internal.__name__}.one_indirection",
                skip_frames=1,
            )
        self.assertWarningPointsHere(warning, offset=-4)

    def test_skip_name_prefixes_is_not_applied_after_skip_frames(self):
        with self.assertNotWarns(RemovedInNextVersionWarning):
            # Stack frames:
            # - deprecated_function()
            # - (skip_name_prefixes does not match here)
            # - one_indirection() -- ignored by skip_frames=1
            # - two_indirections() -- effective caller, is internal
            internal.two_indirections(
                skip_name_prefixes=f"{internal.__name__}.two_indirections",
                skip_frames=1,
            )

    def test_nested_qualname(self):
        with self.assertWarnsMessage(RemovedInNextVersionWarning, "Message") as warning:
            internal.nested(skip_name_prefixes=f"{internal.__name__}.nested")
        self.assertWarningPointsHere(warning)

    def test_does_not_mistake_third_party_packages_for_django(self):
        # Simulate a "django_goodies" package (which is not part of Django)
        # using a deprecated Django feature.
        sys.modules["django.something"] = internal
        self.addCleanup(sys.modules.pop, "django.something", None)
        code = compile(
            (
                "from django.something import deprecated_function\n"
                "\n"
                "def use_deprecated_function(*args, **kwargs):\n"
                "    deprecated_function(*args, **kwargs)\n"
            ),
            filename="/venv/site-packages/django_goodies/__init__.py",
            mode="exec",
        )
        namespace = {"__name__": "django_goodies"}
        exec(code, namespace)
        with self.assertWarnsMessage(RemovedInNextVersionWarning, "Message") as warning:
            # internal_modules=None forces the default modules.
            namespace["use_deprecated_function"](internal_modules=None)
        self.assertEqual(
            warning.filename, "/venv/site-packages/django_goodies/__init__.py"
        )

    def test_internal_modules_must_be_tuple(self):
        with self.assertRaisesMessage(
            TypeError, "internal_modules must be a tuple of module names"
        ):
            internal.deprecated_function(internal_modules="django")

    def test_warns_if_effective_caller_has_no_filename(self):
        # Simulate a frame whose source location can't be identified by
        # compiling with an empty filename.
        code = compile(
            (
                "def use_deprecated_function(*args, **kwargs):\n"
                "    deprecated_function(*args, **kwargs)\n"
            ),
            filename="",
            mode="exec",
        )
        namespace = {"deprecated_function": internal.deprecated_function}
        exec(code, namespace)
        with self.assertWarnsMessage(RemovedInNextVersionWarning, "Message") as warning:
            namespace["use_deprecated_function"]()
        self.assertEqual(warning.filename, "")
        self.assertEqual(warning.lineno, 2)

    def test_handles_skip_frames_overflow(self):
        too_many_frames = len(inspect.stack()) + 20
        with self.assertWarnsMessage(RemovedInNextVersionWarning, "Message") as warning:
            internal.deprecated_function(skip_frames=too_many_frames)
        # In CPython, warning.filename seems to be "<sys>" and warning.lineno
        # is 0. But the exact values are likely implementation-dependent.
        self.assertNotEqual(warning.filename, __file__)

    def test_handles_skip_name_prefixes_overflow(self):
        with self.assertWarnsMessage(RemovedInNextVersionWarning, "Message") as warning:
            # Every string startswith(""). This will ignore the entire stack.
            internal.deprecated_function(skip_name_prefixes="")
        self.assertNotEqual(warning.filename, __file__)
