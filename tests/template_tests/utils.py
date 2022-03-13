import functools
import os

from django.template.engine import Engine
from django.test.utils import override_settings
from django.utils.safestring import mark_safe

ROOT = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(ROOT, "templates")


def setup(templates, *args, test_once=False):
    """
    Runs test method multiple times in the following order:

    debug       cached      string_if_invalid
    -----       ------      -----------------
    False       False
    False       True
    False       False       INVALID
    False       True        INVALID
    True        False
    True        True

    Use test_once=True to test deprecation warnings since the message won't be
    displayed multiple times.
    """

    for arg in args:
        templates.update(arg)

    # numerous tests make use of an inclusion tag
    # add this in here for simplicity
    templates["inclusion.html"] = "{{ result }}"

    loaders = [
        (
            "django.template.loaders.cached.Loader",
            [
                ("django.template.loaders.locmem.Loader", templates),
            ],
        ),
    ]

    def decorator(func):
        # Make Engine.get_default() raise an exception to ensure that tests
        # are properly isolated from Django's global settings.
        @override_settings(TEMPLATES=None)
        @functools.wraps(func)
        def inner(self):
            # Set up custom template tag libraries if specified
            libraries = getattr(self, "libraries", {})

            self.engine = Engine(
                libraries=libraries,
                loaders=loaders,
            )
            func(self)
            if test_once:
                return
            func(self)

            self.engine = Engine(
                libraries=libraries,
                loaders=loaders,
                string_if_invalid="INVALID",
            )
            func(self)
            func(self)

            self.engine = Engine(
                debug=True,
                libraries=libraries,
                loaders=loaders,
            )
            func(self)
            func(self)

        return inner

    return decorator


# Helper objects


class SomeException(Exception):
    silent_variable_failure = True


class SomeOtherException(Exception):
    pass


class ShouldNotExecuteException(Exception):
    pass


class SomeClass:
    def __init__(self):
        self.otherclass = OtherClass()

    def method(self):
        return "SomeClass.method"

    def method2(self, o):
        return o

    def method3(self):
        raise SomeException

    def method4(self):
        raise SomeOtherException

    def method5(self):
        raise TypeError

    def __getitem__(self, key):
        if key == "silent_fail_key":
            raise SomeException
        elif key == "noisy_fail_key":
            raise SomeOtherException
        raise KeyError

    @property
    def silent_fail_attribute(self):
        raise SomeException

    @property
    def noisy_fail_attribute(self):
        raise SomeOtherException

    @property
    def attribute_error_attribute(self):
        raise AttributeError

    @property
    def type_error_attribute(self):
        raise TypeError


class OtherClass:
    def method(self):
        return "OtherClass.method"


class TestObj:
    def is_true(self):
        return True

    def is_false(self):
        return False

    def is_bad(self):
        raise ShouldNotExecuteException()


class SilentGetItemClass:
    def __getitem__(self, key):
        raise SomeException


class SilentAttrClass:
    def b(self):
        raise SomeException

    b = property(b)


class UTF8Class:
    "Class whose __str__ returns non-ASCII data"

    def __str__(self):
        return "ŠĐĆŽćžšđ"


# These two classes are used to test auto-escaping of string output.
class UnsafeClass:
    def __str__(self):
        return "you & me"


class SafeClass:
    def __str__(self):
        return mark_safe("you &gt; me")
