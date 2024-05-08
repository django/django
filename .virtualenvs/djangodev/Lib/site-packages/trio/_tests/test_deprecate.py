from __future__ import annotations

import inspect
import warnings

import pytest

from .._deprecate import (
    TrioDeprecationWarning,
    deprecated,
    deprecated_alias,
    warn_deprecated,
)
from . import module_with_deprecations


@pytest.fixture
def recwarn_always(recwarn: pytest.WarningsRecorder) -> pytest.WarningsRecorder:
    warnings.simplefilter("always")
    # ResourceWarnings about unclosed sockets can occur nondeterministically
    # (during GC) which throws off the tests in this file
    warnings.simplefilter("ignore", ResourceWarning)
    return recwarn


def _here() -> tuple[str, int]:
    frame = inspect.currentframe()
    assert frame is not None
    assert frame.f_back is not None
    info = inspect.getframeinfo(frame.f_back)
    return (info.filename, info.lineno)


def test_warn_deprecated(recwarn_always: pytest.WarningsRecorder) -> None:
    def deprecated_thing() -> None:
        warn_deprecated("ice", "1.2", issue=1, instead="water")

    deprecated_thing()
    filename, lineno = _here()
    assert len(recwarn_always) == 1
    got = recwarn_always.pop(TrioDeprecationWarning)
    assert isinstance(got.message, Warning)
    assert "ice is deprecated" in got.message.args[0]
    assert "Trio 1.2" in got.message.args[0]
    assert "water instead" in got.message.args[0]
    assert "/issues/1" in got.message.args[0]
    assert got.filename == filename
    assert got.lineno == lineno - 1


def test_warn_deprecated_no_instead_or_issue(
    recwarn_always: pytest.WarningsRecorder,
) -> None:
    # Explicitly no instead or issue
    warn_deprecated("water", "1.3", issue=None, instead=None)
    assert len(recwarn_always) == 1
    got = recwarn_always.pop(TrioDeprecationWarning)
    assert isinstance(got.message, Warning)
    assert "water is deprecated" in got.message.args[0]
    assert "no replacement" in got.message.args[0]
    assert "Trio 1.3" in got.message.args[0]


def test_warn_deprecated_stacklevel(recwarn_always: pytest.WarningsRecorder) -> None:
    def nested1() -> None:
        nested2()

    def nested2() -> None:
        warn_deprecated("x", "1.3", issue=7, instead="y", stacklevel=3)

    filename, lineno = _here()
    nested1()
    got = recwarn_always.pop(TrioDeprecationWarning)
    assert got.filename == filename
    assert got.lineno == lineno + 1


def old() -> None:  # pragma: no cover
    pass


def new() -> None:  # pragma: no cover
    pass


def test_warn_deprecated_formatting(recwarn_always: pytest.WarningsRecorder) -> None:
    warn_deprecated(old, "1.0", issue=1, instead=new)
    got = recwarn_always.pop(TrioDeprecationWarning)
    assert isinstance(got.message, Warning)
    assert "test_deprecate.old is deprecated" in got.message.args[0]
    assert "test_deprecate.new instead" in got.message.args[0]


@deprecated("1.5", issue=123, instead=new)
def deprecated_old() -> int:
    return 3


def test_deprecated_decorator(recwarn_always: pytest.WarningsRecorder) -> None:
    assert deprecated_old() == 3
    got = recwarn_always.pop(TrioDeprecationWarning)
    assert isinstance(got.message, Warning)
    assert "test_deprecate.deprecated_old is deprecated" in got.message.args[0]
    assert "1.5" in got.message.args[0]
    assert "test_deprecate.new" in got.message.args[0]
    assert "issues/123" in got.message.args[0]


class Foo:
    @deprecated("1.0", issue=123, instead="crying")
    def method(self) -> int:
        return 7


def test_deprecated_decorator_method(recwarn_always: pytest.WarningsRecorder) -> None:
    f = Foo()
    assert f.method() == 7
    got = recwarn_always.pop(TrioDeprecationWarning)
    assert isinstance(got.message, Warning)
    assert "test_deprecate.Foo.method is deprecated" in got.message.args[0]


@deprecated("1.2", thing="the thing", issue=None, instead=None)
def deprecated_with_thing() -> int:
    return 72


def test_deprecated_decorator_with_explicit_thing(
    recwarn_always: pytest.WarningsRecorder,
) -> None:
    assert deprecated_with_thing() == 72
    got = recwarn_always.pop(TrioDeprecationWarning)
    assert isinstance(got.message, Warning)
    assert "the thing is deprecated" in got.message.args[0]


def new_hotness() -> str:
    return "new hotness"


old_hotness = deprecated_alias("old_hotness", new_hotness, "1.23", issue=1)


def test_deprecated_alias(recwarn_always: pytest.WarningsRecorder) -> None:
    assert old_hotness() == "new hotness"
    got = recwarn_always.pop(TrioDeprecationWarning)
    assert isinstance(got.message, Warning)
    assert "test_deprecate.old_hotness is deprecated" in got.message.args[0]
    assert "1.23" in got.message.args[0]
    assert "test_deprecate.new_hotness instead" in got.message.args[0]
    assert "issues/1" in got.message.args[0]

    assert isinstance(old_hotness.__doc__, str)
    assert ".. deprecated:: 1.23" in old_hotness.__doc__
    assert "test_deprecate.new_hotness instead" in old_hotness.__doc__
    assert "issues/1>`__" in old_hotness.__doc__


class Alias:
    def new_hotness_method(self) -> str:
        return "new hotness method"

    old_hotness_method = deprecated_alias(
        "Alias.old_hotness_method", new_hotness_method, "3.21", issue=1
    )


def test_deprecated_alias_method(recwarn_always: pytest.WarningsRecorder) -> None:
    obj = Alias()
    assert obj.old_hotness_method() == "new hotness method"
    got = recwarn_always.pop(TrioDeprecationWarning)
    assert isinstance(got.message, Warning)
    msg = got.message.args[0]
    assert "test_deprecate.Alias.old_hotness_method is deprecated" in msg
    assert "test_deprecate.Alias.new_hotness_method instead" in msg


@deprecated("2.1", issue=1, instead="hi")
def docstring_test1() -> None:  # pragma: no cover
    """Hello!"""


@deprecated("2.1", issue=None, instead="hi")
def docstring_test2() -> None:  # pragma: no cover
    """Hello!"""


@deprecated("2.1", issue=1, instead=None)
def docstring_test3() -> None:  # pragma: no cover
    """Hello!"""


@deprecated("2.1", issue=None, instead=None)
def docstring_test4() -> None:  # pragma: no cover
    """Hello!"""


def test_deprecated_docstring_munging() -> None:
    assert (
        docstring_test1.__doc__
        == """Hello!

.. deprecated:: 2.1
   Use hi instead.
   For details, see `issue #1 <https://github.com/python-trio/trio/issues/1>`__.

"""
    )

    assert (
        docstring_test2.__doc__
        == """Hello!

.. deprecated:: 2.1
   Use hi instead.

"""
    )

    assert (
        docstring_test3.__doc__
        == """Hello!

.. deprecated:: 2.1
   For details, see `issue #1 <https://github.com/python-trio/trio/issues/1>`__.

"""
    )

    assert (
        docstring_test4.__doc__
        == """Hello!

.. deprecated:: 2.1

"""
    )


def test_module_with_deprecations(recwarn_always: pytest.WarningsRecorder) -> None:
    assert module_with_deprecations.regular == "hi"
    assert len(recwarn_always) == 0

    filename, lineno = _here()
    assert module_with_deprecations.dep1 == "value1"  # type: ignore[attr-defined]
    got = recwarn_always.pop(TrioDeprecationWarning)
    assert isinstance(got.message, Warning)
    assert got.filename == filename
    assert got.lineno == lineno + 1

    assert "module_with_deprecations.dep1" in got.message.args[0]
    assert "Trio 1.1" in got.message.args[0]
    assert "/issues/1" in got.message.args[0]
    assert "value1 instead" in got.message.args[0]

    assert module_with_deprecations.dep2 == "value2"  # type: ignore[attr-defined]
    got = recwarn_always.pop(TrioDeprecationWarning)
    assert isinstance(got.message, Warning)
    assert "instead-string instead" in got.message.args[0]

    with pytest.raises(AttributeError):
        module_with_deprecations.asdf  # type: ignore[attr-defined]  # noqa: B018  # "useless expression"
