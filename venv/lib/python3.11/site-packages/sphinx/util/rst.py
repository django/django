"""reST helper functions."""

from __future__ import annotations

import re
from collections import defaultdict
from contextlib import contextmanager
from typing import TYPE_CHECKING
from unicodedata import east_asian_width

from docutils.parsers.rst import roles
from docutils.parsers.rst.languages import en as english
from docutils.parsers.rst.states import Body
from docutils.utils import Reporter
from jinja2 import Environment, pass_environment

from sphinx.locale import __
from sphinx.util import docutils, logging

if TYPE_CHECKING:
    from collections.abc import Generator

    from docutils.statemachine import StringList

logger = logging.getLogger(__name__)

FIELD_NAME_RE = re.compile(Body.patterns['field_marker'])
symbols_re = re.compile(r'([!-\-/:-@\[-`{-~])')  # symbols without dot(0x2e)
SECTIONING_CHARS = ['=', '-', '~']

# width of characters
WIDECHARS: dict[str, str] = defaultdict(lambda: "WF")  # WF: Wide + Full-width
WIDECHARS["ja"] = "WFA"  # In Japanese, Ambiguous characters also have double width


def escape(text: str) -> str:
    text = symbols_re.sub(r'\\\1', text)
    text = re.sub(r'^\.', r'\.', text)  # escape a dot at top
    return text


def textwidth(text: str, widechars: str = 'WF') -> int:
    """Get width of text."""
    def charwidth(char: str, widechars: str) -> int:
        if east_asian_width(char) in widechars:
            return 2
        else:
            return 1

    return sum(charwidth(c, widechars) for c in text)


@pass_environment
def heading(env: Environment, text: str, level: int = 1) -> str:
    """Create a heading for *level*."""
    assert level <= 3
    width = textwidth(text, WIDECHARS[env.language])
    sectioning_char = SECTIONING_CHARS[level - 1]
    return f'{text}\n{sectioning_char * width}'


@contextmanager
def default_role(docname: str, name: str) -> Generator[None, None, None]:
    if name:
        dummy_reporter = Reporter('', 4, 4)
        role_fn, _ = roles.role(name, english, 0, dummy_reporter)
        if role_fn:  # type: ignore[truthy-function]
            docutils.register_role('', role_fn)  # type: ignore[arg-type]
        else:
            logger.warning(__('default role %s not found'), name, location=docname)

    yield

    docutils.unregister_role('')


def prepend_prolog(content: StringList, prolog: str) -> None:
    """Prepend a string to content body as prolog."""
    if prolog:
        pos = 0
        for line in content:
            if FIELD_NAME_RE.match(line):
                pos += 1
            else:
                break

        if pos > 0:
            # insert a blank line after docinfo
            content.insert(pos, '', '<generated>', 0)
            pos += 1

        # insert prolog (after docinfo if exists)
        lineno = 0
        for lineno, line in enumerate(prolog.splitlines()):
            content.insert(pos + lineno, line, '<rst_prolog>', lineno)

        content.insert(pos + lineno + 1, '', '<generated>', 0)


def append_epilog(content: StringList, epilog: str) -> None:
    """Append a string to content body as epilog."""
    if epilog:
        if len(content) > 0:
            source, lineno = content.info(-1)
        else:
            source = '<generated>'
            lineno = 0
        content.append('', source, lineno + 1)
        for lineno, line in enumerate(epilog.splitlines()):
            content.append(line, '<rst_epilog>', lineno)
