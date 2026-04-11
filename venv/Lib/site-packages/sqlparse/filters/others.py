#
# Copyright (C) 2009-2020 the sqlparse authors and contributors
# <see AUTHORS file>
#
# This module is part of python-sqlparse and is released under
# the BSD License: https://opensource.org/licenses/BSD-3-Clause

import re

from sqlparse import sql, tokens as T
from sqlparse.utils import split_unquoted_newlines


class StripCommentsFilter:

    @staticmethod
    def _process(tlist):
        def get_next_comment(idx=-1):
            # TODO(andi) Comment types should be unified, see related issue38
            return tlist.token_next_by(i=sql.Comment, t=T.Comment, idx=idx)

        def _get_insert_token(token):
            """Returns either a whitespace or the line breaks from token."""
            # See issue484 why line breaks should be preserved.
            # Note: The actual value for a line break is replaced by \n
            # in SerializerUnicode which will be executed in the
            # postprocessing state.
            m = re.search(r'([\r\n]+) *$', token.value)
            if m is not None:
                return sql.Token(T.Whitespace.Newline, m.groups()[0])
            else:
                return sql.Token(T.Whitespace, ' ')

        sql_hints = (T.Comment.Multiline.Hint, T.Comment.Single.Hint)
        tidx, token = get_next_comment()
        while token:
            # skipping token remove if token is a SQL-Hint. issue262
            is_sql_hint = False
            if token.ttype in sql_hints:
                is_sql_hint = True
            elif isinstance(token, sql.Comment):
                comment_tokens = token.tokens
                if len(comment_tokens) > 0:
                    if comment_tokens[0].ttype in sql_hints:
                        is_sql_hint = True

            if is_sql_hint:
                # using current index as start index to search next token for
                # preventing infinite loop in cases when token type is a
                # "SQL-Hint" and has to be skipped
                tidx, token = get_next_comment(idx=tidx)
                continue

            pidx, prev_ = tlist.token_prev(tidx, skip_ws=False)
            nidx, next_ = tlist.token_next(tidx, skip_ws=False)
            # Replace by whitespace if prev and next exist and if they're not
            # whitespaces. This doesn't apply if prev or next is a parenthesis.
            if (
                prev_ is None or next_ is None
                or prev_.is_whitespace or prev_.match(T.Punctuation, '(')
                or next_.is_whitespace or next_.match(T.Punctuation, ')')
            ):
                # Insert a whitespace to ensure the following SQL produces
                # a valid SQL (see #425).
                if prev_ is not None and not prev_.match(T.Punctuation, '('):
                    tlist.tokens.insert(tidx, _get_insert_token(token))
                tlist.tokens.remove(token)
                tidx -= 1
            else:
                tlist.tokens[tidx] = _get_insert_token(token)

            # using current index as start index to search next token for
            # preventing infinite loop in cases when token type is a
            # "SQL-Hint" and has to be skipped
            tidx, token = get_next_comment(idx=tidx)

    def process(self, stmt):
        [self.process(sgroup) for sgroup in stmt.get_sublists()]
        StripCommentsFilter._process(stmt)
        return stmt


class StripWhitespaceFilter:
    def _stripws(self, tlist):
        func_name = f'_stripws_{type(tlist).__name__}'
        func = getattr(self, func_name.lower(), self._stripws_default)
        func(tlist)

    @staticmethod
    def _stripws_default(tlist):
        last_was_ws = False
        is_first_char = True
        for token in tlist.tokens:
            if token.is_whitespace:
                token.value = '' if last_was_ws or is_first_char else ' '
            last_was_ws = token.is_whitespace
            is_first_char = False

    def _stripws_identifierlist(self, tlist):
        # Removes newlines before commas, see issue140
        last_nl = None
        for token in list(tlist.tokens):
            if last_nl and token.ttype is T.Punctuation and token.value == ',':
                tlist.tokens.remove(last_nl)
            last_nl = token if token.is_whitespace else None

            # next_ = tlist.token_next(token, skip_ws=False)
            # if (next_ and not next_.is_whitespace and
            #             token.ttype is T.Punctuation and token.value == ','):
            #     tlist.insert_after(token, sql.Token(T.Whitespace, ' '))
        return self._stripws_default(tlist)

    def _stripws_parenthesis(self, tlist):
        while tlist.tokens[1].is_whitespace:
            tlist.tokens.pop(1)
        while tlist.tokens[-2].is_whitespace:
            tlist.tokens.pop(-2)
        if tlist.tokens[-2].is_group:
            # save to remove the last whitespace
            while tlist.tokens[-2].tokens[-1].is_whitespace:
                tlist.tokens[-2].tokens.pop(-1)
        self._stripws_default(tlist)

    def process(self, stmt, depth=0):
        [self.process(sgroup, depth + 1) for sgroup in stmt.get_sublists()]
        self._stripws(stmt)
        if depth == 0 and stmt.tokens and stmt.tokens[-1].is_whitespace:
            stmt.tokens.pop(-1)
        return stmt


class SpacesAroundOperatorsFilter:
    @staticmethod
    def _process(tlist):

        ttypes = (T.Operator, T.Comparison)
        tidx, token = tlist.token_next_by(t=ttypes)
        while token:
            nidx, next_ = tlist.token_next(tidx, skip_ws=False)
            if next_ and next_.ttype != T.Whitespace:
                tlist.insert_after(tidx, sql.Token(T.Whitespace, ' '))

            pidx, prev_ = tlist.token_prev(tidx, skip_ws=False)
            if prev_ and prev_.ttype != T.Whitespace:
                tlist.insert_before(tidx, sql.Token(T.Whitespace, ' '))
                tidx += 1  # has to shift since token inserted before it

            # assert tlist.token_index(token) == tidx
            tidx, token = tlist.token_next_by(t=ttypes, idx=tidx)

    def process(self, stmt):
        [self.process(sgroup) for sgroup in stmt.get_sublists()]
        SpacesAroundOperatorsFilter._process(stmt)
        return stmt


class StripTrailingSemicolonFilter:

    def process(self, stmt):
        while stmt.tokens and (stmt.tokens[-1].is_whitespace
                               or stmt.tokens[-1].value == ';'):
            stmt.tokens.pop()
        return stmt


# ---------------------------
# postprocess

class SerializerUnicode:
    @staticmethod
    def process(stmt):
        lines = split_unquoted_newlines(stmt)
        return '\n'.join(line.rstrip() for line in lines)
