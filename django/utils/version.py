import datetime
import functools
import os
import subprocess
import sys

from django.utils.regex_helper import _lazy_re_compile

# Private, stable API for detecting the Python implementation.
PYPY = sys.implementation.name == "pypy"

# Private, stable API for detecting the Python version. PYXY means "Python X.Y
# or later". So that third-party apps can use these values, each constant
# should remain as long as the oldest supported Django version supports that
# Python version.
PY310 = sys.version_info >= (3, 10)
PY311 = sys.version_info >= (3, 11)
PY312 = sys.version_info >= (3, 12)
PY313 = sys.version_info >= (3, 13)
PY314 = sys.version_info >= (3, 14)
PY315 = sys.version_info >= (3, 15)


def _validate_version(version):
    # A version is the numbers of the printed version, followed by the status
    # and its iteration, so its last three components are always the patch
    # number, the status, and the iteration. Keeping the numbers as printed is
    # what makes django.VERSION >= (2028, 3) mean what it looks like.
    assert len(version) in (4, 5)
    assert version[-2] in ("alpha", "beta", "rc", "final")


class VersionTuple(tuple):
    """django.VERSION, with named access to its components.

    A version is (major, minor, micro, status, iteration) for X.Y[.Z]
    releases, and (year, patch, status, iteration) for the calendar versions
    used from Django 2028, which have no minor component. See DEP 20. The
    `.feature`, `.patch`, `.status`, and `.iteration` attributes answer the
    same under both schemes:

        VERSION.feature   (6, 2) for 6.2.1, and (2028,) for 2028.1
        VERSION.patch     1 for both 6.2.1 and 2028.1
    """

    __slots__ = ()

    def __new__(cls, *version):
        _validate_version(version)
        return super().__new__(cls, version)

    def __getnewargs__(self):
        # The components are passed to __new__() individually, so copying and
        # pickling must unpack them.
        return self._components

    @property
    def _components(self):
        # The components as a plain tuple, without deprecation warnings.
        return tuple.__getitem__(self, slice(None))

    # Indexed from the end, where the two schemes agree.
    @property
    def feature(self):
        return self._components[:-3]

    @property
    def patch(self):
        return tuple.__getitem__(self, -3)

    @property
    def status(self):
        return tuple.__getitem__(self, -2)

    @property
    def iteration(self):
        return tuple.__getitem__(self, -1)

    # RemovedInDjango2028Warning: everything from here to the end of the class
    # only warns about the coming shape change. Remove it all when the
    # deprecation ends. The attributes above stay.
    def _warn(self, message):
        if len(self._components) == 4:
            # Calendar versions already have their final shape.
            return
        # Imported here to avoid a circular import: django.utils.deprecation
        # imports django.utils.inspect, which imports this module.
        from django.utils.deprecation import (
            RemovedInDjango2028Warning,
            warn_about_external_use,
        )

        warn_about_external_use(
            f"{message} django.VERSION has four components from Django 2028, "
            "(year, patch, status, iteration), as calendar versions have no "
            "minor component. Use `.feature`, `.patch`, `.status`, and "
            "`.iteration` attributes instead.",
            RemovedInDjango2028Warning,
            # Report the caller of the tuple operation, not the operation, and
            # stay quiet when Django reads its own version.
            skip_name_prefixes="django.utils.version.VersionTuple",
        )

    def _warn_comparison(self, other):
        # A comparison against three or more components can reach the ones
        # which move down an index, so its result can change from Django 2028.
        if isinstance(other, tuple) and tuple.__len__(other) > 2:
            self._warn(
                "Comparing django.VERSION with three or more components is "
                "deprecated."
            )

    def __getitem__(self, index):
        # Losing the minor component moves every later component down one
        # index: VERSION[2] is the micro version now, but the status from
        # Django 2028. Indexing any of them is therefore deprecated.
        length = tuple.__len__(self)
        if isinstance(index, slice):
            deprecated = any(i >= 2 for i in range(*index.indices(length)))
        else:
            position = index + length if index < 0 else index
            deprecated = 2 <= position < length
        if deprecated:
            self._warn(
                "Indexing django.VERSION from its third component on is deprecated."
            )
        return tuple.__getitem__(self, index)

    def __iter__(self):
        self._warn("Iterating or unpacking django.VERSION is deprecated.")
        return tuple.__iter__(self)

    def __len__(self):
        self._warn("Relying on the length of django.VERSION is deprecated.")
        return tuple.__len__(self)

    def __eq__(self, other):
        self._warn_comparison(other)
        return tuple.__eq__(self, other)

    def __ne__(self, other):
        self._warn_comparison(other)
        return tuple.__ne__(self, other)

    def __lt__(self, other):
        self._warn_comparison(other)
        return tuple.__lt__(self, other)

    def __le__(self, other):
        self._warn_comparison(other)
        return tuple.__le__(self, other)

    def __gt__(self, other):
        self._warn_comparison(other)
        return tuple.__gt__(self, other)

    def __ge__(self, other):
        self._warn_comparison(other)
        return tuple.__ge__(self, other)

    __hash__ = tuple.__hash__


def get_version(version=None):
    """Return a PEP 440-compliant version number from VERSION."""
    version = get_complete_version(version)

    # Now build the two parts of the version number:
    # main = X.Y[.Z] or YYYY[.N]
    # sub = .devN - for pre-alpha releases
    #     | {a|b|rc}N - for alpha, beta, and rc releases

    main = get_main_version(version)
    *_, status, iteration = version

    sub = ""
    if status == "alpha" and iteration == 0:
        git_changeset = get_git_changeset()
        if git_changeset:
            sub = ".dev%s" % git_changeset

    elif status != "final":
        mapping = {"alpha": "a", "beta": "b", "rc": "rc"}
        sub = mapping[status] + str(iteration)

    return main + sub


def get_main_version(version=None):
    """Return main version (X.Y[.Z] or YYYY[.N]) from VERSION."""
    version = get_complete_version(version)
    # The numbers of the printed version, without a zero patch number.
    numbers = version[:-2]
    if numbers[-1] == 0:
        numbers = numbers[:-1]
    return ".".join(str(number) for number in numbers)


def get_complete_version(version=None):
    """
    Return a tuple of the django version. If version argument is non-empty,
    check for correctness of the tuple provided.
    """
    if version is None:
        from django import VERSION as version
    elif not isinstance(version, VersionTuple):
        # VersionTuple validates itself when constructed.
        _validate_version(version)

    return version


def get_docs_version(version=None):
    version = get_complete_version(version)
    if version[-2] != "final":
        return "dev"
    # Documentation is published per feature release.
    return ".".join(str(number) for number in version[:-3])


@functools.lru_cache
def get_git_changeset():
    """Return a numeric identifier of the latest git changeset.

    The result is the UTC timestamp of the changeset in YYYYMMDDHHMMSS format.
    This value isn't guaranteed to be unique, but collisions are very unlikely,
    so it's sufficient for generating the development version numbers.
    """
    # Repository may not be found if __file__ is undefined, e.g. in a frozen
    # module.
    if "__file__" not in globals():
        return None
    repo_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    git_log = subprocess.run(
        "git log --pretty=format:%ct --quiet -1 HEAD",
        capture_output=True,
        shell=True,
        cwd=repo_dir,
        text=True,
    )
    timestamp = git_log.stdout
    tz = datetime.UTC
    try:
        timestamp = datetime.datetime.fromtimestamp(int(timestamp), tz=tz)
    except ValueError:
        return None
    return timestamp.strftime("%Y%m%d%H%M%S")


version_component_re = _lazy_re_compile(r"(\d+|[a-z]+|\.)")


def get_version_tuple(version):
    """
    Return a tuple of version numbers (e.g. (1, 2, 3)) from the version
    string (e.g. '1.2.3').
    """
    version_numbers = []
    for item in version_component_re.split(version):
        if item and item != ".":
            try:
                component = int(item)
            except ValueError:
                break
            else:
                version_numbers.append(component)
    return tuple(version_numbers)
