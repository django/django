# -*- coding: utf-8 -*-
"""
    pygments.lexers.javascript
    ~~~~~~~~~~~~~~~~~~~~~~~~~~

    Lexers for JavaScript and related languages.

    :copyright: Copyright 2006-2017 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from pygments.lexer import RegexLexer, include, bygroups, default, using, \
    this, words, combined
from pygments.token import Text, Comment, Operator, Keyword, Name, String, \
    Number, Punctuation, Other
from pygments.util import get_bool_opt, iteritems
import pygments.unistring as uni

__all__ = ['JavascriptLexer', 'KalLexer', 'LiveScriptLexer', 'DartLexer',
           'TypeScriptLexer', 'LassoLexer', 'ObjectiveJLexer',
           'CoffeeScriptLexer', 'MaskLexer', 'EarlGreyLexer', 'JuttleLexer']

JS_IDENT_START = ('(?:[$_' + uni.combine('Lu', 'Ll', 'Lt', 'Lm', 'Lo', 'Nl') +
                  ']|\\\\u[a-fA-F0-9]{4})')
JS_IDENT_PART = ('(?:[$' + uni.combine('Lu', 'Ll', 'Lt', 'Lm', 'Lo', 'Nl',
                                       'Mn', 'Mc', 'Nd', 'Pc') +
                 u'\u200c\u200d]|\\\\u[a-fA-F0-9]{4})')
JS_IDENT = JS_IDENT_START + '(?:' + JS_IDENT_PART + ')*'


class JavascriptLexer(RegexLexer):
    """
    For JavaScript source code.
    """

    name = 'JavaScript'
    aliases = ['js', 'javascript']
    filenames = ['*.js', '*.jsm']
    mimetypes = ['application/javascript', 'application/x-javascript',
                 'text/x-javascript', 'text/javascript']

    flags = re.DOTALL | re.UNICODE | re.MULTILINE

    tokens = {
        'commentsandwhitespace': [
            (r'\s+', Text),
            (r'<!--', Comment),
            (r'//.*?\n', Comment.Single),
            (r'/\*.*?\*/', Comment.Multiline)
        ],
        'slashstartsregex': [
            include('commentsandwhitespace'),
            (r'/(\\.|[^[/\\\n]|\[(\\.|[^\]\\\n])*])+/'
             r'([gimuy]+\b|\B)', String.Regex, '#pop'),
            (r'(?=/)', Text, ('#pop', 'badregex')),
            default('#pop')
        ],
        'badregex': [
            (r'\n', Text, '#pop')
        ],
        'root': [
            (r'\A#! ?/.*?\n', Comment.Hashbang),  # recognized by node.js
            (r'^(?=\s|/|<!--)', Text, 'slashstartsregex'),
            include('commentsandwhitespace'),
            (r'(\.\d+|[0-9]+\.[0-9]*)([eE][-+]?[0-9]+)?', Number.Float),
            (r'0[bB][01]+', Number.Bin),
            (r'0[oO][0-7]+', Number.Oct),
            (r'0[xX][0-9a-fA-F]+', Number.Hex),
            (r'[0-9]+', Number.Integer),
            (r'\.\.\.|=>', Punctuation),
            (r'\+\+|--|~|&&|\?|:|\|\||\\(?=\n)|'
             r'(<<|>>>?|==?|!=?|[-<>+*%&|^/])=?', Operator, 'slashstartsregex'),
            (r'[{(\[;,]', Punctuation, 'slashstartsregex'),
            (r'[})\].]', Punctuation),
            (r'(for|in|while|do|break|return|continue|switch|case|default|if|else|'
             r'throw|try|catch|finally|new|delete|typeof|instanceof|void|yield|'
             r'this|of)\b', Keyword, 'slashstartsregex'),
            (r'(var|let|with|function)\b', Keyword.Declaration, 'slashstartsregex'),
            (r'(abstract|boolean|byte|char|class|const|debugger|double|enum|export|'
             r'extends|final|float|goto|implements|import|int|interface|long|native|'
             r'package|private|protected|public|short|static|super|synchronized|throws|'
             r'transient|volatile)\b', Keyword.Reserved),
            (r'(true|false|null|NaN|Infinity|undefined)\b', Keyword.Constant),
            (r'(Array|Boolean|Date|Error|Function|Math|netscape|'
             r'Number|Object|Packages|RegExp|String|Promise|Proxy|sun|decodeURI|'
             r'decodeURIComponent|encodeURI|encodeURIComponent|'
             r'Error|eval|isFinite|isNaN|isSafeInteger|parseFloat|parseInt|'
             r'document|this|window)\b', Name.Builtin),
            (JS_IDENT, Name.Other),
            (r'"(\\\\|\\"|[^"])*"', String.Double),
            (r"'(\\\\|\\'|[^'])*'", String.Single),
            (r'`', String.Backtick, 'interp'),
        ],
        'interp': [
            (r'`', String.Backtick, '#pop'),
            (r'\\\\', String.Backtick),
            (r'\\`', String.Backtick),
            (r'\$\{', String.Interpol, 'interp-inside'),
            (r'\$', String.Backtick),
            (r'[^`\\$]+', String.Backtick),
        ],
        'interp-inside': [
            # TODO: should this include single-line comments and allow nesting strings?
            (r'\}', String.Interpol, '#pop'),
            include('root'),
        ],
        # (\\\\|\\`|[^`])*`', String.Backtick),
    }


class KalLexer(RegexLexer):
    """
    For `Kal`_ source code.

    .. _Kal: http://rzimmerman.github.io/kal


    .. versionadded:: 2.0
    """

    name = 'Kal'
    aliases = ['kal']
    filenames = ['*.kal']
    mimetypes = ['text/kal', 'application/kal']

    flags = re.DOTALL
    tokens = {
        'commentsandwhitespace': [
            (r'\s+', Text),
            (r'###[^#].*?###', Comment.Multiline),
            (r'#(?!##[^#]).*?\n', Comment.Single),
        ],
        'functiondef': [
            (r'[$a-zA-Z_][\w$]*\s*', Name.Function, '#pop'),
            include('commentsandwhitespace'),
        ],
        'classdef': [
            (r'\binherits\s+from\b', Keyword),
            (r'[$a-zA-Z_][\w$]*\s*\n', Name.Class, '#pop'),
            (r'[$a-zA-Z_][\w$]*\s*', Name.Class),
            include('commentsandwhitespace'),
        ],
        'listcomprehension': [
            (r'\]', Punctuation, '#pop'),
            (r'\b(property|value)\b', Keyword),
            include('root'),
        ],
        'waitfor': [
            (r'\n', Punctuation, '#pop'),
            (r'\bfrom\b', Keyword),
            include('root'),
        ],
        'root': [
            include('commentsandwhitespace'),
            (r'/(?! )(\\.|[^[/\\\n]|\[(\\.|[^\]\\\n])*])+/'
             r'([gim]+\b|\B)', String.Regex),
            (r'\?|:|_(?=\n)|==?|!=|-(?!>)|[<>+*/-]=?',
             Operator),
            (r'\b(and|or|isnt|is|not|but|bitwise|mod|\^|xor|exists|'
             r'doesnt\s+exist)\b', Operator.Word),
            (r'(?:\([^()]+\))?\s*>', Name.Function),
            (r'[{(]', Punctuation),
            (r'\[', Punctuation, 'listcomprehension'),
            (r'[})\].,]', Punctuation),
            (r'\b(function|method|task)\b', Keyword.Declaration, 'functiondef'),
            (r'\bclass\b', Keyword.Declaration, 'classdef'),
            (r'\b(safe\s+)?wait\s+for\b', Keyword, 'waitfor'),
            (r'\b(me|this)(\.[$a-zA-Z_][\w.$]*)?\b', Name.Variable.Instance),
            (r'(?<![.$])(for(\s+(parallel|series))?|in|of|while|until|'
             r'break|return|continue|'
             r'when|if|unless|else|otherwise|except\s+when|'
             r'throw|raise|fail\s+with|try|catch|finally|new|delete|'
             r'typeof|instanceof|super|run\s+in\s+parallel|'
             r'inherits\s+from)\b', Keyword),
            (r'(?<![.$])(true|false|yes|no|on|off|null|nothing|none|'
             r'NaN|Infinity|undefined)\b',
             Keyword.Constant),
            (r'(Array|Boolean|Date|Error|Function|Math|netscape|'
             r'Number|Object|Packages|RegExp|String|sun|decodeURI|'
             r'decodeURIComponent|encodeURI|encodeURIComponent|'
             r'eval|isFinite|isNaN|isSafeInteger|parseFloat|parseInt|document|'
             r'window|'
             r'print)\b',
             Name.Builtin),
            (r'[$a-zA-Z_][\w.$]*\s*(:|[+\-*/]?\=)?\b', Name.Variable),
            (r'[0-9][0-9]*\.[0-9]+([eE][0-9]+)?[fd]?', Number.Float),
            (r'0x[0-9a-fA-F]+', Number.Hex),
            (r'[0-9]+', Number.Integer),
            ('"""', String, 'tdqs'),
            ("'''", String, 'tsqs'),
            ('"', String, 'dqs'),
            ("'", String, 'sqs'),
        ],
        'strings': [
            (r'[^#\\\'"]+', String),
            # note that all kal strings are multi-line.
            # hashmarks, quotes and backslashes must be parsed one at a time
        ],
        'interpoling_string': [
            (r'\}', String.Interpol, "#pop"),
            include('root')
        ],
        'dqs': [
            (r'"', String, '#pop'),
            (r'\\.|\'', String),  # double-quoted string don't need ' escapes
            (r'#\{', String.Interpol, "interpoling_string"),
            include('strings')
        ],
        'sqs': [
            (r"'", String, '#pop'),
            (r'#|\\.|"', String),  # single quoted strings don't need " escapses
            include('strings')
        ],
        'tdqs': [
            (r'"""', String, '#pop'),
            (r'\\.|\'|"', String),  # no need to escape quotes in triple-string
            (r'#\{', String.Interpol, "interpoling_string"),
            include('strings'),
        ],
        'tsqs': [
            (r"'''", String, '#pop'),
            (r'#|\\.|\'|"', String),  # no need to escape quotes in triple-strings
            include('strings')
        ],
    }


class LiveScriptLexer(RegexLexer):
    """
    For `LiveScript`_ source code.

    .. _LiveScript: http://gkz.github.com/LiveScript/

    .. versionadded:: 1.6
    """

    name = 'LiveScript'
    aliases = ['live-script', 'livescript']
    filenames = ['*.ls']
    mimetypes = ['text/livescript']

    flags = re.DOTALL
    tokens = {
        'commentsandwhitespace': [
            (r'\s+', Text),
            (r'/\*.*?\*/', Comment.Multiline),
            (r'#.*?\n', Comment.Single),
        ],
        'multilineregex': [
            include('commentsandwhitespace'),
            (r'//([gim]+\b|\B)', String.Regex, '#pop'),
            (r'/', String.Regex),
            (r'[^/#]+', String.Regex)
        ],
        'slashstartsregex': [
            include('commentsandwhitespace'),
            (r'//', String.Regex, ('#pop', 'multilineregex')),
            (r'/(?! )(\\.|[^[/\\\n]|\[(\\.|[^\]\\\n])*])+/'
             r'([gim]+\b|\B)', String.Regex, '#pop'),
            default('#pop'),
        ],
        'root': [
            # this next expr leads to infinite loops root -> slashstartsregex
            # (r'^(?=\s|/|<!--)', Text, 'slashstartsregex'),
            include('commentsandwhitespace'),
            (r'(?:\([^()]+\))?[ ]*[~-]{1,2}>|'
             r'(?:\(?[^()\n]+\)?)?[ ]*<[~-]{1,2}', Name.Function),
            (r'\+\+|&&|(?<![.$])\b(?:and|x?or|is|isnt|not)\b|\?|:|=|'
             r'\|\||\\(?=\n)|(<<|>>>?|==?|!=?|'
             r'~(?!\~?>)|-(?!\-?>)|<(?!\[)|(?<!\])>|'
             r'[+*`%&|^/])=?',
             Operator, 'slashstartsregex'),
            (r'[{(\[;,]', Punctuation, 'slashstartsregex'),
            (r'[})\].]', Punctuation),
            (r'(?<![.$])(for|own|in|of|while|until|loop|break|'
             r'return|continue|switch|when|then|if|unless|else|'
             r'throw|try|catch|finally|new|delete|typeof|instanceof|super|'
             r'extends|this|class|by|const|var|to|til)\b', Keyword,
             'slashstartsregex'),
            (r'(?<![.$])(true|false|yes|no|on|off|'
             r'null|NaN|Infinity|undefined|void)\b',
             Keyword.Constant),
            (r'(Array|Boolean|Date|Error|Function|Math|netscape|'
             r'Number|Object|Packages|RegExp|String|sun|decodeURI|'
             r'decodeURIComponent|encodeURI|encodeURIComponent|'
             r'eval|isFinite|isNaN|parseFloat|parseInt|document|window)\b',
             Name.Builtin),
            (r'[$a-zA-Z_][\w.\-:$]*\s*[:=]\s', Name.Variable,
             'slashstartsregex'),
            (r'@[$a-zA-Z_][\w.\-:$]*\s*[:=]\s', Name.Variable.Instance,
             'slashstartsregex'),
            (r'@', Name.Other, 'slashstartsregex'),
            (r'@?[$a-zA-Z_][\w-]*', Name.Other, 'slashstartsregex'),
            (r'[0-9]+\.[0-9]+([eE][0-9]+)?[fd]?(?:[a-zA-Z_]+)?', Number.Float),
            (r'[0-9]+(~[0-9a-z]+)?(?:[a-zA-Z_]+)?', Number.Integer),
            ('"""', String, 'tdqs'),
            ("'''", String, 'tsqs'),
            ('"', String, 'dqs'),
            ("'", String, 'sqs'),
            (r'\\\S+', String),
            (r'<\[.*?\]>', String),
        ],
        'strings': [
            (r'[^#\\\'"]+', String),
            # note that all coffee script strings are multi-line.
            # hashmarks, quotes and backslashes must be parsed one at a time
        ],
        'interpoling_string': [
            (r'\}', String.Interpol, "#pop"),
            include('root')
        ],
        'dqs': [
            (r'"', String, '#pop'),
            (r'\\.|\'', String),  # double-quoted string don't need ' escapes
            (r'#\{', String.Interpol, "interpoling_string"),
            (r'#', String),
            include('strings')
        ],
        'sqs': [
            (r"'", String, '#pop'),
            (r'#|\\.|"', String),  # single quoted strings don't need " escapses
            include('strings')
        ],
        'tdqs': [
            (r'"""', String, '#pop'),
            (r'\\.|\'|"', String),  # no need to escape quotes in triple-string
            (r'#\{', String.Interpol, "interpoling_string"),
            (r'#', String),
            include('strings'),
        ],
        'tsqs': [
            (r"'''", String, '#pop'),
            (r'#|\\.|\'|"', String),  # no need to escape quotes in triple-strings
            include('strings')
        ],
    }


class DartLexer(RegexLexer):
    """
    For `Dart <http://dartlang.org/>`_ source code.

    .. versionadded:: 1.5
    """

    name = 'Dart'
    aliases = ['dart']
    filenames = ['*.dart']
    mimetypes = ['text/x-dart']

    flags = re.MULTILINE | re.DOTALL

    tokens = {
        'root': [
            include('string_literal'),
            (r'#!(.*?)$', Comment.Preproc),
            (r'\b(import|export)\b', Keyword, 'import_decl'),
            (r'\b(library|source|part of|part)\b', Keyword),
            (r'[^\S\n]+', Text),
            (r'//.*?\n', Comment.Single),
            (r'/\*.*?\*/', Comment.Multiline),
            (r'\b(class)\b(\s+)',
             bygroups(Keyword.Declaration, Text), 'class'),
            (r'\b(assert|break|case|catch|continue|default|do|else|finally|for|'
             r'if|in|is|new|return|super|switch|this|throw|try|while)\b',
             Keyword),
            (r'\b(abstract|async|await|const|extends|factory|final|get|'
             r'implements|native|operator|set|static|sync|typedef|var|with|'
             r'yield)\b', Keyword.Declaration),
            (r'\b(bool|double|dynamic|int|num|Object|String|void)\b', Keyword.Type),
            (r'\b(false|null|true)\b', Keyword.Constant),
            (r'[~!%^&*+=|?:<>/-]|as\b', Operator),
            (r'[a-zA-Z_$]\w*:', Name.Label),
            (r'[a-zA-Z_$]\w*', Name),
            (r'[(){}\[\],.;]', Punctuation),
            (r'0[xX][0-9a-fA-F]+', Number.Hex),
            # DIGIT+ (‘.’ DIGIT*)? EXPONENT?
            (r'\d+(\.\d*)?([eE][+-]?\d+)?', Number),
            (r'\.\d+([eE][+-]?\d+)?', Number),  # ‘.’ DIGIT+ EXPONENT?
            (r'\n', Text)
            # pseudo-keyword negate intentionally left out
        ],
        'class': [
            (r'[a-zA-Z_$]\w*', Name.Class, '#pop')
        ],
        'import_decl': [
            include('string_literal'),
            (r'\s+', Text),
            (r'\b(as|show|hide)\b', Keyword),
            (r'[a-zA-Z_$]\w*', Name),
            (r'\,', Punctuation),
            (r'\;', Punctuation, '#pop')
        ],
        'string_literal': [
            # Raw strings.
            (r'r"""([\w\W]*?)"""', String.Double),
            (r"r'''([\w\W]*?)'''", String.Single),
            (r'r"(.*?)"', String.Double),
            (r"r'(.*?)'", String.Single),
            # Normal Strings.
            (r'"""', String.Double, 'string_double_multiline'),
            (r"'''", String.Single, 'string_single_multiline'),
            (r'"', String.Double, 'string_double'),
            (r"'", String.Single, 'string_single')
        ],
        'string_common': [
            (r"\\(x[0-9A-Fa-f]{2}|u[0-9A-Fa-f]{4}|u\{[0-9A-Fa-f]*\}|[a-z'\"$\\])",
             String.Escape),
            (r'(\$)([a-zA-Z_]\w*)', bygroups(String.Interpol, Name)),
            (r'(\$\{)(.*?)(\})',
             bygroups(String.Interpol, using(this), String.Interpol))
        ],
        'string_double': [
            (r'"', String.Double, '#pop'),
            (r'[^"$\\\n]+', String.Double),
            include('string_common'),
            (r'\$+', String.Double)
        ],
        'string_double_multiline': [
            (r'"""', String.Double, '#pop'),
            (r'[^"$\\]+', String.Double),
            include('string_common'),
            (r'(\$|\")+', String.Double)
        ],
        'string_single': [
            (r"'", String.Single, '#pop'),
            (r"[^'$\\\n]+", String.Single),
            include('string_common'),
            (r'\$+', String.Single)
        ],
        'string_single_multiline': [
            (r"'''", String.Single, '#pop'),
            (r'[^\'$\\]+', String.Single),
            include('string_common'),
            (r'(\$|\')+', String.Single)
        ]
    }


class TypeScriptLexer(RegexLexer):
    """
    For `TypeScript <http://typescriptlang.org/>`_ source code.

    .. versionadded:: 1.6
    """

    name = 'TypeScript'
    aliases = ['ts', 'typescript']
    filenames = ['*.ts', '*.tsx']
    mimetypes = ['text/x-typescript']

    flags = re.DOTALL | re.MULTILINE

    tokens = {
        'commentsandwhitespace': [
            (r'\s+', Text),
            (r'<!--', Comment),
            (r'//.*?\n', Comment.Single),
            (r'/\*.*?\*/', Comment.Multiline)
        ],
        'slashstartsregex': [
            include('commentsandwhitespace'),
            (r'/(\\.|[^[/\\\n]|\[(\\.|[^\]\\\n])*])+/'
             r'([gim]+\b|\B)', String.Regex, '#pop'),
            (r'(?=/)', Text, ('#pop', 'badregex')),
            default('#pop')
        ],
        'badregex': [
            (r'\n', Text, '#pop')
        ],
        'root': [
            (r'^(?=\s|/|<!--)', Text, 'slashstartsregex'),
            include('commentsandwhitespace'),
            (r'\+\+|--|~|&&|\?|:|\|\||\\(?=\n)|'
             r'(<<|>>>?|==?|!=?|[-<>+*%&|^/])=?', Operator, 'slashstartsregex'),
            (r'[{(\[;,]', Punctuation, 'slashstartsregex'),
            (r'[})\].]', Punctuation),
            (r'(for|in|while|do|break|return|continue|switch|case|default|if|else|'
             r'throw|try|catch|finally|new|delete|typeof|instanceof|void|'
             r'this)\b', Keyword, 'slashstartsregex'),
            (r'(var|let|with|function)\b', Keyword.Declaration, 'slashstartsregex'),
            (r'(abstract|boolean|byte|char|class|const|debugger|double|enum|export|'
             r'extends|final|float|goto|implements|import|int|interface|long|native|'
             r'package|private|protected|public|short|static|super|synchronized|throws|'
             r'transient|volatile)\b', Keyword.Reserved),
            (r'(true|false|null|NaN|Infinity|undefined)\b', Keyword.Constant),
            (r'(Array|Boolean|Date|Error|Function|Math|netscape|'
             r'Number|Object|Packages|RegExp|String|sun|decodeURI|'
             r'decodeURIComponent|encodeURI|encodeURIComponent|'
             r'Error|eval|isFinite|isNaN|parseFloat|parseInt|document|this|'
             r'window)\b', Name.Builtin),
            # Match stuff like: module name {...}
            (r'\b(module)(\s*)(\s*[\w?.$][\w?.$]*)(\s*)',
             bygroups(Keyword.Reserved, Text, Name.Other, Text), 'slashstartsregex'),
            # Match variable type keywords
            (r'\b(string|bool|number)\b', Keyword.Type),
            # Match stuff like: constructor
            (r'\b(constructor|declare|interface|as|AS)\b', Keyword.Reserved),
            # Match stuff like: super(argument, list)
            (r'(super)(\s*)(\([\w,?.$\s]+\s*\))',
             bygroups(Keyword.Reserved, Text), 'slashstartsregex'),
            # Match stuff like: function() {...}
            (r'([a-zA-Z_?.$][\w?.$]*)\(\) \{', Name.Other, 'slashstartsregex'),
            # Match stuff like: (function: return type)
            (r'([\w?.$][\w?.$]*)(\s*:\s*)([\w?.$][\w?.$]*)',
             bygroups(Name.Other, Text, Keyword.Type)),
            (r'[$a-zA-Z_]\w*', Name.Other),
            (r'[0-9][0-9]*\.[0-9]+([eE][0-9]+)?[fd]?', Number.Float),
            (r'0x[0-9a-fA-F]+', Number.Hex),
            (r'[0-9]+', Number.Integer),
            (r'"(\\\\|\\"|[^"])*"', String.Double),
            (r"'(\\\\|\\'|[^'])*'", String.Single),
            (r'`', String.Backtick, 'interp'),
            # Match stuff like: Decorators
            (r'@\w+', Keyword.Declaration),
        ],

        # The 'interp*' rules match those in JavascriptLexer. Changes made
        # there should be reflected here as well.
        'interp': [
            (r'`', String.Backtick, '#pop'),
            (r'\\\\', String.Backtick),
            (r'\\`', String.Backtick),
            (r'\$\{', String.Interpol, 'interp-inside'),
            (r'\$', String.Backtick),
            (r'[^`\\$]+', String.Backtick),
        ],
        'interp-inside': [
            # TODO: should this include single-line comments and allow nesting strings?
            (r'\}', String.Interpol, '#pop'),
            include('root'),
        ],
    }

    def analyse_text(text):
        if re.search(r'^(import.+(from\s+)?["\']|'
                     r'(export\s*)?(interface|class|function)\s+)',
                     text, re.MULTILINE):
            return 1.0


class LassoLexer(RegexLexer):
    """
    For `Lasso <http://www.lassosoft.com/>`_ source code, covering both Lasso 9
    syntax and LassoScript for Lasso 8.6 and earlier. For Lasso embedded in
    HTML, use the `LassoHtmlLexer`.

    Additional options accepted:

    `builtinshighlighting`
        If given and ``True``, highlight builtin types, traits, methods, and
        members (default: ``True``).
    `requiredelimiters`
        If given and ``True``, only highlight code between delimiters as Lasso
        (default: ``False``).

    .. versionadded:: 1.6
    """

    name = 'Lasso'
    aliases = ['lasso', 'lassoscript']
    filenames = ['*.lasso', '*.lasso[89]']
    alias_filenames = ['*.incl', '*.inc', '*.las']
    mimetypes = ['text/x-lasso']
    flags = re.IGNORECASE | re.DOTALL | re.MULTILINE

    tokens = {
        'root': [
            (r'^#![ \S]+lasso9\b', Comment.Preproc, 'lasso'),
            (r'(?=\[|<)', Other, 'delimiters'),
            (r'\s+', Other),
            default(('delimiters', 'lassofile')),
        ],
        'delimiters': [
            (r'\[no_square_brackets\]', Comment.Preproc, 'nosquarebrackets'),
            (r'\[noprocess\]', Comment.Preproc, 'noprocess'),
            (r'\[', Comment.Preproc, 'squarebrackets'),
            (r'<\?(lasso(script)?|=)', Comment.Preproc, 'anglebrackets'),
            (r'<(!--.*?-->)?', Other),
            (r'[^[<]+', Other),
        ],
        'nosquarebrackets': [
            (r'\[noprocess\]', Comment.Preproc, 'noprocess'),
            (r'\[', Other),
            (r'<\?(lasso(script)?|=)', Comment.Preproc, 'anglebrackets'),
            (r'<(!--.*?-->)?', Other),
            (r'[^[<]+', Other),
        ],
        'noprocess': [
            (r'\[/noprocess\]', Comment.Preproc, '#pop'),
            (r'\[', Other),
            (r'[^[]', Other),
        ],
        'squarebrackets': [
            (r'\]', Comment.Preproc, '#pop'),
            include('lasso'),
        ],
        'anglebrackets': [
            (r'\?>', Comment.Preproc, '#pop'),
            include('lasso'),
        ],
        'lassofile': [
            (r'\]|\?>', Comment.Preproc, '#pop'),
            include('lasso'),
        ],
        'whitespacecomments': [
            (r'\s+', Text),
            (r'//.*?\n', Comment.Single),
            (r'/\*\*!.*?\*/', String.Doc),
            (r'/\*.*?\*/', Comment.Multiline),
        ],
        'lasso': [
            # whitespace/comments
            include('whitespacecomments'),

            # literals
            (r'\d*\.\d+(e[+-]?\d+)?', Number.Float),
            (r'0x[\da-f]+', Number.Hex),
            (r'\d+', Number.Integer),
            (r'(infinity|NaN)\b', Number),
            (r"'", String.Single, 'singlestring'),
            (r'"', String.Double, 'doublestring'),
            (r'`[^`]*`', String.Backtick),

            # names
            (r'\$[a-z_][\w.]*', Name.Variable),
            (r'#([a-z_][\w.]*|\d+\b)', Name.Variable.Instance),
            (r"(\.\s*)('[a-z_][\w.]*')",
                bygroups(Name.Builtin.Pseudo, Name.Variable.Class)),
            (r"(self)(\s*->\s*)('[a-z_][\w.]*')",
                bygroups(Name.Builtin.Pseudo, Operator, Name.Variable.Class)),
            (r'(\.\.?\s*)([a-z_][\w.]*(=(?!=))?)',
                bygroups(Name.Builtin.Pseudo, Name.Other.Member)),
            (r'(->\\?\s*|&\s*)([a-z_][\w.]*(=(?!=))?)',
                bygroups(Operator, Name.Other.Member)),
            (r'(?<!->)(self|inherited|currentcapture|givenblock)\b',
                Name.Builtin.Pseudo),
            (r'-(?!infinity)[a-z_][\w.]*', Name.Attribute),
            (r'::\s*[a-z_][\w.]*', Name.Label),
            (r'(error_(code|msg)_\w+|Error_AddError|Error_ColumnRestriction|'
             r'Error_DatabaseConnectionUnavailable|Error_DatabaseTimeout|'
             r'Error_DeleteError|Error_FieldRestriction|Error_FileNotFound|'
             r'Error_InvalidDatabase|Error_InvalidPassword|'
             r'Error_InvalidUsername|Error_ModuleNotFound|'
             r'Error_NoError|Error_NoPermission|Error_OutOfMemory|'
             r'Error_ReqColumnMissing|Error_ReqFieldMissing|'
             r'Error_RequiredColumnMissing|Error_RequiredFieldMissing|'
             r'Error_UpdateError)\b', Name.Exception),

            # definitions
            (r'(define)(\s+)([a-z_][\w.]*)(\s*=>\s*)(type|trait|thread)\b',
                bygroups(Keyword.Declaration, Text, Name.Class, Operator, Keyword)),
            (r'(define)(\s+)([a-z_][\w.]*)(\s*->\s*)([a-z_][\w.]*=?|[-+*/%])',
                bygroups(Keyword.Declaration, Text, Name.Class, Operator,
                         Name.Function), 'signature'),
            (r'(define)(\s+)([a-z_][\w.]*)',
                bygroups(Keyword.Declaration, Text, Name.Function), 'signature'),
            (r'(public|protected|private|provide)(\s+)(([a-z_][\w.]*=?|[-+*/%])'
             r'(?=\s*\())', bygroups(Keyword, Text, Name.Function),
                'signature'),
            (r'(public|protected|private|provide)(\s+)([a-z_][\w.]*)',
                bygroups(Keyword, Text, Name.Function)),

            # keywords
            (r'(true|false|none|minimal|full|all|void)\b', Keyword.Constant),
            (r'(local|var|variable|global|data(?=\s))\b', Keyword.Declaration),
            (r'(array|date|decimal|duration|integer|map|pair|string|tag|xml|'
             r'null|boolean|bytes|keyword|list|locale|queue|set|stack|'
             r'staticarray)\b', Keyword.Type),
            (r'([a-z_][\w.]*)(\s+)(in)\b', bygroups(Name, Text, Keyword)),
            (r'(let|into)(\s+)([a-z_][\w.]*)', bygroups(Keyword, Text, Name)),
            (r'require\b', Keyword, 'requiresection'),
            (r'(/?)(Namespace_Using)\b', bygroups(Punctuation, Keyword.Namespace)),
            (r'(/?)(Cache|Database_Names|Database_SchemaNames|'
             r'Database_TableNames|Define_Tag|Define_Type|Email_Batch|'
             r'Encode_Set|HTML_Comment|Handle|Handle_Error|Header|If|Inline|'
             r'Iterate|LJAX_Target|Link|Link_CurrentAction|Link_CurrentGroup|'
             r'Link_CurrentRecord|Link_Detail|Link_FirstGroup|Link_FirstRecord|'
             r'Link_LastGroup|Link_LastRecord|Link_NextGroup|Link_NextRecord|'
             r'Link_PrevGroup|Link_PrevRecord|Log|Loop|Output_None|Portal|'
             r'Private|Protect|Records|Referer|Referrer|Repeating|ResultSet|'
             r'Rows|Search_Args|Search_Arguments|Select|Sort_Args|'
             r'Sort_Arguments|Thread_Atomic|Value_List|While|Abort|Case|Else|'
             r'Fail_If|Fail_IfNot|Fail|If_Empty|If_False|If_Null|If_True|'
             r'Loop_Abort|Loop_Continue|Loop_Count|Params|Params_Up|Return|'
             r'Return_Value|Run_Children|SOAP_DefineTag|SOAP_LastRequest|'
             r'SOAP_LastResponse|Tag_Name|ascending|average|by|define|'
             r'descending|do|equals|frozen|group|handle_failure|import|in|into|'
             r'join|let|match|max|min|on|order|parent|protected|provide|public|'
             r'require|returnhome|skip|split_thread|sum|take|thread|to|trait|'
             r'type|where|with|yield|yieldhome)\b',
                bygroups(Punctuation, Keyword)),

            # other
            (r',', Punctuation, 'commamember'),
            (r'(and|or|not)\b', Operator.Word),
            (r'([a-z_][\w.]*)(\s*::\s*[a-z_][\w.]*)?(\s*=(?!=))',
                bygroups(Name, Name.Label, Operator)),
            (r'(/?)([\w.]+)', bygroups(Punctuation, Name.Other)),
            (r'(=)(n?bw|n?ew|n?cn|lte?|gte?|n?eq|n?rx|ft)\b',
                bygroups(Operator, Operator.Word)),
            (r':=|[-+*/%=<>&|!?\\]+', Operator),
            (r'[{}():;,@^]', Punctuation),
        ],
        'singlestring': [
            (r"'", String.Single, '#pop'),
            (r"[^'\\]+", String.Single),
            include('escape'),
            (r"\\", String.Single),
        ],
        'doublestring': [
            (r'"', String.Double, '#pop'),
            (r'[^"\\]+', String.Double),
            include('escape'),
            (r'\\', String.Double),
        ],
        'escape': [
            (r'\\(U[\da-f]{8}|u[\da-f]{4}|x[\da-f]{1,2}|[0-7]{1,3}|:[^:\n\r]+:|'
             r'[abefnrtv?"\'\\]|$)', String.Escape),
        ],
        'signature': [
            (r'=>', Operator, '#pop'),
            (r'\)', Punctuation, '#pop'),
            (r'[(,]', Punctuation, 'parameter'),
            include('lasso'),
        ],
        'parameter': [
            (r'\)', Punctuation, '#pop'),
            (r'-?[a-z_][\w.]*', Name.Attribute, '#pop'),
            (r'\.\.\.', Name.Builtin.Pseudo),
            include('lasso'),
        ],
        'requiresection': [
            (r'(([a-z_][\w.]*=?|[-+*/%])(?=\s*\())', Name, 'requiresignature'),
            (r'(([a-z_][\w.]*=?|[-+*/%])(?=(\s*::\s*[\w.]+)?\s*,))', Name),
            (r'[a-z_][\w.]*=?|[-+*/%]', Name, '#pop'),
            (r'::\s*[a-z_][\w.]*', Name.Label),
            (r',', Punctuation),
            include('whitespacecomments'),
        ],
        'requiresignature': [
            (r'(\)(?=(\s*::\s*[\w.]+)?\s*,))', Punctuation, '#pop'),
            (r'\)', Punctuation, '#pop:2'),
            (r'-?[a-z_][\w.]*', Name.Attribute),
            (r'::\s*[a-z_][\w.]*', Name.Label),
            (r'\.\.\.', Name.Builtin.Pseudo),
            (r'[(,]', Punctuation),
            include('whitespacecomments'),
        ],
        'commamember': [
            (r'(([a-z_][\w.]*=?|[-+*/%])'
             r'(?=\s*(\(([^()]*\([^()]*\))*[^)]*\)\s*)?(::[\w.\s]+)?=>))',
                Name.Function, 'signature'),
            include('whitespacecomments'),
            default('#pop'),
        ],
    }

    def __init__(self, **options):
        self.builtinshighlighting = get_bool_opt(
            options, 'builtinshighlighting', True)
        self.requiredelimiters = get_bool_opt(
            options, 'requiredelimiters', False)

        self._builtins = set()
        self._members = set()
        if self.builtinshighlighting:
            from pygments.lexers._lasso_builtins import BUILTINS, MEMBERS
            for key, value in iteritems(BUILTINS):
                self._builtins.update(value)
            for key, value in iteritems(MEMBERS):
                self._members.update(value)
        RegexLexer.__init__(self, **options)

    def get_tokens_unprocessed(self, text):
        stack = ['root']
        if self.requiredelimiters:
            stack.append('delimiters')
        for index, token, value in \
                RegexLexer.get_tokens_unprocessed(self, text, stack):
            if (token is Name.Other and value.lower() in self._builtins or
                    token is Name.Other.Member and
                    value.lower().rstrip('=') in self._members):
                yield index, Name.Builtin, value
                continue
            yield index, token, value

    def analyse_text(text):
        rv = 0.0
        if 'bin/lasso9' in text:
            rv += 0.8
        if re.search(r'<\?lasso', text, re.I):
            rv += 0.4
        if re.search(r'local\(', text, re.I):
            rv += 0.4
        return rv


class ObjectiveJLexer(RegexLexer):
    """
    For Objective-J source code with preprocessor directives.

    .. versionadded:: 1.3
    """

    name = 'Objective-J'
    aliases = ['objective-j', 'objectivej', 'obj-j', 'objj']
    filenames = ['*.j']
    mimetypes = ['text/x-objective-j']

    #: optional Comment or Whitespace
    _ws = r'(?:\s|//.*?\n|/[*].*?[*]/)*'

    flags = re.DOTALL | re.MULTILINE

    tokens = {
        'root': [
            include('whitespace'),

            # function definition
            (r'^(' + _ws + r'[+-]' + _ws + r')([(a-zA-Z_].*?[^(])(' + _ws + r'\{)',
             bygroups(using(this), using(this, state='function_signature'),
                      using(this))),

            # class definition
            (r'(@interface|@implementation)(\s+)', bygroups(Keyword, Text),
             'classname'),
            (r'(@class|@protocol)(\s*)', bygroups(Keyword, Text),
             'forward_classname'),
            (r'(\s*)(@end)(\s*)', bygroups(Text, Keyword, Text)),

            include('statements'),
            ('[{()}]', Punctuation),
            (';', Punctuation),
        ],
        'whitespace': [
            (r'(@import)(\s+)("(?:\\\\|\\"|[^"])*")',
             bygroups(Comment.Preproc, Text, String.Double)),
            (r'(@import)(\s+)(<(?:\\\\|\\>|[^>])*>)',
             bygroups(Comment.Preproc, Text, String.Double)),
            (r'(#(?:include|import))(\s+)("(?:\\\\|\\"|[^"])*")',
             bygroups(Comment.Preproc, Text, String.Double)),
            (r'(#(?:include|import))(\s+)(<(?:\\\\|\\>|[^>])*>)',
             bygroups(Comment.Preproc, Text, String.Double)),

            (r'#if\s+0', Comment.Preproc, 'if0'),
            (r'#', Comment.Preproc, 'macro'),

            (r'\n', Text),
            (r'\s+', Text),
            (r'\\\n', Text),  # line continuation
            (r'//(\n|(.|\n)*?[^\\]\n)', Comment.Single),
            (r'/(\\\n)?[*](.|\n)*?[*](\\\n)?/', Comment.Multiline),
            (r'<!--', Comment),
        ],
        'slashstartsregex': [
            include('whitespace'),
            (r'/(\\.|[^[/\\\n]|\[(\\.|[^\]\\\n])*])+/'
             r'([gim]+\b|\B)', String.Regex, '#pop'),
            (r'(?=/)', Text, ('#pop', 'badregex')),
            default('#pop'),
        ],
        'badregex': [
            (r'\n', Text, '#pop'),
        ],
        'statements': [
            (r'(L|@)?"', String, 'string'),
            (r"(L|@)?'(\\.|\\[0-7]{1,3}|\\x[a-fA-F0-9]{1,2}|[^\\\'\n])'",
             String.Char),
            (r'"(\\\\|\\"|[^"])*"', String.Double),
            (r"'(\\\\|\\'|[^'])*'", String.Single),
            (r'(\d+\.\d*|\.\d+|\d+)[eE][+-]?\d+[lL]?', Number.Float),
            (r'(\d+\.\d*|\.\d+|\d+[fF])[fF]?', Number.Float),
            (r'0x[0-9a-fA-F]+[Ll]?', Number.Hex),
            (r'0[0-7]+[Ll]?', Number.Oct),
            (r'\d+[Ll]?', Number.Integer),

            (r'^(?=\s|/|<!--)', Text, 'slashstartsregex'),

            (r'\+\+|--|~|&&|\?|:|\|\||\\(?=\n)|'
             r'(<<|>>>?|==?|!=?|[-<>+*%&|^/])=?',
             Operator, 'slashstartsregex'),
            (r'[{(\[;,]', Punctuation, 'slashstartsregex'),
            (r'[})\].]', Punctuation),

            (r'(for|in|while|do|break|return|continue|switch|case|default|if|'
             r'else|throw|try|catch|finally|new|delete|typeof|instanceof|void|'
             r'prototype|__proto__)\b', Keyword, 'slashstartsregex'),

            (r'(var|with|function)\b', Keyword.Declaration, 'slashstartsregex'),

            (r'(@selector|@private|@protected|@public|@encode|'
             r'@synchronized|@try|@throw|@catch|@finally|@end|@property|'
             r'@synthesize|@dynamic|@for|@accessors|new)\b', Keyword),

            (r'(int|long|float|short|double|char|unsigned|signed|void|'
             r'id|BOOL|bool|boolean|IBOutlet|IBAction|SEL|@outlet|@action)\b',
             Keyword.Type),

            (r'(self|super)\b', Name.Builtin),

            (r'(TRUE|YES|FALSE|NO|Nil|nil|NULL)\b', Keyword.Constant),
            (r'(true|false|null|NaN|Infinity|undefined)\b', Keyword.Constant),
            (r'(ABS|ASIN|ACOS|ATAN|ATAN2|SIN|COS|TAN|EXP|POW|CEIL|FLOOR|ROUND|'
             r'MIN|MAX|RAND|SQRT|E|LN2|LN10|LOG2E|LOG10E|PI|PI2|PI_2|SQRT1_2|'
             r'SQRT2)\b', Keyword.Constant),

            (r'(Array|Boolean|Date|Error|Function|Math|netscape|'
             r'Number|Object|Packages|RegExp|String|sun|decodeURI|'
             r'decodeURIComponent|encodeURI|encodeURIComponent|'
             r'Error|eval|isFinite|isNaN|parseFloat|parseInt|document|this|'
             r'window)\b', Name.Builtin),

            (r'([$a-zA-Z_]\w*)(' + _ws + r')(?=\()',
             bygroups(Name.Function, using(this))),

            (r'[$a-zA-Z_]\w*', Name),
        ],
        'classname': [
            # interface definition that inherits
            (r'([a-zA-Z_]\w*)(' + _ws + r':' + _ws +
             r')([a-zA-Z_]\w*)?',
             bygroups(Name.Class, using(this), Name.Class), '#pop'),
            # interface definition for a category
            (r'([a-zA-Z_]\w*)(' + _ws + r'\()([a-zA-Z_]\w*)(\))',
             bygroups(Name.Class, using(this), Name.Label, Text), '#pop'),
            # simple interface / implementation
            (r'([a-zA-Z_]\w*)', Name.Class, '#pop'),
        ],
        'forward_classname': [
            (r'([a-zA-Z_]\w*)(\s*,\s*)',
             bygroups(Name.Class, Text), '#push'),
            (r'([a-zA-Z_]\w*)(\s*;?)',
             bygroups(Name.Class, Text), '#pop'),
        ],
        'function_signature': [
            include('whitespace'),

            # start of a selector w/ parameters
            (r'(\(' + _ws + r')'                # open paren
             r'([a-zA-Z_]\w+)'                  # return type
             r'(' + _ws + r'\)' + _ws + r')'    # close paren
             r'([$a-zA-Z_]\w+' + _ws + r':)',   # function name
             bygroups(using(this), Keyword.Type, using(this),
                      Name.Function), 'function_parameters'),

            # no-param function
            (r'(\(' + _ws + r')'                # open paren
             r'([a-zA-Z_]\w+)'                  # return type
             r'(' + _ws + r'\)' + _ws + r')'    # close paren
             r'([$a-zA-Z_]\w+)',                # function name
             bygroups(using(this), Keyword.Type, using(this),
                      Name.Function), "#pop"),

            # no return type given, start of a selector w/ parameters
            (r'([$a-zA-Z_]\w+' + _ws + r':)',   # function name
             bygroups(Name.Function), 'function_parameters'),

            # no return type given, no-param function
            (r'([$a-zA-Z_]\w+)',                # function name
             bygroups(Name.Function), "#pop"),

            default('#pop'),
        ],
        'function_parameters': [
            include('whitespace'),

            # parameters
            (r'(\(' + _ws + ')'                 # open paren
             r'([^)]+)'                        # type
             r'(' + _ws + r'\)' + _ws + r')'    # close paren
             r'([$a-zA-Z_]\w+)',      # param name
             bygroups(using(this), Keyword.Type, using(this), Text)),

            # one piece of a selector name
            (r'([$a-zA-Z_]\w+' + _ws + r':)',   # function name
             Name.Function),

            # smallest possible selector piece
            (r'(:)', Name.Function),

            # var args
            (r'(,' + _ws + r'\.\.\.)', using(this)),

            # param name
            (r'([$a-zA-Z_]\w+)', Text),
        ],
        'expression': [
            (r'([$a-zA-Z_]\w*)(\()', bygroups(Name.Function,
                                              Punctuation)),
            (r'(\))', Punctuation, "#pop"),
        ],
        'string': [
            (r'"', String, '#pop'),
            (r'\\([\\abfnrtv"\']|x[a-fA-F0-9]{2,4}|[0-7]{1,3})', String.Escape),
            (r'[^\\"\n]+', String),  # all other characters
            (r'\\\n', String),  # line continuation
            (r'\\', String),  # stray backslash
        ],
        'macro': [
            (r'[^/\n]+', Comment.Preproc),
            (r'/[*](.|\n)*?[*]/', Comment.Multiline),
            (r'//.*?\n', Comment.Single, '#pop'),
            (r'/', Comment.Preproc),
            (r'(?<=\\)\n', Comment.Preproc),
            (r'\n', Comment.Preproc, '#pop'),
        ],
        'if0': [
            (r'^\s*#if.*?(?<!\\)\n', Comment.Preproc, '#push'),
            (r'^\s*#endif.*?(?<!\\)\n', Comment.Preproc, '#pop'),
            (r'.*?\n', Comment),
        ]
    }

    def analyse_text(text):
        if re.search(r'^\s*@import\s+[<"]', text, re.MULTILINE):
            # special directive found in most Objective-J files
            return True
        return False


class CoffeeScriptLexer(RegexLexer):
    """
    For `CoffeeScript`_ source code.

    .. _CoffeeScript: http://coffeescript.org

    .. versionadded:: 1.3
    """

    name = 'CoffeeScript'
    aliases = ['coffee-script', 'coffeescript', 'coffee']
    filenames = ['*.coffee']
    mimetypes = ['text/coffeescript']


    _operator_re = (
        r'\+\+|~|&&|\band\b|\bor\b|\bis\b|\bisnt\b|\bnot\b|\?|:|'
        r'\|\||\\(?=\n)|'
        r'(<<|>>>?|==?(?!>)|!=?|=(?!>)|-(?!>)|[<>+*`%&\|\^/])=?')

    flags = re.DOTALL
    tokens = {
        'commentsandwhitespace': [
            (r'\s+', Text),
            (r'###[^#].*?###', Comment.Multiline),
            (r'#(?!##[^#]).*?\n', Comment.Single),
        ],
        'multilineregex': [
            (r'[^/#]+', String.Regex),
            (r'///([gim]+\b|\B)', String.Regex, '#pop'),
            (r'#\{', String.Interpol, 'interpoling_string'),
            (r'[/#]', String.Regex),
        ],
        'slashstartsregex': [
            include('commentsandwhitespace'),
            (r'///', String.Regex, ('#pop', 'multilineregex')),
            (r'/(?! )(\\.|[^[/\\\n]|\[(\\.|[^\]\\\n])*])+/'
             r'([gim]+\b|\B)', String.Regex, '#pop'),
            # This isn't really guarding against mishighlighting well-formed
            # code, just the ability to infinite-loop between root and
            # slashstartsregex.
            (r'/', Operator),
            default('#pop'),
        ],
        'root': [
            include('commentsandwhitespace'),
            (r'^(?=\s|/)', Text, 'slashstartsregex'),
            (_operator_re, Operator, 'slashstartsregex'),
            (r'(?:\([^()]*\))?\s*[=-]>', Name.Function, 'slashstartsregex'),
            (r'[{(\[;,]', Punctuation, 'slashstartsregex'),
            (r'[})\].]', Punctuation),
            (r'(?<![.$])(for|own|in|of|while|until|'
             r'loop|break|return|continue|'
             r'switch|when|then|if|unless|else|'
             r'throw|try|catch|finally|new|delete|typeof|instanceof|super|'
             r'extends|this|class|by)\b', Keyword, 'slashstartsregex'),
            (r'(?<![.$])(true|false|yes|no|on|off|null|'
             r'NaN|Infinity|undefined)\b',
             Keyword.Constant),
            (r'(Array|Boolean|Date|Error|Function|Math|netscape|'
             r'Number|Object|Packages|RegExp|String|sun|decodeURI|'
             r'decodeURIComponent|encodeURI|encodeURIComponent|'
             r'eval|isFinite|isNaN|parseFloat|parseInt|document|window)\b',
             Name.Builtin),
            (r'[$a-zA-Z_][\w.:$]*\s*[:=]\s', Name.Variable,
             'slashstartsregex'),
            (r'@[$a-zA-Z_][\w.:$]*\s*[:=]\s', Name.Variable.Instance,
             'slashstartsregex'),
            (r'@', Name.Other, 'slashstartsregex'),
            (r'@?[$a-zA-Z_][\w$]*', Name.Other),
            (r'[0-9][0-9]*\.[0-9]+([eE][0-9]+)?[fd]?', Number.Float),
            (r'0x[0-9a-fA-F]+', Number.Hex),
            (r'[0-9]+', Number.Integer),
            ('"""', String, 'tdqs'),
            ("'''", String, 'tsqs'),
            ('"', String, 'dqs'),
            ("'", String, 'sqs'),
        ],
        'strings': [
            (r'[^#\\\'"]+', String),
            # note that all coffee script strings are multi-line.
            # hashmarks, quotes and backslashes must be parsed one at a time
        ],
        'interpoling_string': [
            (r'\}', String.Interpol, "#pop"),
            include('root')
        ],
        'dqs': [
            (r'"', String, '#pop'),
            (r'\\.|\'', String),  # double-quoted string don't need ' escapes
            (r'#\{', String.Interpol, "interpoling_string"),
            (r'#', String),
            include('strings')
        ],
        'sqs': [
            (r"'", String, '#pop'),
            (r'#|\\.|"', String),  # single quoted strings don't need " escapses
            include('strings')
        ],
        'tdqs': [
            (r'"""', String, '#pop'),
            (r'\\.|\'|"', String),  # no need to escape quotes in triple-string
            (r'#\{', String.Interpol, "interpoling_string"),
            (r'#', String),
            include('strings'),
        ],
        'tsqs': [
            (r"'''", String, '#pop'),
            (r'#|\\.|\'|"', String),  # no need to escape quotes in triple-strings
            include('strings')
        ],
    }


class MaskLexer(RegexLexer):
    """
    For `Mask <http://github.com/atmajs/MaskJS>`__ markup.

    .. versionadded:: 2.0
    """
    name = 'Mask'
    aliases = ['mask']
    filenames = ['*.mask']
    mimetypes = ['text/x-mask']

    flags = re.MULTILINE | re.IGNORECASE | re.DOTALL
    tokens = {
        'root': [
            (r'\s+', Text),
            (r'//.*?\n', Comment.Single),
            (r'/\*.*?\*/', Comment.Multiline),
            (r'[{};>]', Punctuation),
            (r"'''", String, 'string-trpl-single'),
            (r'"""', String, 'string-trpl-double'),
            (r"'", String, 'string-single'),
            (r'"', String, 'string-double'),
            (r'([\w-]+)', Name.Tag, 'node'),
            (r'([^.#;{>\s]+)', Name.Class, 'node'),
            (r'(#[\w-]+)', Name.Function, 'node'),
            (r'(\.[\w-]+)', Name.Variable.Class, 'node')
        ],
        'string-base': [
            (r'\\.', String.Escape),
            (r'~\[', String.Interpol, 'interpolation'),
            (r'.', String.Single),
        ],
        'string-single': [
            (r"'", String.Single, '#pop'),
            include('string-base')
        ],
        'string-double': [
            (r'"', String.Single, '#pop'),
            include('string-base')
        ],
        'string-trpl-single': [
            (r"'''", String.Single, '#pop'),
            include('string-base')
        ],
        'string-trpl-double': [
            (r'"""', String.Single, '#pop'),
            include('string-base')
        ],
        'interpolation': [
            (r'\]', String.Interpol, '#pop'),
            (r'\s*:', String.Interpol, 'expression'),
            (r'\s*\w+:', Name.Other),
            (r'[^\]]+', String.Interpol)
        ],
        'expression': [
            (r'[^\]]+', using(JavascriptLexer), '#pop')
        ],
        'node': [
            (r'\s+', Text),
            (r'\.', Name.Variable.Class, 'node-class'),
            (r'\#', Name.Function, 'node-id'),
            (r'style[ \t]*=', Name.Attribute, 'node-attr-style-value'),
            (r'[\w:-]+[ \t]*=', Name.Attribute, 'node-attr-value'),
            (r'[\w:-]+', Name.Attribute),
            (r'[>{;]', Punctuation, '#pop')
        ],
        'node-class': [
            (r'[\w-]+', Name.Variable.Class),
            (r'~\[', String.Interpol, 'interpolation'),
            default('#pop')
        ],
        'node-id': [
            (r'[\w-]+', Name.Function),
            (r'~\[', String.Interpol, 'interpolation'),
            default('#pop')
        ],
        'node-attr-value': [
            (r'\s+', Text),
            (r'\w+', Name.Variable, '#pop'),
            (r"'", String, 'string-single-pop2'),
            (r'"', String, 'string-double-pop2'),
            default('#pop')
        ],
        'node-attr-style-value': [
            (r'\s+', Text),
            (r"'", String.Single, 'css-single-end'),
            (r'"', String.Single, 'css-double-end'),
            include('node-attr-value')
        ],
        'css-base': [
            (r'\s+', Text),
            (r";", Punctuation),
            (r"[\w\-]+\s*:", Name.Builtin)
        ],
        'css-single-end': [
            include('css-base'),
            (r"'", String.Single, '#pop:2'),
            (r"[^;']+", Name.Entity)
        ],
        'css-double-end': [
            include('css-base'),
            (r'"', String.Single, '#pop:2'),
            (r'[^;"]+', Name.Entity)
        ],
        'string-single-pop2': [
            (r"'", String.Single, '#pop:2'),
            include('string-base')
        ],
        'string-double-pop2': [
            (r'"', String.Single, '#pop:2'),
            include('string-base')
        ],
    }


class EarlGreyLexer(RegexLexer):
    """
    For `Earl-Grey`_ source code.

    .. _Earl-Grey: https://breuleux.github.io/earl-grey/

    .. versionadded: 2.1
    """

    name = 'Earl Grey'
    aliases = ['earl-grey', 'earlgrey', 'eg']
    filenames = ['*.eg']
    mimetypes = ['text/x-earl-grey']

    tokens = {
        'root': [
            (r'\n', Text),
            include('control'),
            (r'[^\S\n]+', Text),
            (r';;.*\n', Comment),
            (r'[\[\]{}:(),;]', Punctuation),
            (r'\\\n', Text),
            (r'\\', Text),
            include('errors'),
            (words((
                'with', 'where', 'when', 'and', 'not', 'or', 'in',
                'as', 'of', 'is'),
                prefix=r'(?<=\s|\[)', suffix=r'(?![\w$\-])'),
             Operator.Word),
            (r'[*@]?->', Name.Function),
            (r'[+\-*/~^<>%&|?!@#.]*=', Operator.Word),
            (r'\.{2,3}', Operator.Word),  # Range Operator
            (r'([+*/~^<>&|?!]+)|([#\-](?=\s))|@@+(?=\s)|=+', Operator),
            (r'(?<![\w$\-])(var|let)(?:[^\w$])', Keyword.Declaration),
            include('keywords'),
            include('builtins'),
            include('assignment'),
            (r'''(?x)
                (?:()([a-zA-Z$_](?:[\w$\-]*[\w$])?)|
                   (?<=[\s{\[(])(\.)([a-zA-Z$_](?:[\w$\-]*[\w$])?))
                (?=.*%)''',
             bygroups(Punctuation, Name.Tag, Punctuation, Name.Class.Start), 'dbs'),
            (r'[rR]?`', String.Backtick, 'bt'),
            (r'[rR]?```', String.Backtick, 'tbt'),
            (r'(?<=[\s\[{(,;])\.([a-zA-Z$_](?:[\w$\-]*[\w$])?)'
             r'(?=[\s\]}),;])', String.Symbol),
            include('nested'),
            (r'(?:[rR]|[rR]\.[gmi]{1,3})?"', String, combined('stringescape', 'dqs')),
            (r'(?:[rR]|[rR]\.[gmi]{1,3})?\'', String, combined('stringescape', 'sqs')),
            (r'"""', String, combined('stringescape', 'tdqs')),
            include('tuple'),
            include('import_paths'),
            include('name'),
            include('numbers'),
        ],
        'dbs': [
            (r'(\.)([a-zA-Z$_](?:[\w$\-]*[\w$])?)(?=[.\[\s])',
             bygroups(Punctuation, Name.Class.DBS)),
            (r'(\[)([\^#][a-zA-Z$_](?:[\w$\-]*[\w$])?)(\])',
             bygroups(Punctuation, Name.Entity.DBS, Punctuation)),
            (r'\s+', Text),
            (r'%', Operator.DBS, '#pop'),
        ],
        'import_paths': [
            (r'(?<=[\s:;,])(\.{1,3}(?:[\w\-]*/)*)(\w(?:[\w\-]*\w)*)(?=[\s;,])',
             bygroups(Text.Whitespace, Text)),
        ],
        'assignment': [
            (r'(\.)?([a-zA-Z$_](?:[\w$\-]*[\w$])?)'
             r'(?=\s+[+\-*/~^<>%&|?!@#.]*\=\s)',
             bygroups(Punctuation, Name.Variable))
        ],
        'errors': [
            (words(('Error', 'TypeError', 'ReferenceError'),
                   prefix=r'(?<![\w\-$.])', suffix=r'(?![\w\-$.])'),
             Name.Exception),
            (r'''(?x)
                (?<![\w$])
                E\.[\w$](?:[\w$\-]*[\w$])?
                (?:\.[\w$](?:[\w$\-]*[\w$])?)*
                (?=[({\[?!\s])''',
             Name.Exception),
        ],
        'control': [
            (r'''(?x)
                ([a-zA-Z$_](?:[\w$-]*[\w$])?)
                (?!\n)\s+
                (?!and|as|each\*|each|in|is|mod|of|or|when|where|with)
                (?=(?:[+\-*/~^<>%&|?!@#.])?[a-zA-Z$_](?:[\w$-]*[\w$])?)''',
             Keyword.Control),
            (r'([a-zA-Z$_](?:[\w$-]*[\w$])?)(?!\n)\s+(?=[\'"\d{\[(])',
             Keyword.Control),
            (r'''(?x)
                (?:
                    (?<=[%=])|
                    (?<=[=\-]>)|
                    (?<=with|each|with)|
                    (?<=each\*|where)
                )(\s+)
                ([a-zA-Z$_](?:[\w$-]*[\w$])?)(:)''',
             bygroups(Text, Keyword.Control, Punctuation)),
            (r'''(?x)
                (?<![+\-*/~^<>%&|?!@#.])(\s+)
                ([a-zA-Z$_](?:[\w$-]*[\w$])?)(:)''',
             bygroups(Text, Keyword.Control, Punctuation)),
        ],
        'nested': [
            (r'''(?x)
                (?<=[\w$\]})])(\.)
                ([a-zA-Z$_](?:[\w$-]*[\w$])?)
                (?=\s+with(?:\s|\n))''',
             bygroups(Punctuation, Name.Function)),
            (r'''(?x)
                (?<!\s)(\.)
                ([a-zA-Z$_](?:[\w$-]*[\w$])?)
                (?=[}\]).,;:\s])''',
             bygroups(Punctuation, Name.Field)),
            (r'''(?x)
                (?<=[\w$\]})])(\.)
                ([a-zA-Z$_](?:[\w$-]*[\w$])?)
                (?=[\[{(:])''',
             bygroups(Punctuation, Name.Function)),
        ],
        'keywords': [
            (words((
                'each', 'each*', 'mod', 'await', 'break', 'chain',
                'continue', 'elif', 'expr-value', 'if', 'match',
                'return', 'yield', 'pass', 'else', 'require', 'var',
                'let', 'async', 'method', 'gen'),
                prefix=r'(?<![\w\-$.])', suffix=r'(?![\w\-$.])'),
             Keyword.Pseudo),
            (words(('this', 'self', '@'),
                   prefix=r'(?<![\w\-$.])', suffix=r'(?![\w\-$])'),
             Keyword.Constant),
            (words((
                'Function', 'Object', 'Array', 'String', 'Number',
                'Boolean', 'ErrorFactory', 'ENode', 'Promise'),
                prefix=r'(?<![\w\-$.])', suffix=r'(?![\w\-$])'),
             Keyword.Type),
        ],
        'builtins': [
            (words((
                'send', 'object', 'keys', 'items', 'enumerate', 'zip',
                'product', 'neighbours', 'predicate', 'equal',
                'nequal', 'contains', 'repr', 'clone', 'range',
                'getChecker', 'get-checker', 'getProperty', 'get-property',
                'getProjector', 'get-projector', 'consume', 'take',
                'promisify', 'spawn', 'constructor'),
                prefix=r'(?<![\w\-#.])', suffix=r'(?![\w\-.])'),
             Name.Builtin),
            (words((
                'true', 'false', 'null', 'undefined'),
                prefix=r'(?<![\w\-$.])', suffix=r'(?![\w\-$.])'),
             Name.Constant),
        ],
        'name': [
            (r'@([a-zA-Z$_](?:[\w$-]*[\w$])?)', Name.Variable.Instance),
            (r'([a-zA-Z$_](?:[\w$-]*[\w$])?)(\+\+|\-\-)?',
             bygroups(Name.Symbol, Operator.Word))
        ],
        'tuple': [
            (r'#[a-zA-Z_][\w\-]*(?=[\s{(,;])', Name.Namespace)
        ],
        'interpoling_string': [
            (r'\}', String.Interpol, '#pop'),
            include('root')
        ],
        'stringescape': [
            (r'\\([\\abfnrtv"\']|\n|N\{.*?\}|u[a-fA-F0-9]{4}|'
             r'U[a-fA-F0-9]{8}|x[a-fA-F0-9]{2}|[0-7]{1,3})', String.Escape)
        ],
        'strings': [
            (r'[^\\\'"]', String),
            (r'[\'"\\]', String),
            (r'\n', String)  # All strings are multiline in EG
        ],
        'dqs': [
            (r'"', String, '#pop'),
            (r'\\\\|\\"|\\\n', String.Escape),
            include('strings')
        ],
        'sqs': [
            (r"'", String, '#pop'),
            (r"\\\\|\\'|\\\n", String.Escape),
            (r'\{', String.Interpol, 'interpoling_string'),
            include('strings')
        ],
        'tdqs': [
            (r'"""', String, '#pop'),
            include('strings'),
        ],
        'bt': [
            (r'`', String.Backtick, '#pop'),
            (r'(?<!`)\n', String.Backtick),
            (r'\^=?', String.Escape),
            (r'.+', String.Backtick),
        ],
        'tbt': [
            (r'```', String.Backtick, '#pop'),
            (r'\n', String.Backtick),
            (r'\^=?', String.Escape),
            (r'[^`]+', String.Backtick),
        ],
        'numbers': [
            (r'\d+\.(?!\.)\d*([eE][+-]?[0-9]+)?', Number.Float),
            (r'\d+[eE][+-]?[0-9]+', Number.Float),
            (r'8r[0-7]+', Number.Oct),
            (r'2r[01]+', Number.Bin),
            (r'16r[a-fA-F0-9]+', Number.Hex),
            (r'([3-79]|[12][0-9]|3[0-6])r[a-zA-Z\d]+(\.[a-zA-Z\d]+)?', Number.Radix),
            (r'\d+', Number.Integer)
        ],
    }

class JuttleLexer(RegexLexer):
    """
    For `Juttle`_ source code.

    .. _Juttle: https://github.com/juttle/juttle

    """

    name = 'Juttle'
    aliases = ['juttle', 'juttle']
    filenames = ['*.juttle']
    mimetypes = ['application/juttle', 'application/x-juttle',
                 'text/x-juttle', 'text/juttle']

    flags = re.DOTALL | re.UNICODE | re.MULTILINE

    tokens = {
        'commentsandwhitespace': [
            (r'\s+', Text),
            (r'//.*?\n', Comment.Single),
            (r'/\*.*?\*/', Comment.Multiline)
        ],
        'slashstartsregex': [
            include('commentsandwhitespace'),
            (r'/(\\.|[^[/\\\n]|\[(\\.|[^\]\\\n])*])+/'
             r'([gim]+\b|\B)', String.Regex, '#pop'),
            (r'(?=/)', Text, ('#pop', 'badregex')),
            default('#pop')
        ],
        'badregex': [
            (r'\n', Text, '#pop')
        ],
        'root': [
            (r'^(?=\s|/)', Text, 'slashstartsregex'),
            include('commentsandwhitespace'),
            (r':\d{2}:\d{2}:\d{2}(\.\d*)?:', String.Moment),
            (r':(now|beginning|end|forever|yesterday|today|tomorrow|'
             r'(\d+(\.\d*)?|\.\d+)(ms|[smhdwMy])?):', String.Moment),
            (r':\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2}(\.\d*)?)?'
             r'(Z|[+-]\d{2}:\d{2}|[+-]\d{4})?:', String.Moment),
            (r':((\d+(\.\d*)?|\.\d+)[ ]+)?(millisecond|second|minute|hour|day|week|month|year)[s]?'
             r'(([ ]+and[ ]+(\d+[ ]+)?(millisecond|second|minute|hour|day|week|month|year)[s]?)'
             r'|[ ]+(ago|from[ ]+now))*:', String.Moment),
            (r'\+\+|--|~|&&|\?|:|\|\||\\(?=\n)|'
             r'(==?|!=?|[-<>+*%&|^/])=?', Operator, 'slashstartsregex'),
            (r'[{(\[;,]', Punctuation, 'slashstartsregex'),
            (r'[})\].]', Punctuation),
            (r'(import|return|continue|if|else)\b', Keyword, 'slashstartsregex'),
            (r'(var|const|function|reducer|sub|input)\b', Keyword.Declaration, 'slashstartsregex'),
            (r'(batch|emit|filter|head|join|keep|pace|pass|put|read|reduce|remove|'
             r'sequence|skip|sort|split|tail|unbatch|uniq|view|write)\b', Keyword.Reserved),
            (r'(true|false|null|Infinity)\b', Keyword.Constant),
            (r'(Array|Date|Juttle|Math|Number|Object|RegExp|String)\b', Name.Builtin),
            (JS_IDENT, Name.Other),
            (r'[0-9][0-9]*\.[0-9]+([eE][0-9]+)?[fd]?', Number.Float),
            (r'[0-9]+', Number.Integer),
            (r'"(\\\\|\\"|[^"])*"', String.Double),
            (r"'(\\\\|\\'|[^'])*'", String.Single)
        ]

    }
