# -*- coding: utf-8 -*-
#
# Copyright (C) 2016 Andi Albrecht, albrecht.andi@gmail.com
#
# This module is part of python-sqlparse and is released under
# the BSD License: https://opensource.org/licenses/BSD-3-Clause

import re

from sqlparse import sql, tokens as T
from sqlparse.compat import text_type


# FIXME: Doesn't work
class RightMarginFilter(object):
    keep_together = (
        # sql.TypeCast, sql.Identifier, sql.Alias,
    )

    def __init__(self, width=79):
        self.width = width
        self.line = ''

    def _process(self, group, stream):
        for token in stream:
            if token.is_whitespace and '\n' in token.value:
                if token.value.endswith('\n'):
                    self.line = ''
                else:
                    self.line = token.value.splitlines()[-1]
            elif token.is_group and type(token) not in self.keep_together:
                token.tokens = self._process(token, token.tokens)
            else:
                val = text_type(token)
                if len(self.line) + len(val) > self.width:
                    match = re.search(r'^ +', self.line)
                    if match is not None:
                        indent = match.group()
                    else:
                        indent = ''
                    yield sql.Token(T.Whitespace, '\n{0}'.format(indent))
                    self.line = indent
                self.line += val
            yield token

    def process(self, group):
        # return
        # group.tokens = self._process(group, group.tokens)
        raise NotImplementedError
