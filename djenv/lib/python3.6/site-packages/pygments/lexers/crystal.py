# -*- coding: utf-8 -*-
"""
    pygments.lexers.crystal
    ~~~~~~~~~~~~~~~~~~~~~~~

    Lexer for Crystal.

    :copyright: Copyright 2006-2017 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from pygments.lexer import ExtendedRegexLexer, include, \
    bygroups, default, LexerContext, words
from pygments.token import Text, Comment, Operator, Keyword, Name, String, \
    Number, Punctuation, Error

__all__ = ['CrystalLexer']

line_re = re.compile('.*?\n')


CRYSTAL_OPERATORS = [
    '!=', '!~', '!', '%', '&&', '&', '**', '*', '+', '-', '/', '<=>', '<<', '<=', '<',
    '===', '==', '=~', '=', '>=', '>>', '>', '[]=', '[]?', '[]', '^', '||', '|', '~'
]


class CrystalLexer(ExtendedRegexLexer):
    """
    For `Crystal <http://crystal-lang.org>`_ source code.

    .. versionadded:: 2.2
    """

    name = 'Crystal'
    aliases = ['cr', 'crystal']
    filenames = ['*.cr']
    mimetypes = ['text/x-crystal']

    flags = re.DOTALL | re.MULTILINE

    def heredoc_callback(self, match, ctx):
        # okay, this is the hardest part of parsing Crystal...
        # match: 1 = <<-?, 2 = quote? 3 = name 4 = quote? 5 = rest of line

        start = match.start(1)
        yield start, Operator, match.group(1)        # <<-?
        yield match.start(2), String.Heredoc, match.group(2)    # quote ", ', `
        yield match.start(3), String.Delimiter, match.group(3)  # heredoc name
        yield match.start(4), String.Heredoc, match.group(4)    # quote again

        heredocstack = ctx.__dict__.setdefault('heredocstack', [])
        outermost = not bool(heredocstack)
        heredocstack.append((match.group(1) == '<<-', match.group(3)))

        ctx.pos = match.start(5)
        ctx.end = match.end(5)
        # this may find other heredocs
        for i, t, v in self.get_tokens_unprocessed(context=ctx):
            yield i, t, v
        ctx.pos = match.end()

        if outermost:
            # this is the outer heredoc again, now we can process them all
            for tolerant, hdname in heredocstack:
                lines = []
                for match in line_re.finditer(ctx.text, ctx.pos):
                    if tolerant:
                        check = match.group().strip()
                    else:
                        check = match.group().rstrip()
                    if check == hdname:
                        for amatch in lines:
                            yield amatch.start(), String.Heredoc, amatch.group()
                        yield match.start(), String.Delimiter, match.group()
                        ctx.pos = match.end()
                        break
                    else:
                        lines.append(match)
                else:
                    # end of heredoc not found -- error!
                    for amatch in lines:
                        yield amatch.start(), Error, amatch.group()
            ctx.end = len(ctx.text)
            del heredocstack[:]

    def gen_crystalstrings_rules():
        def intp_regex_callback(self, match, ctx):
            yield match.start(1), String.Regex, match.group(1)  # begin
            nctx = LexerContext(match.group(3), 0, ['interpolated-regex'])
            for i, t, v in self.get_tokens_unprocessed(context=nctx):
                yield match.start(3)+i, t, v
            yield match.start(4), String.Regex, match.group(4)  # end[imsx]*
            ctx.pos = match.end()

        def intp_string_callback(self, match, ctx):
            yield match.start(1), String.Other, match.group(1)
            nctx = LexerContext(match.group(3), 0, ['interpolated-string'])
            for i, t, v in self.get_tokens_unprocessed(context=nctx):
                yield match.start(3)+i, t, v
            yield match.start(4), String.Other, match.group(4)  # end
            ctx.pos = match.end()

        states = {}
        states['strings'] = [
            (r'\:@{0,2}[a-zA-Z_]\w*[!?]?', String.Symbol),
            (words(CRYSTAL_OPERATORS, prefix=r'\:@{0,2}'), String.Symbol),
            (r":'(\\\\|\\'|[^'])*'", String.Symbol),
            # This allows arbitrary text after '\ for simplicity
            (r"'(\\\\|\\'|[^']|\\[^'\\]+)'", String.Char),
            (r':"', String.Symbol, 'simple-sym'),
            # Crystal doesn't have "symbol:"s but this simplifies function args
            (r'([a-zA-Z_]\w*)(:)(?!:)', bygroups(String.Symbol, Punctuation)),
            (r'"', String.Double, 'simple-string'),
            (r'(?<!\.)`', String.Backtick, 'simple-backtick'),
        ]

        # double-quoted string and symbol
        for name, ttype, end in ('string', String.Double, '"'), \
                                ('sym', String.Symbol, '"'), \
                                ('backtick', String.Backtick, '`'):
            states['simple-'+name] = [
                include('string-escaped' if name == 'sym' else 'string-intp-escaped'),
                (r'[^\\%s#]+' % end, ttype),
                (r'[\\#]', ttype),
                (end, ttype, '#pop'),
            ]

        # braced quoted strings
        for lbrace, rbrace, bracecc, name in \
                ('\\{', '\\}', '{}', 'cb'), \
                ('\\[', '\\]', '\\[\\]', 'sb'), \
                ('\\(', '\\)', '()', 'pa'), \
                ('<', '>', '<>', 'ab'):
            states[name+'-intp-string'] = [
                (r'\\[' + lbrace + ']', String.Other),
                (lbrace, String.Other, '#push'),
                (rbrace, String.Other, '#pop'),
                include('string-intp-escaped'),
                (r'[\\#' + bracecc + ']', String.Other),
                (r'[^\\#' + bracecc + ']+', String.Other),
            ]
            states['strings'].append((r'%' + lbrace, String.Other,
                                      name+'-intp-string'))
            states[name+'-string'] = [
                (r'\\[\\' + bracecc + ']', String.Other),
                (lbrace, String.Other, '#push'),
                (rbrace, String.Other, '#pop'),
                (r'[\\#' + bracecc + ']', String.Other),
                (r'[^\\#' + bracecc + ']+', String.Other),
            ]
            # http://crystal-lang.org/docs/syntax_and_semantics/literals/array.html
            states['strings'].append((r'%[wi]' + lbrace, String.Other,
                                      name+'-string'))
            states[name+'-regex'] = [
                (r'\\[\\' + bracecc + ']', String.Regex),
                (lbrace, String.Regex, '#push'),
                (rbrace + '[imsx]*', String.Regex, '#pop'),
                include('string-intp'),
                (r'[\\#' + bracecc + ']', String.Regex),
                (r'[^\\#' + bracecc + ']+', String.Regex),
            ]
            states['strings'].append((r'%r' + lbrace, String.Regex,
                                      name+'-regex'))

        # these must come after %<brace>!
        states['strings'] += [
            # %r regex
            (r'(%r([\W_]))((?:\\\2|(?!\2).)*)(\2[imsx]*)',
             intp_regex_callback),
            # regular fancy strings with qsw
            (r'(%[wi]([\W_]))((?:\\\2|(?!\2).)*)(\2)',
             intp_string_callback),
            # special forms of fancy strings after operators or
            # in method calls with braces
            (r'(?<=[-+/*%=<>&!^|~,(])(\s*)(%([\t ])(?:(?:\\\3|(?!\3).)*)\3)',
             bygroups(Text, String.Other, None)),
            # and because of fixed width lookbehinds the whole thing a
            # second time for line startings...
            (r'^(\s*)(%([\t ])(?:(?:\\\3|(?!\3).)*)\3)',
             bygroups(Text, String.Other, None)),
            # all regular fancy strings without qsw
            (r'(%([\[{(<]))((?:\\\2|(?!\2).)*)(\2)',
             intp_string_callback),
        ]

        return states

    tokens = {
        'root': [
            (r'#.*?$', Comment.Single),
            # keywords
            (words('''
                abstract asm as begin break case do else elsif end ensure extend ifdef if
                include instance_sizeof next of pointerof private protected rescue return
                require sizeof super then typeof unless until when while with yield
            '''.split(), suffix=r'\b'), Keyword),
            (words(['true', 'false', 'nil'], suffix=r'\b'), Keyword.Constant),
            # start of function, class and module names
            (r'(module|lib)(\s+)([a-zA-Z_]\w*(?:::[a-zA-Z_]\w*)*)',
             bygroups(Keyword, Text, Name.Namespace)),
            (r'(def|fun|macro)(\s+)((?:[a-zA-Z_]\w*::)*)',
             bygroups(Keyword, Text, Name.Namespace), 'funcname'),
            (r'def(?=[*%&^`~+-/\[<>=])', Keyword, 'funcname'),
            (r'(class|struct|union|type|alias|enum)(\s+)((?:[a-zA-Z_]\w*::)*)',
             bygroups(Keyword, Text, Name.Namespace), 'classname'),
            (r'(self|out|uninitialized)\b|(is_a|responds_to)\?', Keyword.Pseudo),
            # macros
            (words('''
                debugger record pp assert_responds_to spawn parallel
                getter setter property delegate def_hash def_equals def_equals_and_hash
                forward_missing_to
            '''.split(), suffix=r'\b'), Name.Builtin.Pseudo),
            (r'getter[!?]|property[!?]|__(DIR|FILE|LINE)__\b', Name.Builtin.Pseudo),
            # builtins
            # http://crystal-lang.org/api/toplevel.html
            (words('''
                Object Value Struct Reference Proc Class Nil Symbol Enum Void
                Bool Number Int Int8 Int16 Int32 Int64 UInt8 UInt16 UInt32 UInt64
                Float Float32 Float64 Char String
                Pointer Slice Range Exception Regex
                Mutex StaticArray Array Hash Set Tuple Deque Box Process File
                Dir Time Channel Concurrent Scheduler
                abort at_exit caller delay exit fork future get_stack_top gets
                lazy loop main p print printf puts
                raise rand read_line sleep sprintf system with_color
            '''.split(), prefix=r'(?<!\.)', suffix=r'\b'), Name.Builtin),
            # normal heredocs
            (r'(?<!\w)(<<-?)(["`\']?)([a-zA-Z_]\w*)(\2)(.*?\n)',
             heredoc_callback),
            # empty string heredocs
            (r'(<<-?)("|\')()(\2)(.*?\n)', heredoc_callback),
            (r'__END__', Comment.Preproc, 'end-part'),
            # multiline regex (after keywords or assignments)
            (r'(?:^|(?<=[=<>~!:])|'
             r'(?<=(?:\s|;)when\s)|'
             r'(?<=(?:\s|;)or\s)|'
             r'(?<=(?:\s|;)and\s)|'
             r'(?<=\.index\s)|'
             r'(?<=\.scan\s)|'
             r'(?<=\.sub\s)|'
             r'(?<=\.sub!\s)|'
             r'(?<=\.gsub\s)|'
             r'(?<=\.gsub!\s)|'
             r'(?<=\.match\s)|'
             r'(?<=(?:\s|;)if\s)|'
             r'(?<=(?:\s|;)elsif\s)|'
             r'(?<=^when\s)|'
             r'(?<=^index\s)|'
             r'(?<=^scan\s)|'
             r'(?<=^sub\s)|'
             r'(?<=^gsub\s)|'
             r'(?<=^sub!\s)|'
             r'(?<=^gsub!\s)|'
             r'(?<=^match\s)|'
             r'(?<=^if\s)|'
             r'(?<=^elsif\s)'
             r')(\s*)(/)', bygroups(Text, String.Regex), 'multiline-regex'),
            # multiline regex (in method calls or subscripts)
            (r'(?<=\(|,|\[)/', String.Regex, 'multiline-regex'),
            # multiline regex (this time the funny no whitespace rule)
            (r'(\s+)(/)(?![\s=])', bygroups(Text, String.Regex),
             'multiline-regex'),
            # lex numbers and ignore following regular expressions which
            # are division operators in fact (grrrr. i hate that. any
            # better ideas?)
            # since pygments 0.7 we also eat a "?" operator after numbers
            # so that the char operator does not work. Chars are not allowed
            # there so that you can use the ternary operator.
            # stupid example:
            #   x>=0?n[x]:""
            (r'(0o[0-7]+(?:_[0-7]+)*(?:_?[iu][0-9]+)?)\b(\s*)([/?])?',
             bygroups(Number.Oct, Text, Operator)),
            (r'(0x[0-9A-Fa-f]+(?:_[0-9A-Fa-f]+)*(?:_?[iu][0-9]+)?)\b(\s*)([/?])?',
             bygroups(Number.Hex, Text, Operator)),
            (r'(0b[01]+(?:_[01]+)*(?:_?[iu][0-9]+)?)\b(\s*)([/?])?',
             bygroups(Number.Bin, Text, Operator)),
            # 3 separate expressions for floats because any of the 3 optional
            # parts makes it a float
            (r'((?:0(?![0-9])|[1-9][\d_]*)(?:\.\d[\d_]*)(?:e[+-]?[0-9]+)?'
             r'(?:_?f[0-9]+)?)(\s*)([/?])?',
             bygroups(Number.Float, Text, Operator)),
            (r'((?:0(?![0-9])|[1-9][\d_]*)(?:\.\d[\d_]*)?(?:e[+-]?[0-9]+)'
             r'(?:_?f[0-9]+)?)(\s*)([/?])?',
             bygroups(Number.Float, Text, Operator)),
            (r'((?:0(?![0-9])|[1-9][\d_]*)(?:\.\d[\d_]*)?(?:e[+-]?[0-9]+)?'
             r'(?:_?f[0-9]+))(\s*)([/?])?',
             bygroups(Number.Float, Text, Operator)),
            (r'(0\b|[1-9][\d]*(?:_\d+)*(?:_?[iu][0-9]+)?)\b(\s*)([/?])?',
             bygroups(Number.Integer, Text, Operator)),
            # Names
            (r'@@[a-zA-Z_]\w*', Name.Variable.Class),
            (r'@[a-zA-Z_]\w*', Name.Variable.Instance),
            (r'\$\w+', Name.Variable.Global),
            (r'\$[!@&`\'+~=/\\,;.<>_*$?:"^-]', Name.Variable.Global),
            (r'\$-[0adFiIlpvw]', Name.Variable.Global),
            (r'::', Operator),
            include('strings'),
            # chars
            (r'\?(\\[MC]-)*'  # modifiers
             r'(\\([\\befnrtv#"\']|x[a-fA-F0-9]{1,2}|[0-7]{1,3})|\S)'
             r'(?!\w)',
             String.Char),
            (r'[A-Z][A-Z_]+\b', Name.Constant),
            # macro expansion
            (r'\{%', String.Interpol, 'in-macro-control'),
            (r'\{\{', String.Interpol, 'in-macro-expr'),
            # attributes
            (r'(@\[)(\s*)([A-Z]\w*)',
             bygroups(Operator, Text, Name.Decorator), 'in-attr'),
            # this is needed because Crystal attributes can look
            # like keywords (class) or like this: ` ?!?
            (words(CRYSTAL_OPERATORS, prefix=r'(\.|::)'),
             bygroups(Operator, Name.Operator)),
            (r'(\.|::)([a-zA-Z_]\w*[!?]?|[*%&^`~+\-/\[<>=])',
             bygroups(Operator, Name)),
            # Names can end with [!?] unless it's "!="
            (r'[a-zA-Z_]\w*(?:[!?](?!=))?', Name),
            (r'(\[|\]\??|\*\*|<=>?|>=|<<?|>>?|=~|===|'
             r'!~|&&?|\|\||\.{1,3})', Operator),
            (r'[-+/*%=<>&!^|~]=?', Operator),
            (r'[(){};,/?:\\]', Punctuation),
            (r'\s+', Text)
        ],
        'funcname': [
            (r'(?:([a-zA-Z_]\w*)(\.))?'
             r'([a-zA-Z_]\w*[!?]?|\*\*?|[-+]@?|'
             r'[/%&|^`~]|\[\]=?|<<|>>|<=?>|>=?|===?)',
             bygroups(Name.Class, Operator, Name.Function), '#pop'),
            default('#pop')
        ],
        'classname': [
            (r'[A-Z_]\w*', Name.Class),
            (r'(\()(\s*)([A-Z_]\w*)(\s*)(\))',
             bygroups(Punctuation, Text, Name.Class, Text, Punctuation)),
            default('#pop')
        ],
        'in-intp': [
            (r'\{', String.Interpol, '#push'),
            (r'\}', String.Interpol, '#pop'),
            include('root'),
        ],
        'string-intp': [
            (r'#\{', String.Interpol, 'in-intp'),
        ],
        'string-escaped': [
            (r'\\([\\befnstv#"\']|x[a-fA-F0-9]{1,2}|[0-7]{1,3})', String.Escape)
        ],
        'string-intp-escaped': [
            include('string-intp'),
            include('string-escaped'),
        ],
        'interpolated-regex': [
            include('string-intp'),
            (r'[\\#]', String.Regex),
            (r'[^\\#]+', String.Regex),
        ],
        'interpolated-string': [
            include('string-intp'),
            (r'[\\#]', String.Other),
            (r'[^\\#]+', String.Other),
        ],
        'multiline-regex': [
            include('string-intp'),
            (r'\\\\', String.Regex),
            (r'\\/', String.Regex),
            (r'[\\#]', String.Regex),
            (r'[^\\/#]+', String.Regex),
            (r'/[imsx]*', String.Regex, '#pop'),
        ],
        'end-part': [
            (r'.+', Comment.Preproc, '#pop')
        ],
        'in-macro-control': [
            (r'\{%', String.Interpol, '#push'),
            (r'%\}', String.Interpol, '#pop'),
            (r'for\b|in\b', Keyword),
            include('root'),
        ],
        'in-macro-expr': [
            (r'\{\{', String.Interpol, '#push'),
            (r'\}\}', String.Interpol, '#pop'),
            include('root'),
        ],
        'in-attr': [
            (r'\[', Operator, '#push'),
            (r'\]', Operator, '#pop'),
            include('root'),
        ],
    }
    tokens.update(gen_crystalstrings_rules())
