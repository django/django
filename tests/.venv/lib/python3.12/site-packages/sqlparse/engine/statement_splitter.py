#
# Copyright (C) 2009-2020 the sqlparse authors and contributors
# <see AUTHORS file>
#
# This module is part of python-sqlparse and is released under
# the BSD License: https://opensource.org/licenses/BSD-3-Clause

from sqlparse import sql, tokens as T


class StatementSplitter:
    """Filter that split stream at individual statements"""

    def __init__(self):
        self._reset()

    def _reset(self):
        """Set the filter attributes to its default values"""
        self._in_declare = False
        self._in_case = False
        self._is_create = False
        self._begin_depth = 0
        self._seen_begin = False

        self.consume_ws = False
        self.tokens = []
        self.level = 0

    def _change_splitlevel(self, ttype, value):
        """Get the new split level (increase, decrease or remain equal)"""

        # parenthesis increase/decrease a level
        if ttype is T.Punctuation and value == '(':
            return 1
        elif ttype is T.Punctuation and value == ')':
            return -1
        elif ttype not in T.Keyword:  # if normal token return
            return 0

        # Everything after here is ttype = T.Keyword
        # Also to note, once entered an If statement you are done and basically
        # returning
        unified = value.upper()

        # three keywords begin with CREATE, but only one of them is DDL
        # DDL Create though can contain more words such as "or replace"
        if ttype is T.Keyword.DDL and unified.startswith('CREATE'):
            self._is_create = True
            return 0

        # can have nested declare inside of being...
        if unified == 'DECLARE' and self._is_create and self._begin_depth == 0:
            self._in_declare = True
            return 1

        if unified == 'BEGIN':
            self._begin_depth += 1
            self._seen_begin = True
            if self._is_create:
                # FIXME(andi): This makes no sense.  ## this comment neither
                return 1
            return 0

        # Issue826: If we see a transaction keyword after BEGIN,
        # it's a transaction statement, not a block.
        if self._seen_begin and \
                (ttype is T.Keyword or ttype is T.Name) and \
                unified in ('TRANSACTION', 'WORK', 'TRAN',
                            'DISTRIBUTED', 'DEFERRED',
                            'IMMEDIATE', 'EXCLUSIVE'):
            self._begin_depth = max(0, self._begin_depth - 1)
            self._seen_begin = False
            return 0

        # BEGIN and CASE/WHEN both end with END
        if unified == 'END':
            if not self._in_case:
                self._begin_depth = max(0, self._begin_depth - 1)
            else:
                self._in_case = False
            return -1

        if (unified in ('IF', 'FOR', 'WHILE', 'CASE')
                and self._is_create and self._begin_depth > 0):
            if unified == 'CASE':
                self._in_case = True
            return 1

        if unified in ('END IF', 'END FOR', 'END WHILE'):
            return -1

        # Default
        return 0

    def process(self, stream):
        """Process the stream"""
        EOS_TTYPE = T.Whitespace, T.Comment.Single

        # Run over all stream tokens
        for ttype, value in stream:
            # Yield token if we finished a statement and there's no whitespaces
            # It will count newline token as a non whitespace. In this context
            # whitespace ignores newlines.
            # why don't multi line comments also count?
            if self.consume_ws and ttype not in EOS_TTYPE:
                yield sql.Statement(self.tokens)

                # Reset filter and prepare to process next statement
                self._reset()

            # Change current split level (increase, decrease or remain equal)
            self.level += self._change_splitlevel(ttype, value)

            # Append the token to the current statement
            self.tokens.append(sql.Token(ttype, value))

            # Check if we get the end of a statement
            # Issue762: Allow GO (or "GO 2") as statement splitter.
            # When implementing a language toggle, it's not only to add
            # keywords it's also to change some rules, like this splitting
            # rule.
            # Issue809: Ignore semicolons inside BEGIN...END blocks, but handle
            # standalone BEGIN; as a transaction statement
            if ttype is T.Punctuation and value == ';':
                # If we just saw BEGIN; then this is a transaction BEGIN,
                # not a BEGIN...END block, so decrement depth
                if self._seen_begin:
                    self._begin_depth = max(0, self._begin_depth - 1)
                self._seen_begin = False
                # Split on semicolon if not inside a BEGIN...END block
                if self.level <= 0 and self._begin_depth == 0:
                    self.consume_ws = True
            elif ttype is T.Keyword and value.split()[0] == 'GO':
                self.consume_ws = True
            elif (ttype not in (T.Whitespace, T.Newline, T.Comment.Single,
                                T.Comment.Multiline)
                  and not (ttype is T.Keyword and value.upper() == 'BEGIN')):
                # Reset _seen_begin if we see a non-whitespace, non-comment
                # token but not for BEGIN itself (which just set the flag)
                self._seen_begin = False

        # Yield pending statement (if any)
        if self.tokens and not all(t.is_whitespace for t in self.tokens):
            yield sql.Statement(self.tokens)
