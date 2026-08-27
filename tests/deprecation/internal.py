# Simulated Django "internals" for WarnAboutExternalUseTests.
#
# Every function in this module ends up calling deprecated_function(), which
# calls warn_about_external_use(). The other functions provide various stack
# depths and qualnames for test purposes. All functions pass their arguments
# through to warn_about_external_use().
#
# The tests set internal_modules to treat this module (only) as the "internal"
# Django code. Pass internal_modules=None for the original default behavior or
# internal_modules=tuple(...) to make some other modules "internal."

from django.utils.deprecation import (
    RemovedAfterNextVersionWarning,
    RemovedInNextVersionWarning,
    deprecate_posargs,
    warn_about_external_use,
)


def deprecated_function(message=None, category=None, **kwargs):
    kwargs.setdefault("internal_modules", (__name__,))
    warn_about_external_use(
        message or "Message",
        category or RemovedInNextVersionWarning,
        **kwargs,
    )


def one_indirection(*args, **kwargs):
    deprecated_function(*args, **kwargs)


def two_indirections(*args, **kwargs):
    one_indirection(*args, **kwargs)


def three_indirections(*args, **kwargs):
    two_indirections(*args, **kwargs)


class Class:
    def deprecated_method(self, *args, **kwargs):
        deprecated_function(*args, **kwargs)

    def one_indirection(self, *args, **kwargs):
        self.deprecated_method(*args, **kwargs)

    def two_indirections(self, *args, **kwargs):
        self.one_indirection(*args, **kwargs)


@deprecate_posargs(RemovedAfterNextVersionWarning, ["a"])
def decorated(message=None, category=None, *, a=None, **kwargs):
    deprecated_function(message, category, **kwargs)


def call_decorated(*args, **kwargs):
    decorated(*args, **kwargs)


def nested(*args, **kwargs):
    # inner.__qualname__ is something like "nested.<locals>.inner".
    def inner(*args, **kwargs):
        deprecated_function(*args, **kwargs)

    inner(*args, **kwargs)
