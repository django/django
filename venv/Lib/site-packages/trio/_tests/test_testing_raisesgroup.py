from __future__ import annotations

import re
import sys
from types import TracebackType

import pytest

import trio
from trio.testing import _Matcher as Matcher, _RaisesGroup as RaisesGroup
from trio.testing._raises_group import repr_callable

if sys.version_info < (3, 11):
    from exceptiongroup import BaseExceptionGroup, ExceptionGroup


def wrap_escape(s: str) -> str:
    return "^" + re.escape(s) + "$"


def fails_raises_group(
    msg: str, add_prefix: bool = True
) -> pytest.RaisesExc[AssertionError]:
    assert (
        msg[-1] != "\n"
    ), "developer error, expected string should not end with newline"
    prefix = "Raised exception group did not match: " if add_prefix else ""
    return pytest.raises(AssertionError, match=wrap_escape(prefix + msg))


def test_raises_group() -> None:
    with pytest.raises(
        ValueError,
        match=wrap_escape(
            f'Invalid argument "{TypeError()!r}" must be exception type, Matcher, or RaisesGroup.',
        ),
    ):
        RaisesGroup(TypeError())  # type: ignore[call-overload]
    with RaisesGroup(ValueError):
        raise ExceptionGroup("foo", (ValueError(),))

    with (
        fails_raises_group("'SyntaxError' is not of type 'ValueError'"),
        RaisesGroup(ValueError),
    ):
        raise ExceptionGroup("foo", (SyntaxError(),))

    # multiple exceptions
    with RaisesGroup(ValueError, SyntaxError):
        raise ExceptionGroup("foo", (ValueError(), SyntaxError()))

    # order doesn't matter
    with RaisesGroup(SyntaxError, ValueError):
        raise ExceptionGroup("foo", (ValueError(), SyntaxError()))

    # nested exceptions
    with RaisesGroup(RaisesGroup(ValueError)):
        raise ExceptionGroup("foo", (ExceptionGroup("bar", (ValueError(),)),))

    with RaisesGroup(
        SyntaxError,
        RaisesGroup(ValueError),
        RaisesGroup(RuntimeError),
    ):
        raise ExceptionGroup(
            "foo",
            (
                SyntaxError(),
                ExceptionGroup("bar", (ValueError(),)),
                ExceptionGroup("", (RuntimeError(),)),
            ),
        )


def test_incorrect_number_exceptions() -> None:
    # We previously gave an error saying the number of exceptions was wrong,
    # but we now instead indicate excess/missing exceptions
    with (
        fails_raises_group(
            "1 matched exception. Unexpected exception(s): [RuntimeError()]"
        ),
        RaisesGroup(ValueError),
    ):
        raise ExceptionGroup("", (RuntimeError(), ValueError()))

    # will error if there's missing exceptions
    with (
        fails_raises_group(
            "1 matched exception. Too few exceptions raised, found no match for: ['SyntaxError']"
        ),
        RaisesGroup(ValueError, SyntaxError),
    ):
        raise ExceptionGroup("", (ValueError(),))

    with (
        fails_raises_group(
            "\n"
            "1 matched exception. \n"
            "Too few exceptions raised!\n"
            "The following expected exceptions did not find a match:\n"
            "  'ValueError'\n"
            "    It matches ValueError() which was paired with 'ValueError'"
        ),
        RaisesGroup(ValueError, ValueError),
    ):
        raise ExceptionGroup("", (ValueError(),))

    with (
        fails_raises_group(
            "\n"
            "1 matched exception. \n"
            "Unexpected exception(s)!\n"
            "The following raised exceptions did not find a match\n"
            "  ValueError():\n"
            "    It matches 'ValueError' which was paired with ValueError()"
        ),
        RaisesGroup(ValueError),
    ):
        raise ExceptionGroup("", (ValueError(), ValueError()))

    with (
        fails_raises_group(
            "\n"
            "1 matched exception. \n"
            "The following expected exceptions did not find a match:\n"
            "  'ValueError'\n"
            "    It matches ValueError() which was paired with 'ValueError'\n"
            "The following raised exceptions did not find a match\n"
            "  SyntaxError():\n"
            "    'SyntaxError' is not of type 'ValueError'"
        ),
        RaisesGroup(ValueError, ValueError),
    ):
        raise ExceptionGroup("", [ValueError(), SyntaxError()])


def test_flatten_subgroups() -> None:
    # loose semantics, as with expect*
    with RaisesGroup(ValueError, flatten_subgroups=True):
        raise ExceptionGroup("", (ExceptionGroup("", (ValueError(),)),))

    with RaisesGroup(ValueError, TypeError, flatten_subgroups=True):
        raise ExceptionGroup("", (ExceptionGroup("", (ValueError(), TypeError())),))
    with RaisesGroup(ValueError, TypeError, flatten_subgroups=True):
        raise ExceptionGroup("", [ExceptionGroup("", [ValueError()]), TypeError()])

    # mixed loose is possible if you want it to be at least N deep
    with RaisesGroup(RaisesGroup(ValueError, flatten_subgroups=True)):
        raise ExceptionGroup("", (ExceptionGroup("", (ValueError(),)),))
    with RaisesGroup(RaisesGroup(ValueError, flatten_subgroups=True)):
        raise ExceptionGroup(
            "",
            (ExceptionGroup("", (ExceptionGroup("", (ValueError(),)),)),),
        )

    # but not the other way around
    with pytest.raises(
        ValueError,
        match=r"^You cannot specify a nested structure inside a RaisesGroup with",
    ):
        RaisesGroup(RaisesGroup(ValueError), flatten_subgroups=True)  # type: ignore[call-overload]

    # flatten_subgroups is not sufficient to catch fully unwrapped
    with (
        fails_raises_group(
            "'ValueError' is not an exception group, but would match with `allow_unwrapped=True`"
        ),
        RaisesGroup(ValueError, flatten_subgroups=True),
    ):
        raise ValueError
    with (
        fails_raises_group(
            "RaisesGroup(ValueError, flatten_subgroups=True): 'ValueError' is not an exception group, but would match with `allow_unwrapped=True`"
        ),
        RaisesGroup(RaisesGroup(ValueError, flatten_subgroups=True)),
    ):
        raise ExceptionGroup("", (ValueError(),))

    # helpful suggestion if flatten_subgroups would make it pass
    with (
        fails_raises_group(
            "Raised exception group did not match: \n"
            "The following expected exceptions did not find a match:\n"
            "  'ValueError'\n"
            "  'TypeError'\n"
            "The following raised exceptions did not find a match\n"
            "  ExceptionGroup('', [ValueError(), TypeError()]):\n"
            "    Unexpected nested 'ExceptionGroup', expected 'ValueError'\n"
            "    Unexpected nested 'ExceptionGroup', expected 'TypeError'\n"
            "Did you mean to use `flatten_subgroups=True`?",
            add_prefix=False,
        ),
        RaisesGroup(ValueError, TypeError),
    ):
        raise ExceptionGroup("", [ExceptionGroup("", [ValueError(), TypeError()])])
    # but doesn't consider check (otherwise we'd break typing guarantees)
    with (
        fails_raises_group(
            "Raised exception group did not match: \n"
            "The following expected exceptions did not find a match:\n"
            "  'ValueError'\n"
            "  'TypeError'\n"
            "The following raised exceptions did not find a match\n"
            "  ExceptionGroup('', [ValueError(), TypeError()]):\n"
            "    Unexpected nested 'ExceptionGroup', expected 'ValueError'\n"
            "    Unexpected nested 'ExceptionGroup', expected 'TypeError'\n"
            "Did you mean to use `flatten_subgroups=True`?",
            add_prefix=False,
        ),
        RaisesGroup(
            ValueError,
            TypeError,
            check=lambda eg: len(eg.exceptions) == 1,
        ),
    ):
        raise ExceptionGroup("", [ExceptionGroup("", [ValueError(), TypeError()])])
    # correct number of exceptions, and flatten_subgroups would make it pass
    # This now doesn't print a repr of the caught exception at all, but that can be found in the traceback
    with (
        fails_raises_group(
            "Raised exception group did not match: Unexpected nested 'ExceptionGroup', expected 'ValueError'\n"
            "  Did you mean to use `flatten_subgroups=True`?",
            add_prefix=False,
        ),
        RaisesGroup(ValueError),
    ):
        raise ExceptionGroup("", [ExceptionGroup("", [ValueError()])])
    # correct number of exceptions, but flatten_subgroups wouldn't help, so we don't suggest it
    with (
        fails_raises_group("Unexpected nested 'ExceptionGroup', expected 'ValueError'"),
        RaisesGroup(ValueError),
    ):
        raise ExceptionGroup("", [ExceptionGroup("", [TypeError()])])

    # flatten_subgroups can be suggested if nested. This will implicitly ask the user to
    # do `RaisesGroup(RaisesGroup(ValueError, flatten_subgroups=True))` which is unlikely
    # to be what they actually want - but I don't think it's worth trying to special-case
    with (
        fails_raises_group(
            "RaisesGroup(ValueError): Unexpected nested 'ExceptionGroup', expected 'ValueError'\n"
            "  Did you mean to use `flatten_subgroups=True`?",
        ),
        RaisesGroup(RaisesGroup(ValueError)),
    ):
        raise ExceptionGroup(
            "",
            [ExceptionGroup("", [ExceptionGroup("", [ValueError()])])],
        )

    # Don't mention "unexpected nested" if expecting an ExceptionGroup.
    # Although it should perhaps be an error to specify `RaisesGroup(ExceptionGroup)` in
    # favor of doing `RaisesGroup(RaisesGroup(...))`.
    with (
        fails_raises_group("'BaseExceptionGroup' is not of type 'ExceptionGroup'"),
        RaisesGroup(ExceptionGroup),
    ):
        raise BaseExceptionGroup("", [BaseExceptionGroup("", [KeyboardInterrupt()])])


def test_catch_unwrapped_exceptions() -> None:
    # Catches lone exceptions with strict=False
    # just as except* would
    with RaisesGroup(ValueError, allow_unwrapped=True):
        raise ValueError

    # expecting multiple unwrapped exceptions is not possible
    with pytest.raises(
        ValueError,
        match=r"^You cannot specify multiple exceptions with",
    ):
        RaisesGroup(SyntaxError, ValueError, allow_unwrapped=True)  # type: ignore[call-overload]
    # if users want one of several exception types they need to use a Matcher
    # (which the error message suggests)
    with RaisesGroup(
        Matcher(check=lambda e: isinstance(e, (SyntaxError, ValueError))),
        allow_unwrapped=True,
    ):
        raise ValueError

    # Unwrapped nested `RaisesGroup` is likely a user error, so we raise an error.
    with pytest.raises(ValueError, match="has no effect when expecting"):
        RaisesGroup(RaisesGroup(ValueError), allow_unwrapped=True)  # type: ignore[call-overload]

    # But it *can* be used to check for nesting level +- 1 if they move it to
    # the nested RaisesGroup. Users should probably use `Matcher`s instead though.
    with RaisesGroup(RaisesGroup(ValueError, allow_unwrapped=True)):
        raise ExceptionGroup("", [ExceptionGroup("", [ValueError()])])
    with RaisesGroup(RaisesGroup(ValueError, allow_unwrapped=True)):
        raise ExceptionGroup("", [ValueError()])

    # with allow_unwrapped=False (default) it will not be caught
    with (
        fails_raises_group(
            "'ValueError' is not an exception group, but would match with `allow_unwrapped=True`"
        ),
        RaisesGroup(ValueError),
    ):
        raise ValueError("value error text")

    # allow_unwrapped on its own won't match against nested groups
    with (
        fails_raises_group(
            "Unexpected nested 'ExceptionGroup', expected 'ValueError'\n"
            "  Did you mean to use `flatten_subgroups=True`?",
        ),
        RaisesGroup(ValueError, allow_unwrapped=True),
    ):
        raise ExceptionGroup("foo", [ExceptionGroup("bar", [ValueError()])])

    # you need both allow_unwrapped and flatten_subgroups to fully emulate except*
    with RaisesGroup(ValueError, allow_unwrapped=True, flatten_subgroups=True):
        raise ExceptionGroup("", [ExceptionGroup("", [ValueError()])])

    # code coverage
    with (
        fails_raises_group(
            "Raised exception (group) did not match: 'TypeError' is not of type 'ValueError'",
            add_prefix=False,
        ),
        RaisesGroup(ValueError, allow_unwrapped=True),
    ):
        raise TypeError("this text doesn't show up in the error message")
    with (
        fails_raises_group(
            "Raised exception (group) did not match: Matcher(ValueError): 'TypeError' is not of type 'ValueError'",
            add_prefix=False,
        ),
        RaisesGroup(Matcher(ValueError), allow_unwrapped=True),
    ):
        raise TypeError

    # check we don't suggest unwrapping with nested RaisesGroup
    with (
        fails_raises_group("'ValueError' is not an exception group"),
        RaisesGroup(RaisesGroup(ValueError)),
    ):
        raise ValueError


def test_match() -> None:
    # supports match string
    with RaisesGroup(ValueError, match="bar"):
        raise ExceptionGroup("bar", (ValueError(),))

    # now also works with ^$
    with RaisesGroup(ValueError, match="^bar$"):
        raise ExceptionGroup("bar", (ValueError(),))

    # it also includes notes
    with RaisesGroup(ValueError, match="my note"):
        e = ExceptionGroup("bar", (ValueError(),))
        e.add_note("my note")
        raise e

    # and technically you can match it all with ^$
    # but you're probably better off using a Matcher at that point
    with RaisesGroup(ValueError, match="^bar\nmy note$"):
        e = ExceptionGroup("bar", (ValueError(),))
        e.add_note("my note")
        raise e

    with (
        fails_raises_group(
            "Regex pattern 'foo' did not match 'bar' of 'ExceptionGroup'"
        ),
        RaisesGroup(ValueError, match="foo"),
    ):
        raise ExceptionGroup("bar", (ValueError(),))

    # Suggest a fix for easy pitfall of adding match to the RaisesGroup instead of
    # using a Matcher.
    # This requires a single expected & raised exception, the expected is a type,
    # and `isinstance(raised, expected_type)`.
    with (
        fails_raises_group(
            "Regex pattern 'foo' did not match 'bar' of 'ExceptionGroup', but matched the expected 'ValueError'. You might want RaisesGroup(Matcher(ValueError, match='foo'))"
        ),
        RaisesGroup(ValueError, match="foo"),
    ):
        raise ExceptionGroup("bar", [ValueError("foo")])


def test_check() -> None:
    exc = ExceptionGroup("", (ValueError(),))

    def is_exc(e: ExceptionGroup[ValueError]) -> bool:
        return e is exc

    is_exc_repr = repr_callable(is_exc)
    with RaisesGroup(ValueError, check=is_exc):
        raise exc

    with (
        fails_raises_group(f"check {is_exc_repr} did not return True"),
        RaisesGroup(ValueError, check=is_exc),
    ):
        raise ExceptionGroup("", (ValueError(),))


def test_unwrapped_match_check() -> None:
    def my_check(e: object) -> bool:  # pragma: no cover
        return True

    msg = (
        "`allow_unwrapped=True` bypasses the `match` and `check` parameters"
        " if the exception is unwrapped. If you intended to match/check the"
        " exception you should use a `Matcher` object. If you want to match/check"
        " the exceptiongroup when the exception *is* wrapped you need to"
        " do e.g. `if isinstance(exc.value, ExceptionGroup):"
        " assert RaisesGroup(...).matches(exc.value)` afterwards."
    )
    with pytest.raises(ValueError, match=re.escape(msg)):
        RaisesGroup(ValueError, allow_unwrapped=True, match="foo")  # type: ignore[call-overload]
    with pytest.raises(ValueError, match=re.escape(msg)):
        RaisesGroup(ValueError, allow_unwrapped=True, check=my_check)  # type: ignore[call-overload]

    # Users should instead use a Matcher
    rg = RaisesGroup(Matcher(ValueError, match="^foo$"), allow_unwrapped=True)
    with rg:
        raise ValueError("foo")
    with rg:
        raise ExceptionGroup("", [ValueError("foo")])

    # or if they wanted to match/check the group, do a conditional `.matches()`
    with RaisesGroup(ValueError, allow_unwrapped=True) as exc:
        raise ExceptionGroup("bar", [ValueError("foo")])
    if isinstance(exc.value, ExceptionGroup):  # pragma: no branch
        assert RaisesGroup(ValueError, match="bar").matches(exc.value)


def test_RaisesGroup_matches() -> None:
    rg = RaisesGroup(ValueError)
    assert not rg.matches(None)
    assert not rg.matches(ValueError())
    assert rg.matches(ExceptionGroup("", (ValueError(),)))


def test_message() -> None:
    def check_message(
        message: str,
        body: RaisesGroup[BaseException],
    ) -> None:
        with (
            pytest.raises(
                AssertionError,
                match=f"^DID NOT RAISE any exception, expected {re.escape(message)}$",
            ),
            body,
        ):
            ...

    # basic
    check_message("ExceptionGroup(ValueError)", RaisesGroup(ValueError))
    # multiple exceptions
    check_message(
        "ExceptionGroup(ValueError, ValueError)",
        RaisesGroup(ValueError, ValueError),
    )
    # nested
    check_message(
        "ExceptionGroup(ExceptionGroup(ValueError))",
        RaisesGroup(RaisesGroup(ValueError)),
    )

    # Matcher
    check_message(
        "ExceptionGroup(Matcher(ValueError, match='my_str'))",
        RaisesGroup(Matcher(ValueError, "my_str")),
    )
    check_message(
        "ExceptionGroup(Matcher(match='my_str'))",
        RaisesGroup(Matcher(match="my_str")),
    )

    # BaseExceptionGroup
    check_message(
        "BaseExceptionGroup(KeyboardInterrupt)",
        RaisesGroup(KeyboardInterrupt),
    )
    # BaseExceptionGroup with type inside Matcher
    check_message(
        "BaseExceptionGroup(Matcher(KeyboardInterrupt))",
        RaisesGroup(Matcher(KeyboardInterrupt)),
    )
    # Base-ness transfers to parent containers
    check_message(
        "BaseExceptionGroup(BaseExceptionGroup(KeyboardInterrupt))",
        RaisesGroup(RaisesGroup(KeyboardInterrupt)),
    )
    # but not to child containers
    check_message(
        "BaseExceptionGroup(BaseExceptionGroup(KeyboardInterrupt), ExceptionGroup(ValueError))",
        RaisesGroup(RaisesGroup(KeyboardInterrupt), RaisesGroup(ValueError)),
    )


def test_assert_message() -> None:
    # the message does not need to list all parameters to RaisesGroup, nor all exceptions
    # in the exception group, as those are both visible in the traceback.
    # first fails to match
    with (
        fails_raises_group("'TypeError' is not of type 'ValueError'"),
        RaisesGroup(ValueError),
    ):
        raise ExceptionGroup("a", [TypeError()])
    with (
        fails_raises_group(
            "Raised exception group did not match: \n"
            "The following expected exceptions did not find a match:\n"
            "  RaisesGroup(ValueError)\n"
            "  RaisesGroup(ValueError, match='a')\n"
            "The following raised exceptions did not find a match\n"
            "  ExceptionGroup('', [RuntimeError()]):\n"
            "    RaisesGroup(ValueError): 'RuntimeError' is not of type 'ValueError'\n"
            "    RaisesGroup(ValueError, match='a'): Regex pattern 'a' did not match '' of 'ExceptionGroup'\n"
            "  RuntimeError():\n"
            "    RaisesGroup(ValueError): 'RuntimeError' is not an exception group\n"
            "    RaisesGroup(ValueError, match='a'): 'RuntimeError' is not an exception group",
            add_prefix=False,  # to see the full structure
        ),
        RaisesGroup(RaisesGroup(ValueError), RaisesGroup(ValueError, match="a")),
    ):
        raise ExceptionGroup(
            "",
            [ExceptionGroup("", [RuntimeError()]), RuntimeError()],
        )

    with (
        fails_raises_group(
            "Raised exception group did not match: \n"
            "2 matched exceptions. \n"
            "The following expected exceptions did not find a match:\n"
            "  RaisesGroup(RuntimeError)\n"
            "  RaisesGroup(ValueError)\n"
            "The following raised exceptions did not find a match\n"
            "  RuntimeError():\n"
            # "    'RuntimeError' is not of type 'ValueError'\n"
            # "    Matcher(TypeError): 'RuntimeError' is not of type 'TypeError'\n"
            "    RaisesGroup(RuntimeError): 'RuntimeError' is not an exception group, but would match with `allow_unwrapped=True`\n"
            "    RaisesGroup(ValueError): 'RuntimeError' is not an exception group\n"
            "  ValueError('bar'):\n"
            "    It matches 'ValueError' which was paired with ValueError('foo')\n"
            "    RaisesGroup(RuntimeError): 'ValueError' is not an exception group\n"
            "    RaisesGroup(ValueError): 'ValueError' is not an exception group, but would match with `allow_unwrapped=True`",
            add_prefix=False,  # to see the full structure
        ),
        RaisesGroup(
            ValueError,
            Matcher(TypeError),
            RaisesGroup(RuntimeError),
            RaisesGroup(ValueError),
        ),
    ):
        raise ExceptionGroup(
            "a",
            [RuntimeError(), TypeError(), ValueError("foo"), ValueError("bar")],
        )

    with (
        fails_raises_group(
            "1 matched exception. 'AssertionError' is not of type 'TypeError'"
        ),
        RaisesGroup(ValueError, TypeError),
    ):
        raise ExceptionGroup("a", [ValueError(), AssertionError()])

    with (
        fails_raises_group(
            "Matcher(ValueError): 'TypeError' is not of type 'ValueError'"
        ),
        RaisesGroup(Matcher(ValueError)),
    ):
        raise ExceptionGroup("a", [TypeError()])

    # suggest escaping
    with (
        fails_raises_group(
            "Raised exception group did not match: Regex pattern 'h(ell)o' did not match 'h(ell)o' of 'ExceptionGroup'\n"
            "  Did you mean to `re.escape()` the regex?",
            add_prefix=False,  # to see the full structure
        ),
        RaisesGroup(ValueError, match="h(ell)o"),
    ):
        raise ExceptionGroup("h(ell)o", [ValueError()])
    with (
        fails_raises_group(
            "Matcher(match='h(ell)o'): Regex pattern 'h(ell)o' did not match 'h(ell)o'\n"
            "  Did you mean to `re.escape()` the regex?",
        ),
        RaisesGroup(Matcher(match="h(ell)o")),
    ):
        raise ExceptionGroup("", [ValueError("h(ell)o")])

    with (
        fails_raises_group(
            "Raised exception group did not match: \n"
            "The following expected exceptions did not find a match:\n"
            "  'ValueError'\n"
            "  'ValueError'\n"
            "  'ValueError'\n"
            "  'ValueError'\n"
            "The following raised exceptions did not find a match\n"
            "  ExceptionGroup('', [ValueError(), TypeError()]):\n"
            "    Unexpected nested 'ExceptionGroup', expected 'ValueError'\n"
            "    Unexpected nested 'ExceptionGroup', expected 'ValueError'\n"
            "    Unexpected nested 'ExceptionGroup', expected 'ValueError'\n"
            "    Unexpected nested 'ExceptionGroup', expected 'ValueError'",
            add_prefix=False,  # to see the full structure
        ),
        RaisesGroup(ValueError, ValueError, ValueError, ValueError),
    ):
        raise ExceptionGroup("", [ExceptionGroup("", [ValueError(), TypeError()])])


def test_message_indent() -> None:
    with (
        fails_raises_group(
            "Raised exception group did not match: \n"
            "The following expected exceptions did not find a match:\n"
            "  RaisesGroup(ValueError, ValueError)\n"
            "  'ValueError'\n"
            "The following raised exceptions did not find a match\n"
            "  ExceptionGroup('', [TypeError(), RuntimeError()]):\n"
            "    RaisesGroup(ValueError, ValueError): \n"
            "      The following expected exceptions did not find a match:\n"
            "        'ValueError'\n"
            "        'ValueError'\n"
            "      The following raised exceptions did not find a match\n"
            "        TypeError():\n"
            "          'TypeError' is not of type 'ValueError'\n"
            "          'TypeError' is not of type 'ValueError'\n"
            "        RuntimeError():\n"
            "          'RuntimeError' is not of type 'ValueError'\n"
            "          'RuntimeError' is not of type 'ValueError'\n"
            # TODO: this line is not great, should maybe follow the same format as the other and say
            # 'ValueError': Unexpected nested 'ExceptionGroup' (?)
            "    Unexpected nested 'ExceptionGroup', expected 'ValueError'\n"
            "  TypeError():\n"
            "    RaisesGroup(ValueError, ValueError): 'TypeError' is not an exception group\n"
            "    'TypeError' is not of type 'ValueError'",
            add_prefix=False,
        ),
        RaisesGroup(
            RaisesGroup(ValueError, ValueError),
            ValueError,
        ),
    ):
        raise ExceptionGroup(
            "",
            [
                ExceptionGroup("", [TypeError(), RuntimeError()]),
                TypeError(),
            ],
        )
    with (
        fails_raises_group(
            "Raised exception group did not match: \n"
            "RaisesGroup(ValueError, ValueError): \n"
            "  The following expected exceptions did not find a match:\n"
            "    'ValueError'\n"
            "    'ValueError'\n"
            "  The following raised exceptions did not find a match\n"
            "    TypeError():\n"
            "      'TypeError' is not of type 'ValueError'\n"
            "      'TypeError' is not of type 'ValueError'\n"
            "    RuntimeError():\n"
            "      'RuntimeError' is not of type 'ValueError'\n"
            "      'RuntimeError' is not of type 'ValueError'",
            add_prefix=False,
        ),
        RaisesGroup(
            RaisesGroup(ValueError, ValueError),
        ),
    ):
        raise ExceptionGroup(
            "",
            [
                ExceptionGroup("", [TypeError(), RuntimeError()]),
            ],
        )


def test_suggestion_on_nested_and_brief_error() -> None:
    # Make sure "Did you mean" suggestion gets indented iff it follows a single-line error
    with (
        fails_raises_group(
            "\n"
            "The following expected exceptions did not find a match:\n"
            "  RaisesGroup(ValueError)\n"
            "  'ValueError'\n"
            "The following raised exceptions did not find a match\n"
            "  ExceptionGroup('', [ExceptionGroup('', [ValueError()])]):\n"
            "    RaisesGroup(ValueError): Unexpected nested 'ExceptionGroup', expected 'ValueError'\n"
            "      Did you mean to use `flatten_subgroups=True`?\n"
            "    Unexpected nested 'ExceptionGroup', expected 'ValueError'",
        ),
        RaisesGroup(RaisesGroup(ValueError), ValueError),
    ):
        raise ExceptionGroup(
            "",
            [ExceptionGroup("", [ExceptionGroup("", [ValueError()])])],
        )
    # if indented here it would look like another raised exception
    with (
        fails_raises_group(
            "\n"
            "The following expected exceptions did not find a match:\n"
            "  RaisesGroup(ValueError, ValueError)\n"
            "  'ValueError'\n"
            "The following raised exceptions did not find a match\n"
            "  ExceptionGroup('', [ValueError(), ExceptionGroup('', [ValueError()])]):\n"
            "    RaisesGroup(ValueError, ValueError): \n"
            "      1 matched exception. \n"
            "      The following expected exceptions did not find a match:\n"
            "        'ValueError'\n"
            "          It matches ValueError() which was paired with 'ValueError'\n"
            "      The following raised exceptions did not find a match\n"
            "        ExceptionGroup('', [ValueError()]):\n"
            "          Unexpected nested 'ExceptionGroup', expected 'ValueError'\n"
            "      Did you mean to use `flatten_subgroups=True`?\n"
            "    Unexpected nested 'ExceptionGroup', expected 'ValueError'"
        ),
        RaisesGroup(RaisesGroup(ValueError, ValueError), ValueError),
    ):
        raise ExceptionGroup(
            "",
            [ExceptionGroup("", [ValueError(), ExceptionGroup("", [ValueError()])])],
        )

    # re.escape always comes after single-line errors
    with (
        fails_raises_group(
            "\n"
            "The following expected exceptions did not find a match:\n"
            "  RaisesGroup(Exception, match='^hello')\n"
            "  'ValueError'\n"
            "The following raised exceptions did not find a match\n"
            "  ExceptionGroup('^hello', [Exception()]):\n"
            "    RaisesGroup(Exception, match='^hello'): Regex pattern '^hello' did not match '^hello' of 'ExceptionGroup'\n"
            "      Did you mean to `re.escape()` the regex?\n"
            "    Unexpected nested 'ExceptionGroup', expected 'ValueError'"
        ),
        RaisesGroup(RaisesGroup(Exception, match="^hello"), ValueError),
    ):
        raise ExceptionGroup("", [ExceptionGroup("^hello", [Exception()])])


def test_assert_message_nested() -> None:
    # we only get one instance of aaaaaaaaaa... and bbbbbb..., but we do get multiple instances of ccccc... and dddddd..
    # but I think this now only prints the full repr when that is necessary to disambiguate exceptions
    with (
        fails_raises_group(
            "Raised exception group did not match: \n"
            "The following expected exceptions did not find a match:\n"
            "  RaisesGroup(ValueError)\n"
            "  RaisesGroup(RaisesGroup(ValueError))\n"
            "  RaisesGroup(Matcher(TypeError, match='foo'))\n"
            "  RaisesGroup(TypeError, ValueError)\n"
            "The following raised exceptions did not find a match\n"
            "  TypeError('aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'):\n"
            "    RaisesGroup(ValueError): 'TypeError' is not an exception group\n"
            "    RaisesGroup(RaisesGroup(ValueError)): 'TypeError' is not an exception group\n"
            "    RaisesGroup(Matcher(TypeError, match='foo')): 'TypeError' is not an exception group\n"
            "    RaisesGroup(TypeError, ValueError): 'TypeError' is not an exception group\n"
            "  ExceptionGroup('Exceptions from Trio nursery', [TypeError('bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb')]):\n"
            "    RaisesGroup(ValueError): 'TypeError' is not of type 'ValueError'\n"
            "    RaisesGroup(RaisesGroup(ValueError)): RaisesGroup(ValueError): 'TypeError' is not an exception group\n"
            "    RaisesGroup(Matcher(TypeError, match='foo')): Matcher(TypeError, match='foo'): Regex pattern 'foo' did not match 'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb'\n"
            "    RaisesGroup(TypeError, ValueError): 1 matched exception. Too few exceptions raised, found no match for: ['ValueError']\n"
            "  ExceptionGroup('Exceptions from Trio nursery', [TypeError('cccccccccccccccccccccccccccccccccccccccc'), TypeError('dddddddddddddddddddddddddddddddddddddddd')]):\n"
            "    RaisesGroup(ValueError): \n"
            "      The following expected exceptions did not find a match:\n"
            "        'ValueError'\n"
            "      The following raised exceptions did not find a match\n"
            "        TypeError('cccccccccccccccccccccccccccccccccccccccc'):\n"
            "          'TypeError' is not of type 'ValueError'\n"
            "        TypeError('dddddddddddddddddddddddddddddddddddddddd'):\n"
            "          'TypeError' is not of type 'ValueError'\n"
            "    RaisesGroup(RaisesGroup(ValueError)): \n"
            "      The following expected exceptions did not find a match:\n"
            "        RaisesGroup(ValueError)\n"
            "      The following raised exceptions did not find a match\n"
            "        TypeError('cccccccccccccccccccccccccccccccccccccccc'):\n"
            "          RaisesGroup(ValueError): 'TypeError' is not an exception group\n"
            "        TypeError('dddddddddddddddddddddddddddddddddddddddd'):\n"
            "          RaisesGroup(ValueError): 'TypeError' is not an exception group\n"
            "    RaisesGroup(Matcher(TypeError, match='foo')): \n"
            "      The following expected exceptions did not find a match:\n"
            "        Matcher(TypeError, match='foo')\n"
            "      The following raised exceptions did not find a match\n"
            "        TypeError('cccccccccccccccccccccccccccccccccccccccc'):\n"
            "          Matcher(TypeError, match='foo'): Regex pattern 'foo' did not match 'cccccccccccccccccccccccccccccccccccccccc'\n"
            "        TypeError('dddddddddddddddddddddddddddddddddddddddd'):\n"
            "          Matcher(TypeError, match='foo'): Regex pattern 'foo' did not match 'dddddddddddddddddddddddddddddddddddddddd'\n"
            "    RaisesGroup(TypeError, ValueError): \n"
            "      1 matched exception. \n"
            "      The following expected exceptions did not find a match:\n"
            "        'ValueError'\n"
            "      The following raised exceptions did not find a match\n"
            "        TypeError('dddddddddddddddddddddddddddddddddddddddd'):\n"
            "          It matches 'TypeError' which was paired with TypeError('cccccccccccccccccccccccccccccccccccccccc')\n"
            "          'TypeError' is not of type 'ValueError'",
            add_prefix=False,  # to see the full structure
        ),
        RaisesGroup(
            RaisesGroup(ValueError),
            RaisesGroup(RaisesGroup(ValueError)),
            RaisesGroup(Matcher(TypeError, match="foo")),
            RaisesGroup(TypeError, ValueError),
        ),
    ):
        raise ExceptionGroup(
            "",
            [
                TypeError("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"),
                ExceptionGroup(
                    "Exceptions from Trio nursery",
                    [TypeError("bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb")],
                ),
                ExceptionGroup(
                    "Exceptions from Trio nursery",
                    [
                        TypeError("cccccccccccccccccccccccccccccccccccccccc"),
                        TypeError("dddddddddddddddddddddddddddddddddddddddd"),
                    ],
                ),
            ],
        )


@pytest.mark.skipif(
    "hypothesis" in sys.modules,
    reason="hypothesis may have monkeypatched _check_repr",
)
def test_check_no_patched_repr() -> None:
    # We make `_check_repr` monkeypatchable to avoid this very ugly and verbose
    # repr. The other tests that use `check` make use of `_check_repr` so they'll
    # continue passing in case it is patched - but we have this one test that
    # demonstrates just how nasty it gets otherwise.
    with (
        pytest.raises(
            AssertionError,
            match=(
                r"^Raised exception group did not match: \n"
                r"The following expected exceptions did not find a match:\n"
                r"  Matcher\(check=<function test_check_no_patched_repr.<locals>.<lambda> at .*>\)\n"
                r"  'TypeError'\n"
                r"The following raised exceptions did not find a match\n"
                r"  ValueError\('foo'\):\n"
                r"    Matcher\(check=<function test_check_no_patched_repr.<locals>.<lambda> at .*>\): check did not return True\n"
                r"    'ValueError' is not of type 'TypeError'\n"
                r"  ValueError\('bar'\):\n"
                r"    Matcher\(check=<function test_check_no_patched_repr.<locals>.<lambda> at .*>\): check did not return True\n"
                r"    'ValueError' is not of type 'TypeError'$"
            ),
        ),
        RaisesGroup(Matcher(check=lambda x: False), TypeError),
    ):
        raise ExceptionGroup("", [ValueError("foo"), ValueError("bar")])


def test_misordering_example() -> None:
    with (
        fails_raises_group(
            "\n"
            "3 matched exceptions. \n"
            "The following expected exceptions did not find a match:\n"
            "  Matcher(ValueError, match='foo')\n"
            "    It matches ValueError('foo') which was paired with 'ValueError'\n"
            "    It matches ValueError('foo') which was paired with 'ValueError'\n"
            "    It matches ValueError('foo') which was paired with 'ValueError'\n"
            "The following raised exceptions did not find a match\n"
            "  ValueError('bar'):\n"
            "    It matches 'ValueError' which was paired with ValueError('foo')\n"
            "    It matches 'ValueError' which was paired with ValueError('foo')\n"
            "    It matches 'ValueError' which was paired with ValueError('foo')\n"
            "    Matcher(ValueError, match='foo'): Regex pattern 'foo' did not match 'bar'\n"
            "There exist a possible match when attempting an exhaustive check, but RaisesGroup uses a greedy algorithm. Please make your expected exceptions more stringent with `Matcher` etc so the greedy algorithm can function."
        ),
        RaisesGroup(
            ValueError, ValueError, ValueError, Matcher(ValueError, match="foo")
        ),
    ):
        raise ExceptionGroup(
            "",
            [
                ValueError("foo"),
                ValueError("foo"),
                ValueError("foo"),
                ValueError("bar"),
            ],
        )


def test_brief_error_on_one_fail() -> None:
    """if only one raised and one expected fail to match up, we print a full table iff
    the raised exception would match one of the expected that previously got matched"""
    # no also-matched
    with (
        fails_raises_group(
            "1 matched exception. 'TypeError' is not of type 'RuntimeError'"
        ),
        RaisesGroup(ValueError, RuntimeError),
    ):
        raise ExceptionGroup("", [ValueError(), TypeError()])

    # raised would match an expected
    with (
        fails_raises_group(
            "\n"
            "1 matched exception. \n"
            "The following expected exceptions did not find a match:\n"
            "  'RuntimeError'\n"
            "The following raised exceptions did not find a match\n"
            "  TypeError():\n"
            "    It matches 'Exception' which was paired with ValueError()\n"
            "    'TypeError' is not of type 'RuntimeError'"
        ),
        RaisesGroup(Exception, RuntimeError),
    ):
        raise ExceptionGroup("", [ValueError(), TypeError()])

    # expected would match a raised
    with (
        fails_raises_group(
            "\n"
            "1 matched exception. \n"
            "The following expected exceptions did not find a match:\n"
            "  'ValueError'\n"
            "    It matches ValueError() which was paired with 'ValueError'\n"
            "The following raised exceptions did not find a match\n"
            "  TypeError():\n"
            "    'TypeError' is not of type 'ValueError'"
        ),
        RaisesGroup(ValueError, ValueError),
    ):
        raise ExceptionGroup("", [ValueError(), TypeError()])


def test_identity_oopsies() -> None:
    # it's both possible to have several instances of the same exception in the same group
    # and to expect multiple of the same type
    # this previously messed up the logic

    with (
        fails_raises_group(
            "3 matched exceptions. 'RuntimeError' is not of type 'TypeError'"
        ),
        RaisesGroup(ValueError, ValueError, ValueError, TypeError),
    ):
        raise ExceptionGroup(
            "", [ValueError(), ValueError(), ValueError(), RuntimeError()]
        )

    e = ValueError("foo")
    m = Matcher(match="bar")
    with (
        fails_raises_group(
            "\n"
            "The following expected exceptions did not find a match:\n"
            "  Matcher(match='bar')\n"
            "  Matcher(match='bar')\n"
            "  Matcher(match='bar')\n"
            "The following raised exceptions did not find a match\n"
            "  ValueError('foo'):\n"
            "    Matcher(match='bar'): Regex pattern 'bar' did not match 'foo'\n"
            "    Matcher(match='bar'): Regex pattern 'bar' did not match 'foo'\n"
            "    Matcher(match='bar'): Regex pattern 'bar' did not match 'foo'\n"
            "  ValueError('foo'):\n"
            "    Matcher(match='bar'): Regex pattern 'bar' did not match 'foo'\n"
            "    Matcher(match='bar'): Regex pattern 'bar' did not match 'foo'\n"
            "    Matcher(match='bar'): Regex pattern 'bar' did not match 'foo'\n"
            "  ValueError('foo'):\n"
            "    Matcher(match='bar'): Regex pattern 'bar' did not match 'foo'\n"
            "    Matcher(match='bar'): Regex pattern 'bar' did not match 'foo'\n"
            "    Matcher(match='bar'): Regex pattern 'bar' did not match 'foo'"
        ),
        RaisesGroup(m, m, m),
    ):
        raise ExceptionGroup("", [e, e, e])


def test_matcher() -> None:
    with pytest.raises(
        ValueError,
        match=r"^You must specify at least one parameter to match on.$",
    ):
        Matcher()  # type: ignore[call-overload]
    with pytest.raises(
        ValueError,
        match=f"^exception_type {re.escape(repr(object))} must be a subclass of BaseException$",
    ):
        Matcher(object)  # type: ignore[type-var]

    with RaisesGroup(Matcher(ValueError)):
        raise ExceptionGroup("", (ValueError(),))
    with (
        fails_raises_group(
            "Matcher(TypeError): 'ValueError' is not of type 'TypeError'"
        ),
        RaisesGroup(Matcher(TypeError)),
    ):
        raise ExceptionGroup("", (ValueError(),))


def test_matcher_match() -> None:
    with RaisesGroup(Matcher(ValueError, "foo")):
        raise ExceptionGroup("", (ValueError("foo"),))
    with (
        fails_raises_group(
            "Matcher(ValueError, match='foo'): Regex pattern 'foo' did not match 'bar'"
        ),
        RaisesGroup(Matcher(ValueError, "foo")),
    ):
        raise ExceptionGroup("", (ValueError("bar"),))

    # Can be used without specifying the type
    with RaisesGroup(Matcher(match="foo")):
        raise ExceptionGroup("", (ValueError("foo"),))
    with (
        fails_raises_group(
            "Matcher(match='foo'): Regex pattern 'foo' did not match 'bar'"
        ),
        RaisesGroup(Matcher(match="foo")),
    ):
        raise ExceptionGroup("", (ValueError("bar"),))

    # check ^$
    with RaisesGroup(Matcher(ValueError, match="^bar$")):
        raise ExceptionGroup("", [ValueError("bar")])
    with (
        fails_raises_group(
            "Matcher(ValueError, match='^bar$'): Regex pattern '^bar$' did not match 'barr'"
        ),
        RaisesGroup(Matcher(ValueError, match="^bar$")),
    ):
        raise ExceptionGroup("", [ValueError("barr")])


def test_Matcher_check() -> None:
    def check_oserror_and_errno_is_5(e: BaseException) -> bool:
        return isinstance(e, OSError) and e.errno == 5

    with RaisesGroup(Matcher(check=check_oserror_and_errno_is_5)):
        raise ExceptionGroup("", (OSError(5, ""),))

    # specifying exception_type narrows the parameter type to the callable
    def check_errno_is_5(e: OSError) -> bool:
        return e.errno == 5

    with RaisesGroup(Matcher(OSError, check=check_errno_is_5)):
        raise ExceptionGroup("", (OSError(5, ""),))

    # avoid printing overly verbose repr multiple times
    with (
        fails_raises_group(
            f"Matcher(OSError, check={check_errno_is_5!r}): check did not return True"
        ),
        RaisesGroup(Matcher(OSError, check=check_errno_is_5)),
    ):
        raise ExceptionGroup("", (OSError(6, ""),))

    # in nested cases you still get it multiple times though
    # to address this you'd need logic in Matcher.__repr__ and RaisesGroup.__repr__
    with (
        fails_raises_group(
            f"RaisesGroup(Matcher(OSError, check={check_errno_is_5!r})): Matcher(OSError, check={check_errno_is_5!r}): check did not return True"
        ),
        RaisesGroup(RaisesGroup(Matcher(OSError, check=check_errno_is_5))),
    ):
        raise ExceptionGroup("", [ExceptionGroup("", [OSError(6, "")])])


def test_matcher_tostring() -> None:
    assert str(Matcher(ValueError)) == "Matcher(ValueError)"
    assert str(Matcher(match="[a-z]")) == "Matcher(match='[a-z]')"
    pattern_no_flags = re.compile(r"noflag", 0)
    assert str(Matcher(match=pattern_no_flags)) == "Matcher(match='noflag')"
    pattern_flags = re.compile(r"noflag", re.IGNORECASE)
    assert str(Matcher(match=pattern_flags)) == f"Matcher(match={pattern_flags!r})"
    assert (
        str(Matcher(ValueError, match="re", check=bool))
        == f"Matcher(ValueError, match='re', check={bool!r})"
    )


def test_raisesgroup_tostring() -> None:
    def check_str_and_repr(s: str) -> None:
        evaled = eval(s)
        assert s == str(evaled) == repr(evaled)

    check_str_and_repr("RaisesGroup(ValueError)")
    check_str_and_repr("RaisesGroup(RaisesGroup(ValueError))")
    check_str_and_repr("RaisesGroup(Matcher(ValueError))")
    check_str_and_repr("RaisesGroup(ValueError, allow_unwrapped=True)")
    check_str_and_repr("RaisesGroup(ValueError, match='aoeu')")

    assert (
        str(RaisesGroup(ValueError, match="[a-z]", check=bool))
        == f"RaisesGroup(ValueError, match='[a-z]', check={bool!r})"
    )


def test__ExceptionInfo(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        trio.testing._raises_group,
        "ExceptionInfo",
        trio.testing._raises_group._ExceptionInfo,
    )
    with RaisesGroup(ValueError) as excinfo:
        raise ExceptionGroup("", (ValueError("hello"),))
    assert excinfo.type is ExceptionGroup
    assert excinfo.value.exceptions[0].args == ("hello",)
    assert isinstance(excinfo.tb, TracebackType)


def test_raisesgroup_matcher_deprecation() -> None:
    with pytest.deprecated_call():
        trio.testing.Matcher  # type: ignore # noqa: B018

    with pytest.deprecated_call():
        trio.testing.RaisesGroup  # type: ignore # noqa: B018

    with pytest.deprecated_call():
        from trio.testing import Matcher  # type: ignore # noqa: F401

    with pytest.deprecated_call():
        from trio.testing import RaisesGroup  # type: ignore # noqa: F401
