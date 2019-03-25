# -*- coding: utf-8 -*-
"""
    pygments.lexers.markup
    ~~~~~~~~~~~~~~~~~~~~~~

    Lexers for non-HTML markup languages.

    :copyright: Copyright 2006-2017 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from pygments.lexers.html import HtmlLexer, XmlLexer
from pygments.lexers.javascript import JavascriptLexer
from pygments.lexers.css import CssLexer

from pygments.lexer import RegexLexer, DelegatingLexer, include, bygroups, \
    using, this, do_insertions, default, words
from pygments.token import Text, Comment, Operator, Keyword, Name, String, \
    Number, Punctuation, Generic, Other
from pygments.util import get_bool_opt, ClassNotFound

__all__ = ['BBCodeLexer', 'MoinWikiLexer', 'RstLexer', 'TexLexer', 'GroffLexer',
           'MozPreprocHashLexer', 'MozPreprocPercentLexer',
           'MozPreprocXulLexer', 'MozPreprocJavascriptLexer',
           'MozPreprocCssLexer', 'MarkdownLexer']


class BBCodeLexer(RegexLexer):
    """
    A lexer that highlights BBCode(-like) syntax.

    .. versionadded:: 0.6
    """

    name = 'BBCode'
    aliases = ['bbcode']
    mimetypes = ['text/x-bbcode']

    tokens = {
        'root': [
            (r'[^[]+', Text),
            # tag/end tag begin
            (r'\[/?\w+', Keyword, 'tag'),
            # stray bracket
            (r'\[', Text),
        ],
        'tag': [
            (r'\s+', Text),
            # attribute with value
            (r'(\w+)(=)("?[^\s"\]]+"?)',
             bygroups(Name.Attribute, Operator, String)),
            # tag argument (a la [color=green])
            (r'(=)("?[^\s"\]]+"?)',
             bygroups(Operator, String)),
            # tag end
            (r'\]', Keyword, '#pop'),
        ],
    }


class MoinWikiLexer(RegexLexer):
    """
    For MoinMoin (and Trac) Wiki markup.

    .. versionadded:: 0.7
    """

    name = 'MoinMoin/Trac Wiki markup'
    aliases = ['trac-wiki', 'moin']
    filenames = []
    mimetypes = ['text/x-trac-wiki']
    flags = re.MULTILINE | re.IGNORECASE

    tokens = {
        'root': [
            (r'^#.*$', Comment),
            (r'(!)(\S+)', bygroups(Keyword, Text)),  # Ignore-next
            # Titles
            (r'^(=+)([^=]+)(=+)(\s*#.+)?$',
             bygroups(Generic.Heading, using(this), Generic.Heading, String)),
            # Literal code blocks, with optional shebang
            (r'(\{\{\{)(\n#!.+)?', bygroups(Name.Builtin, Name.Namespace), 'codeblock'),
            (r'(\'\'\'?|\|\||`|__|~~|\^|,,|::)', Comment),  # Formatting
            # Lists
            (r'^( +)([.*-])( )', bygroups(Text, Name.Builtin, Text)),
            (r'^( +)([a-z]{1,5}\.)( )', bygroups(Text, Name.Builtin, Text)),
            # Other Formatting
            (r'\[\[\w+.*?\]\]', Keyword),  # Macro
            (r'(\[[^\s\]]+)(\s+[^\]]+?)?(\])',
             bygroups(Keyword, String, Keyword)),  # Link
            (r'^----+$', Keyword),  # Horizontal rules
            (r'[^\n\'\[{!_~^,|]+', Text),
            (r'\n', Text),
            (r'.', Text),
        ],
        'codeblock': [
            (r'\}\}\}', Name.Builtin, '#pop'),
            # these blocks are allowed to be nested in Trac, but not MoinMoin
            (r'\{\{\{', Text, '#push'),
            (r'[^{}]+', Comment.Preproc),  # slurp boring text
            (r'.', Comment.Preproc),  # allow loose { or }
        ],
    }


class RstLexer(RegexLexer):
    """
    For `reStructuredText <http://docutils.sf.net/rst.html>`_ markup.

    .. versionadded:: 0.7

    Additional options accepted:

    `handlecodeblocks`
        Highlight the contents of ``.. sourcecode:: language``,
        ``.. code:: language`` and ``.. code-block:: language``
        directives with a lexer for the given language (default:
        ``True``).

        .. versionadded:: 0.8
    """
    name = 'reStructuredText'
    aliases = ['rst', 'rest', 'restructuredtext']
    filenames = ['*.rst', '*.rest']
    mimetypes = ["text/x-rst", "text/prs.fallenstein.rst"]
    flags = re.MULTILINE

    def _handle_sourcecode(self, match):
        from pygments.lexers import get_lexer_by_name

        # section header
        yield match.start(1), Punctuation, match.group(1)
        yield match.start(2), Text, match.group(2)
        yield match.start(3), Operator.Word, match.group(3)
        yield match.start(4), Punctuation, match.group(4)
        yield match.start(5), Text, match.group(5)
        yield match.start(6), Keyword, match.group(6)
        yield match.start(7), Text, match.group(7)

        # lookup lexer if wanted and existing
        lexer = None
        if self.handlecodeblocks:
            try:
                lexer = get_lexer_by_name(match.group(6).strip())
            except ClassNotFound:
                pass
        indention = match.group(8)
        indention_size = len(indention)
        code = (indention + match.group(9) + match.group(10) + match.group(11))

        # no lexer for this language. handle it like it was a code block
        if lexer is None:
            yield match.start(8), String, code
            return

        # highlight the lines with the lexer.
        ins = []
        codelines = code.splitlines(True)
        code = ''
        for line in codelines:
            if len(line) > indention_size:
                ins.append((len(code), [(0, Text, line[:indention_size])]))
                code += line[indention_size:]
            else:
                code += line
        for item in do_insertions(ins, lexer.get_tokens_unprocessed(code)):
            yield item

    # from docutils.parsers.rst.states
    closers = u'\'")]}>\u2019\u201d\xbb!?'
    unicode_delimiters = u'\u2010\u2011\u2012\u2013\u2014\u00a0'
    end_string_suffix = (r'((?=$)|(?=[-/:.,; \n\x00%s%s]))'
                         % (re.escape(unicode_delimiters),
                            re.escape(closers)))

    tokens = {
        'root': [
            # Heading with overline
            (r'^(=+|-+|`+|:+|\.+|\'+|"+|~+|\^+|_+|\*+|\++|#+)([ \t]*\n)'
             r'(.+)(\n)(\1)(\n)',
             bygroups(Generic.Heading, Text, Generic.Heading,
                      Text, Generic.Heading, Text)),
            # Plain heading
            (r'^(\S.*)(\n)(={3,}|-{3,}|`{3,}|:{3,}|\.{3,}|\'{3,}|"{3,}|'
             r'~{3,}|\^{3,}|_{3,}|\*{3,}|\+{3,}|#{3,})(\n)',
             bygroups(Generic.Heading, Text, Generic.Heading, Text)),
            # Bulleted lists
            (r'^(\s*)([-*+])( .+\n(?:\1  .+\n)*)',
             bygroups(Text, Number, using(this, state='inline'))),
            # Numbered lists
            (r'^(\s*)([0-9#ivxlcmIVXLCM]+\.)( .+\n(?:\1  .+\n)*)',
             bygroups(Text, Number, using(this, state='inline'))),
            (r'^(\s*)(\(?[0-9#ivxlcmIVXLCM]+\))( .+\n(?:\1  .+\n)*)',
             bygroups(Text, Number, using(this, state='inline'))),
            # Numbered, but keep words at BOL from becoming lists
            (r'^(\s*)([A-Z]+\.)( .+\n(?:\1  .+\n)+)',
             bygroups(Text, Number, using(this, state='inline'))),
            (r'^(\s*)(\(?[A-Za-z]+\))( .+\n(?:\1  .+\n)+)',
             bygroups(Text, Number, using(this, state='inline'))),
            # Line blocks
            (r'^(\s*)(\|)( .+\n(?:\|  .+\n)*)',
             bygroups(Text, Operator, using(this, state='inline'))),
            # Sourcecode directives
            (r'^( *\.\.)(\s*)((?:source)?code(?:-block)?)(::)([ \t]*)([^\n]+)'
             r'(\n[ \t]*\n)([ \t]+)(.*)(\n)((?:(?:\8.*|)\n)+)',
             _handle_sourcecode),
            # A directive
            (r'^( *\.\.)(\s*)([\w:-]+?)(::)(?:([ \t]*)(.*))',
             bygroups(Punctuation, Text, Operator.Word, Punctuation, Text,
                      using(this, state='inline'))),
            # A reference target
            (r'^( *\.\.)(\s*)(_(?:[^:\\]|\\.)+:)(.*?)$',
             bygroups(Punctuation, Text, Name.Tag, using(this, state='inline'))),
            # A footnote/citation target
            (r'^( *\.\.)(\s*)(\[.+\])(.*?)$',
             bygroups(Punctuation, Text, Name.Tag, using(this, state='inline'))),
            # A substitution def
            (r'^( *\.\.)(\s*)(\|.+\|)(\s*)([\w:-]+?)(::)(?:([ \t]*)(.*))',
             bygroups(Punctuation, Text, Name.Tag, Text, Operator.Word,
                      Punctuation, Text, using(this, state='inline'))),
            # Comments
            (r'^ *\.\..*(\n( +.*\n|\n)+)?', Comment.Preproc),
            # Field list
            (r'^( *)(:[a-zA-Z-]+:)(\s*)$', bygroups(Text, Name.Class, Text)),
            (r'^( *)(:.*?:)([ \t]+)(.*?)$',
             bygroups(Text, Name.Class, Text, Name.Function)),
            # Definition list
            (r'^(\S.*(?<!::)\n)((?:(?: +.*)\n)+)',
             bygroups(using(this, state='inline'), using(this, state='inline'))),
            # Code blocks
            (r'(::)(\n[ \t]*\n)([ \t]+)(.*)(\n)((?:(?:\3.*|)\n)+)',
             bygroups(String.Escape, Text, String, String, Text, String)),
            include('inline'),
        ],
        'inline': [
            (r'\\.', Text),  # escape
            (r'``', String, 'literal'),  # code
            (r'(`.+?)(<.+?>)(`__?)',  # reference with inline target
             bygroups(String, String.Interpol, String)),
            (r'`.+?`__?', String),  # reference
            (r'(`.+?`)(:[a-zA-Z0-9:-]+?:)?',
             bygroups(Name.Variable, Name.Attribute)),  # role
            (r'(:[a-zA-Z0-9:-]+?:)(`.+?`)',
             bygroups(Name.Attribute, Name.Variable)),  # role (content first)
            (r'\*\*.+?\*\*', Generic.Strong),  # Strong emphasis
            (r'\*.+?\*', Generic.Emph),  # Emphasis
            (r'\[.*?\]_', String),  # Footnote or citation
            (r'<.+?>', Name.Tag),   # Hyperlink
            (r'[^\\\n\[*`:]+', Text),
            (r'.', Text),
        ],
        'literal': [
            (r'[^`]+', String),
            (r'``' + end_string_suffix, String, '#pop'),
            (r'`', String),
        ]
    }

    def __init__(self, **options):
        self.handlecodeblocks = get_bool_opt(options, 'handlecodeblocks', True)
        RegexLexer.__init__(self, **options)

    def analyse_text(text):
        if text[:2] == '..' and text[2:3] != '.':
            return 0.3
        p1 = text.find("\n")
        p2 = text.find("\n", p1 + 1)
        if (p2 > -1 and              # has two lines
                p1 * 2 + 1 == p2 and     # they are the same length
                text[p1+1] in '-=' and   # the next line both starts and ends with
                text[p1+1] == text[p2-1]):  # ...a sufficiently high header
            return 0.5


class TexLexer(RegexLexer):
    """
    Lexer for the TeX and LaTeX typesetting languages.
    """

    name = 'TeX'
    aliases = ['tex', 'latex']
    filenames = ['*.tex', '*.aux', '*.toc']
    mimetypes = ['text/x-tex', 'text/x-latex']

    tokens = {
        'general': [
            (r'%.*?\n', Comment),
            (r'[{}]', Name.Builtin),
            (r'[&_^]', Name.Builtin),
        ],
        'root': [
            (r'\\\[', String.Backtick, 'displaymath'),
            (r'\\\(', String, 'inlinemath'),
            (r'\$\$', String.Backtick, 'displaymath'),
            (r'\$', String, 'inlinemath'),
            (r'\\([a-zA-Z]+|.)', Keyword, 'command'),
            (r'\\$', Keyword),
            include('general'),
            (r'[^\\$%&_^{}]+', Text),
        ],
        'math': [
            (r'\\([a-zA-Z]+|.)', Name.Variable),
            include('general'),
            (r'[0-9]+', Number),
            (r'[-=!+*/()\[\]]', Operator),
            (r'[^=!+*/()\[\]\\$%&_^{}0-9-]+', Name.Builtin),
        ],
        'inlinemath': [
            (r'\\\)', String, '#pop'),
            (r'\$', String, '#pop'),
            include('math'),
        ],
        'displaymath': [
            (r'\\\]', String, '#pop'),
            (r'\$\$', String, '#pop'),
            (r'\$', Name.Builtin),
            include('math'),
        ],
        'command': [
            (r'\[.*?\]', Name.Attribute),
            (r'\*', Keyword),
            default('#pop'),
        ],
    }

    def analyse_text(text):
        for start in ("\\documentclass", "\\input", "\\documentstyle",
                      "\\relax"):
            if text[:len(start)] == start:
                return True


class GroffLexer(RegexLexer):
    """
    Lexer for the (g)roff typesetting language, supporting groff
    extensions. Mainly useful for highlighting manpage sources.

    .. versionadded:: 0.6
    """

    name = 'Groff'
    aliases = ['groff', 'nroff', 'man']
    filenames = ['*.[1234567]', '*.man']
    mimetypes = ['application/x-troff', 'text/troff']

    tokens = {
        'root': [
            (r'(\.)(\w+)', bygroups(Text, Keyword), 'request'),
            (r'\.', Punctuation, 'request'),
            # Regular characters, slurp till we find a backslash or newline
            (r'[^\\\n]+', Text, 'textline'),
            default('textline'),
        ],
        'textline': [
            include('escapes'),
            (r'[^\\\n]+', Text),
            (r'\n', Text, '#pop'),
        ],
        'escapes': [
            # groff has many ways to write escapes.
            (r'\\"[^\n]*', Comment),
            (r'\\[fn]\w', String.Escape),
            (r'\\\(.{2}', String.Escape),
            (r'\\.\[.*\]', String.Escape),
            (r'\\.', String.Escape),
            (r'\\\n', Text, 'request'),
        ],
        'request': [
            (r'\n', Text, '#pop'),
            include('escapes'),
            (r'"[^\n"]+"', String.Double),
            (r'\d+', Number),
            (r'\S+', String),
            (r'\s+', Text),
        ],
    }

    def analyse_text(text):
        if text[:1] != '.':
            return False
        if text[:3] == '.\\"':
            return True
        if text[:4] == '.TH ':
            return True
        if text[1:3].isalnum() and text[3].isspace():
            return 0.9


class MozPreprocHashLexer(RegexLexer):
    """
    Lexer for Mozilla Preprocessor files (with '#' as the marker).

    Other data is left untouched.

    .. versionadded:: 2.0
    """
    name = 'mozhashpreproc'
    aliases = [name]
    filenames = []
    mimetypes = []

    tokens = {
        'root': [
            (r'^#', Comment.Preproc, ('expr', 'exprstart')),
            (r'.+', Other),
        ],
        'exprstart': [
            (r'(literal)(.*)', bygroups(Comment.Preproc, Text), '#pop:2'),
            (words((
                'define', 'undef', 'if', 'ifdef', 'ifndef', 'else', 'elif',
                'elifdef', 'elifndef', 'endif', 'expand', 'filter', 'unfilter',
                'include', 'includesubst', 'error')),
             Comment.Preproc, '#pop'),
        ],
        'expr': [
            (words(('!', '!=', '==', '&&', '||')), Operator),
            (r'(defined)(\()', bygroups(Keyword, Punctuation)),
            (r'\)', Punctuation),
            (r'[0-9]+', Number.Decimal),
            (r'__\w+?__', Name.Variable),
            (r'@\w+?@', Name.Class),
            (r'\w+', Name),
            (r'\n', Text, '#pop'),
            (r'\s+', Text),
            (r'\S', Punctuation),
        ],
    }


class MozPreprocPercentLexer(MozPreprocHashLexer):
    """
    Lexer for Mozilla Preprocessor files (with '%' as the marker).

    Other data is left untouched.

    .. versionadded:: 2.0
    """
    name = 'mozpercentpreproc'
    aliases = [name]
    filenames = []
    mimetypes = []

    tokens = {
        'root': [
            (r'^%', Comment.Preproc, ('expr', 'exprstart')),
            (r'.+', Other),
        ],
    }


class MozPreprocXulLexer(DelegatingLexer):
    """
    Subclass of the `MozPreprocHashLexer` that highlights unlexed data with the
    `XmlLexer`.

    .. versionadded:: 2.0
    """
    name = "XUL+mozpreproc"
    aliases = ['xul+mozpreproc']
    filenames = ['*.xul.in']
    mimetypes = []

    def __init__(self, **options):
        super(MozPreprocXulLexer, self).__init__(
            XmlLexer, MozPreprocHashLexer, **options)


class MozPreprocJavascriptLexer(DelegatingLexer):
    """
    Subclass of the `MozPreprocHashLexer` that highlights unlexed data with the
    `JavascriptLexer`.

    .. versionadded:: 2.0
    """
    name = "Javascript+mozpreproc"
    aliases = ['javascript+mozpreproc']
    filenames = ['*.js.in']
    mimetypes = []

    def __init__(self, **options):
        super(MozPreprocJavascriptLexer, self).__init__(
            JavascriptLexer, MozPreprocHashLexer, **options)


class MozPreprocCssLexer(DelegatingLexer):
    """
    Subclass of the `MozPreprocHashLexer` that highlights unlexed data with the
    `CssLexer`.

    .. versionadded:: 2.0
    """
    name = "CSS+mozpreproc"
    aliases = ['css+mozpreproc']
    filenames = ['*.css.in']
    mimetypes = []

    def __init__(self, **options):
        super(MozPreprocCssLexer, self).__init__(
            CssLexer, MozPreprocPercentLexer, **options)


class MarkdownLexer(RegexLexer):
    """
    For `Markdown <https://help.github.com/categories/writing-on-github/>`_ markup.

    .. versionadded:: 2.2
    """
    name = 'markdown'
    aliases = ['md']
    filenames = ['*.md']
    mimetypes = ["text/x-markdown"]
    flags = re.MULTILINE

    def _handle_codeblock(self, match):
        """
        match args: 1:backticks, 2:lang_name, 3:newline, 4:code, 5:backticks
        """
        from pygments.lexers import get_lexer_by_name

        # section header
        yield match.start(1), String        , match.group(1)
        yield match.start(2), String        , match.group(2)
        yield match.start(3), Text          , match.group(3)

        # lookup lexer if wanted and existing
        lexer = None
        if self.handlecodeblocks:
            try:
                lexer = get_lexer_by_name( match.group(2).strip() )
            except ClassNotFound:
                pass
        code = match.group(4)

        # no lexer for this language. handle it like it was a code block
        if lexer is None:
            yield match.start(4), String, code
        else:
            for item in do_insertions([], lexer.get_tokens_unprocessed(code)):
                yield item

        yield match.start(5), String        , match.group(5)

    tokens = {
        'root': [
            # heading with pound prefix
            (r'^(#)([^#].+\n)', bygroups(Generic.Heading, Text)),
            (r'^(#{2,6})(.+\n)', bygroups(Generic.Subheading, Text)),
            # task list
            (r'^(\s*)([*-] )(\[[ xX]\])( .+\n)',
            bygroups(Text, Keyword, Keyword, using(this, state='inline'))),
            # bulleted lists
            (r'^(\s*)([*-])(\s)(.+\n)',
            bygroups(Text, Keyword, Text, using(this, state='inline'))),
            # numbered lists
            (r'^(\s*)([0-9]+\.)( .+\n)',
            bygroups(Text, Keyword, using(this, state='inline'))),
            # quote
            (r'^(\s*>\s)(.+\n)', bygroups(Keyword, Generic.Emph)),
            # text block
            (r'^(```\n)([\w\W]*?)(^```$)', bygroups(String, Text, String)),
            # code block with language
            (r'^(```)(\w+)(\n)([\w\W]*?)(^```$)', _handle_codeblock),

            include('inline'),
        ],
        'inline': [
            # escape
            (r'\\.', Text),
            # italics
            (r'(\s)([*_][^*_]+[*_])(\W|\n)', bygroups(Text, Generic.Emph, Text)),
            # bold
            # warning: the following rule eats internal tags. eg. **foo _bar_ baz** bar is not italics
            (r'(\s)((\*\*|__).*\3)((?=\W|\n))', bygroups(Text, Generic.Strong, None, Text)),
            # "proper way" (r'(\s)([*_]{2}[^*_]+[*_]{2})((?=\W|\n))', bygroups(Text, Generic.Strong, Text)),
            # strikethrough
            (r'(\s)(~~[^~]+~~)((?=\W|\n))', bygroups(Text, Generic.Deleted, Text)),
            # inline code
            (r'`[^`]+`', String.Backtick),
            # mentions and topics (twitter and github stuff)
            (r'[@#][\w/:]+', Name.Entity),
            # (image?) links eg: ![Image of Yaktocat](https://octodex.github.com/images/yaktocat.png)
            (r'(!?\[)([^]]+)(\])(\()([^)]+)(\))', bygroups(Text, Name.Tag, Text, Text, Name.Attribute, Text)),

            # general text, must come last!
            (r'[^\\\s]+', Text),
            (r'.', Text),
        ],
    }

    def __init__(self, **options):
        self.handlecodeblocks = get_bool_opt(options, 'handlecodeblocks', True)
        RegexLexer.__init__(self, **options)
