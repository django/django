#
# Copyright (C) 2009-2020 the sqlparse authors and contributors
# <see AUTHORS file>
#
# This module is part of python-sqlparse and is released under
# the BSD License: https://opensource.org/licenses/BSD-3-Clause
#
# The Token implementation is based on pygment's token system written
# by Georg Brandl.
# http://pygments.org/

"""Tokens"""


class _TokenType(tuple):
    parent = None

    def __contains__(self, item):
        return item is not None and (self is item or item[:len(self)] == self)

    def __getattr__(self, name):
        # don't mess with dunder
        if name.startswith('__'):
            return super().__getattr__(self, name)
        new = _TokenType(self + (name,))
        setattr(self, name, new)
        new.parent = self
        return new

    def __repr__(self):
        # self can be False only if its the `root` i.e. Token itself
        return 'Token' + ('.' if self else '') + '.'.join(self)


Token = _TokenType()

# Special token types
Text = Token.Text
Whitespace = Text.Whitespace
Newline = Whitespace.Newline
Error = Token.Error
# Text that doesn't belong to this lexer (e.g. HTML in PHP)
Other = Token.Other

# Common token types for source code
Keyword = Token.Keyword
Name = Token.Name
Literal = Token.Literal
String = Literal.String
Number = Literal.Number
Punctuation = Token.Punctuation
Operator = Token.Operator
Comparison = Operator.Comparison
Wildcard = Token.Wildcard
Comment = Token.Comment
Assignment = Token.Assignment

# Generic types for non-source code
Generic = Token.Generic
Command = Generic.Command

# String and some others are not direct children of Token.
# alias them:
Token.Token = Token
Token.String = String
Token.Number = Number

# SQL specific tokens
DML = Keyword.DML
DDL = Keyword.DDL
CTE = Keyword.CTE
