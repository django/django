#
# Copyright (C) 2009-2020 the sqlparse authors and contributors
# <see AUTHORS file>
#
# This module is part of python-sqlparse and is released under
# the BSD License: https://opensource.org/licenses/BSD-3-Clause

import itertools
import re
from collections import deque
from contextlib import contextmanager

# This regular expression replaces the home-cooked parser that was here before.
# It is much faster, but requires an extra post-processing step to get the
# desired results (that are compatible with what you would expect from the
# str.splitlines() method).
#
# It matches groups of characters: newlines, quoted strings, or unquoted text,
# and splits on that basis. The post-processing step puts those back together
# into the actual lines of SQL.
SPLIT_REGEX = re.compile(r"""
(
 (?:                     # Start of non-capturing group
  (?:\r\n|\r|\n)      |  # Match any single newline, or
  [^\r\n'"]+          |  # Match any character series without quotes or
                         # newlines, or
  "(?:[^"\\]|\\.)*"   |  # Match double-quoted strings, or
  '(?:[^'\\]|\\.)*'      # Match single quoted strings
 )
)
""", re.VERBOSE)

LINE_MATCH = re.compile(r'(\r\n|\r|\n)')


def split_unquoted_newlines(stmt):
    """Split a string on all unquoted newlines.

    Unlike str.splitlines(), this will ignore CR/LF/CR+LF if the requisite
    character is inside of a string."""
    text = str(stmt)
    lines = SPLIT_REGEX.split(text)
    outputlines = ['']
    for line in lines:
        if not line:
            continue
        elif LINE_MATCH.match(line):
            outputlines.append('')
        else:
            outputlines[-1] += line
    return outputlines


def remove_quotes(val):
    """Helper that removes surrounding quotes from strings."""
    if val is None:
        return
    if val[0] in ('"', "'", '`') and val[0] == val[-1]:
        val = val[1:-1]
    return val


def recurse(*cls):
    """Function decorator to help with recursion

    :param cls: Classes to not recurse over
    :return: function
    """
    def wrap(f):
        def wrapped_f(tlist):
            for sgroup in tlist.get_sublists():
                if not isinstance(sgroup, cls):
                    wrapped_f(sgroup)
            f(tlist)

        return wrapped_f

    return wrap


def imt(token, i=None, m=None, t=None):
    """Helper function to simplify comparisons Instance, Match and TokenType
    :param token:
    :param i: Class or Tuple/List of Classes
    :param m: Tuple of TokenType & Value. Can be list of Tuple for multiple
    :param t: TokenType or Tuple/List of TokenTypes
    :return:  bool
    """
    clss = i
    types = [t, ] if t and not isinstance(t, list) else t
    mpatterns = [m, ] if m and not isinstance(m, list) else m

    if token is None:
        return False
    elif clss and isinstance(token, clss):
        return True
    elif mpatterns and any(token.match(*pattern) for pattern in mpatterns):
        return True
    elif types and any(token.ttype in ttype for ttype in types):
        return True
    else:
        return False


def consume(iterator, n):
    """Advance the iterator n-steps ahead. If n is none, consume entirely."""
    deque(itertools.islice(iterator, n), maxlen=0)


@contextmanager
def offset(filter_, n=0):
    filter_.offset += n
    yield
    filter_.offset -= n


@contextmanager
def indent(filter_, n=1):
    filter_.indent += n
    yield
    filter_.indent -= n
