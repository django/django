# $Id: pygmentsformatter.py 10136 2025-05-20 15:48:27Z milde $
# Author: Dave Kuhlman <dkuhlman@rexx.com>
# Copyright: This module has been placed in the public domain.

"""Additional support for Pygments formatter."""

from __future__ import annotations

import pygments
import pygments.formatter


class OdtPygmentsFormatter(pygments.formatter.Formatter):
    def __init__(self, rststyle_function, escape_function) -> None:
        pygments.formatter.Formatter.__init__(self)
        self.rststyle_function = rststyle_function
        self.escape_function = escape_function

    def rststyle(self, name, parameters=()):
        return self.rststyle_function(name, parameters)


class OdtPygmentsProgFormatter(OdtPygmentsFormatter):
    def format(self, tokensource, outfile) -> None:
        tokenclass = pygments.token.Token
        for ttype, value in tokensource:
            value = self.escape_function(value)
            if ttype == tokenclass.Keyword:
                s2 = self.rststyle('codeblock-keyword')
                s1 = '<text:span text:style-name="%s">%s</text:span>' % \
                    (s2, value, )
            elif ttype == tokenclass.Literal.String:
                s2 = self.rststyle('codeblock-string')
                s1 = '<text:span text:style-name="%s">%s</text:span>' % \
                    (s2, value, )
            elif ttype in (
                    tokenclass.Literal.Number.Integer,
                    tokenclass.Literal.Number.Integer.Long,
                    tokenclass.Literal.Number.Float,
                    tokenclass.Literal.Number.Hex,
                    tokenclass.Literal.Number.Oct,
                    tokenclass.Literal.Number,
                    ):
                s2 = self.rststyle('codeblock-number')
                s1 = '<text:span text:style-name="%s">%s</text:span>' % \
                    (s2, value, )
            elif ttype == tokenclass.Operator:
                s2 = self.rststyle('codeblock-operator')
                s1 = '<text:span text:style-name="%s">%s</text:span>' % \
                    (s2, value, )
            elif ttype == tokenclass.Comment:
                s2 = self.rststyle('codeblock-comment')
                s1 = '<text:span text:style-name="%s">%s</text:span>' % \
                    (s2, value, )
            elif ttype == tokenclass.Name.Class:
                s2 = self.rststyle('codeblock-classname')
                s1 = '<text:span text:style-name="%s">%s</text:span>' % \
                    (s2, value, )
            elif ttype == tokenclass.Name.Function:
                s2 = self.rststyle('codeblock-functionname')
                s1 = '<text:span text:style-name="%s">%s</text:span>' % \
                    (s2, value, )
            elif ttype == tokenclass.Name:
                s2 = self.rststyle('codeblock-name')
                s1 = '<text:span text:style-name="%s">%s</text:span>' % \
                    (s2, value, )
            else:
                s1 = value
            outfile.write(s1)


class OdtPygmentsLaTeXFormatter(OdtPygmentsFormatter):
    def format(self, tokensource, outfile) -> None:
        tokenclass = pygments.token.Token
        for ttype, value in tokensource:
            value = self.escape_function(value)
            if ttype == tokenclass.Keyword:
                s2 = self.rststyle('codeblock-keyword')
                s1 = '<text:span text:style-name="%s">%s</text:span>' % \
                    (s2, value, )
            elif ttype in (tokenclass.Literal.String,
                           tokenclass.Literal.String.Backtick,
                           ):
                s2 = self.rststyle('codeblock-string')
                s1 = '<text:span text:style-name="%s">%s</text:span>' % \
                    (s2, value, )
            elif ttype == tokenclass.Name.Attribute:
                s2 = self.rststyle('codeblock-operator')
                s1 = '<text:span text:style-name="%s">%s</text:span>' % \
                    (s2, value, )
            elif ttype == tokenclass.Comment:
                if value[-1] == '\n':
                    s2 = self.rststyle('codeblock-comment')
                    s1 = '<text:span text:style-name="%s">%s</text:span>\n' % \
                        (s2, value[:-1], )
                else:
                    s2 = self.rststyle('codeblock-comment')
                    s1 = '<text:span text:style-name="%s">%s</text:span>' % \
                        (s2, value, )
            elif ttype == tokenclass.Name.Builtin:
                s2 = self.rststyle('codeblock-name')
                s1 = '<text:span text:style-name="%s">%s</text:span>' % \
                    (s2, value, )
            else:
                s1 = value
            outfile.write(s1)
