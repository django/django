# -*- coding: utf-8 -*-
"""
    pygments.lexers.lisp
    ~~~~~~~~~~~~~~~~~~~~

    Lexers for Lispy languages.

    :copyright: Copyright 2006-2017 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from pygments.lexer import RegexLexer, include, bygroups, words, default
from pygments.token import Text, Comment, Operator, Keyword, Name, String, \
    Number, Punctuation, Literal, Error

from pygments.lexers.python import PythonLexer

__all__ = ['SchemeLexer', 'CommonLispLexer', 'HyLexer', 'RacketLexer',
           'NewLispLexer', 'EmacsLispLexer', 'ShenLexer', 'CPSALexer',
           'XtlangLexer', 'FennelLexer']


class SchemeLexer(RegexLexer):
    """
    A Scheme lexer, parsing a stream and outputting the tokens
    needed to highlight scheme code.
    This lexer could be most probably easily subclassed to parse
    other LISP-Dialects like Common Lisp, Emacs Lisp or AutoLisp.

    This parser is checked with pastes from the LISP pastebin
    at http://paste.lisp.org/ to cover as much syntax as possible.

    It supports the full Scheme syntax as defined in R5RS.

    .. versionadded:: 0.6
    """
    name = 'Scheme'
    aliases = ['scheme', 'scm']
    filenames = ['*.scm', '*.ss']
    mimetypes = ['text/x-scheme', 'application/x-scheme']

    # list of known keywords and builtins taken form vim 6.4 scheme.vim
    # syntax file.
    keywords = (
        'lambda', 'define', 'if', 'else', 'cond', 'and', 'or', 'case', 'let',
        'let*', 'letrec', 'begin', 'do', 'delay', 'set!', '=>', 'quote',
        'quasiquote', 'unquote', 'unquote-splicing', 'define-syntax',
        'let-syntax', 'letrec-syntax', 'syntax-rules'
    )
    builtins = (
        '*', '+', '-', '/', '<', '<=', '=', '>', '>=', 'abs', 'acos', 'angle',
        'append', 'apply', 'asin', 'assoc', 'assq', 'assv', 'atan',
        'boolean?', 'caaaar', 'caaadr', 'caaar', 'caadar', 'caaddr', 'caadr',
        'caar', 'cadaar', 'cadadr', 'cadar', 'caddar', 'cadddr', 'caddr',
        'cadr', 'call-with-current-continuation', 'call-with-input-file',
        'call-with-output-file', 'call-with-values', 'call/cc', 'car',
        'cdaaar', 'cdaadr', 'cdaar', 'cdadar', 'cdaddr', 'cdadr', 'cdar',
        'cddaar', 'cddadr', 'cddar', 'cdddar', 'cddddr', 'cdddr', 'cddr',
        'cdr', 'ceiling', 'char->integer', 'char-alphabetic?', 'char-ci<=?',
        'char-ci<?', 'char-ci=?', 'char-ci>=?', 'char-ci>?', 'char-downcase',
        'char-lower-case?', 'char-numeric?', 'char-ready?', 'char-upcase',
        'char-upper-case?', 'char-whitespace?', 'char<=?', 'char<?', 'char=?',
        'char>=?', 'char>?', 'char?', 'close-input-port', 'close-output-port',
        'complex?', 'cons', 'cos', 'current-input-port', 'current-output-port',
        'denominator', 'display', 'dynamic-wind', 'eof-object?', 'eq?',
        'equal?', 'eqv?', 'eval', 'even?', 'exact->inexact', 'exact?', 'exp',
        'expt', 'floor', 'for-each', 'force', 'gcd', 'imag-part',
        'inexact->exact', 'inexact?', 'input-port?', 'integer->char',
        'integer?', 'interaction-environment', 'lcm', 'length', 'list',
        'list->string', 'list->vector', 'list-ref', 'list-tail', 'list?',
        'load', 'log', 'magnitude', 'make-polar', 'make-rectangular',
        'make-string', 'make-vector', 'map', 'max', 'member', 'memq', 'memv',
        'min', 'modulo', 'negative?', 'newline', 'not', 'null-environment',
        'null?', 'number->string', 'number?', 'numerator', 'odd?',
        'open-input-file', 'open-output-file', 'output-port?', 'pair?',
        'peek-char', 'port?', 'positive?', 'procedure?', 'quotient',
        'rational?', 'rationalize', 'read', 'read-char', 'real-part', 'real?',
        'remainder', 'reverse', 'round', 'scheme-report-environment',
        'set-car!', 'set-cdr!', 'sin', 'sqrt', 'string', 'string->list',
        'string->number', 'string->symbol', 'string-append', 'string-ci<=?',
        'string-ci<?', 'string-ci=?', 'string-ci>=?', 'string-ci>?',
        'string-copy', 'string-fill!', 'string-length', 'string-ref',
        'string-set!', 'string<=?', 'string<?', 'string=?', 'string>=?',
        'string>?', 'string?', 'substring', 'symbol->string', 'symbol?',
        'tan', 'transcript-off', 'transcript-on', 'truncate', 'values',
        'vector', 'vector->list', 'vector-fill!', 'vector-length',
        'vector-ref', 'vector-set!', 'vector?', 'with-input-from-file',
        'with-output-to-file', 'write', 'write-char', 'zero?'
    )

    # valid names for identifiers
    # well, names can only not consist fully of numbers
    # but this should be good enough for now
    valid_name = r'[\w!$%&*+,/:<=>?@^~|-]+'

    tokens = {
        'root': [
            # the comments
            # and going to the end of the line
            (r';.*$', Comment.Single),
            # multi-line comment
            (r'#\|', Comment.Multiline, 'multiline-comment'),
            # commented form (entire sexpr folliwng)
            (r'#;\s*\(', Comment, 'commented-form'),
            # signifies that the program text that follows is written with the
            # lexical and datum syntax described in r6rs
            (r'#!r6rs', Comment),

            # whitespaces - usually not relevant
            (r'\s+', Text),

            # numbers
            (r'-?\d+\.\d+', Number.Float),
            (r'-?\d+', Number.Integer),
            # support for uncommon kinds of numbers -
            # have to figure out what the characters mean
            # (r'(#e|#i|#b|#o|#d|#x)[\d.]+', Number),

            # strings, symbols and characters
            (r'"(\\\\|\\"|[^"])*"', String),
            (r"'" + valid_name, String.Symbol),
            (r"#\\([()/'\"._!§$%& ?=+-]|[a-zA-Z0-9]+)", String.Char),

            # constants
            (r'(#t|#f)', Name.Constant),

            # special operators
            (r"('|#|`|,@|,|\.)", Operator),

            # highlight the keywords
            ('(%s)' % '|'.join(re.escape(entry) + ' ' for entry in keywords),
             Keyword),

            # first variable in a quoted string like
            # '(this is syntactic sugar)
            (r"(?<='\()" + valid_name, Name.Variable),
            (r"(?<=#\()" + valid_name, Name.Variable),

            # highlight the builtins
            (r"(?<=\()(%s)" % '|'.join(re.escape(entry) + ' ' for entry in builtins),
             Name.Builtin),

            # the remaining functions
            (r'(?<=\()' + valid_name, Name.Function),
            # find the remaining variables
            (valid_name, Name.Variable),

            # the famous parentheses!
            (r'(\(|\))', Punctuation),
            (r'(\[|\])', Punctuation),
        ],
        'multiline-comment': [
            (r'#\|', Comment.Multiline, '#push'),
            (r'\|#', Comment.Multiline, '#pop'),
            (r'[^|#]+', Comment.Multiline),
            (r'[|#]', Comment.Multiline),
        ],
        'commented-form': [
            (r'\(', Comment, '#push'),
            (r'\)', Comment, '#pop'),
            (r'[^()]+', Comment),
        ],
    }


class CommonLispLexer(RegexLexer):
    """
    A Common Lisp lexer.

    .. versionadded:: 0.9
    """
    name = 'Common Lisp'
    aliases = ['common-lisp', 'cl', 'lisp']
    filenames = ['*.cl', '*.lisp']
    mimetypes = ['text/x-common-lisp']

    flags = re.IGNORECASE | re.MULTILINE

    # couple of useful regexes

    # characters that are not macro-characters and can be used to begin a symbol
    nonmacro = r'\\.|[\w!$%&*+-/<=>?@\[\]^{}~]'
    constituent = nonmacro + '|[#.:]'
    terminated = r'(?=[ "()\'\n,;`])'  # whitespace or terminating macro characters

    # symbol token, reverse-engineered from hyperspec
    # Take a deep breath...
    symbol = r'(\|[^|]+\||(?:%s)(?:%s)*)' % (nonmacro, constituent)

    def __init__(self, **options):
        from pygments.lexers._cl_builtins import BUILTIN_FUNCTIONS, \
            SPECIAL_FORMS, MACROS, LAMBDA_LIST_KEYWORDS, DECLARATIONS, \
            BUILTIN_TYPES, BUILTIN_CLASSES
        self.builtin_function = BUILTIN_FUNCTIONS
        self.special_forms = SPECIAL_FORMS
        self.macros = MACROS
        self.lambda_list_keywords = LAMBDA_LIST_KEYWORDS
        self.declarations = DECLARATIONS
        self.builtin_types = BUILTIN_TYPES
        self.builtin_classes = BUILTIN_CLASSES
        RegexLexer.__init__(self, **options)

    def get_tokens_unprocessed(self, text):
        stack = ['root']
        for index, token, value in RegexLexer.get_tokens_unprocessed(self, text, stack):
            if token is Name.Variable:
                if value in self.builtin_function:
                    yield index, Name.Builtin, value
                    continue
                if value in self.special_forms:
                    yield index, Keyword, value
                    continue
                if value in self.macros:
                    yield index, Name.Builtin, value
                    continue
                if value in self.lambda_list_keywords:
                    yield index, Keyword, value
                    continue
                if value in self.declarations:
                    yield index, Keyword, value
                    continue
                if value in self.builtin_types:
                    yield index, Keyword.Type, value
                    continue
                if value in self.builtin_classes:
                    yield index, Name.Class, value
                    continue
            yield index, token, value

    tokens = {
        'root': [
            default('body'),
        ],
        'multiline-comment': [
            (r'#\|', Comment.Multiline, '#push'),  # (cf. Hyperspec 2.4.8.19)
            (r'\|#', Comment.Multiline, '#pop'),
            (r'[^|#]+', Comment.Multiline),
            (r'[|#]', Comment.Multiline),
        ],
        'commented-form': [
            (r'\(', Comment.Preproc, '#push'),
            (r'\)', Comment.Preproc, '#pop'),
            (r'[^()]+', Comment.Preproc),
        ],
        'body': [
            # whitespace
            (r'\s+', Text),

            # single-line comment
            (r';.*$', Comment.Single),

            # multi-line comment
            (r'#\|', Comment.Multiline, 'multiline-comment'),

            # encoding comment (?)
            (r'#\d*Y.*$', Comment.Special),

            # strings and characters
            (r'"(\\.|\\\n|[^"\\])*"', String),
            # quoting
            (r":" + symbol, String.Symbol),
            (r"::" + symbol, String.Symbol),
            (r":#" + symbol, String.Symbol),
            (r"'" + symbol, String.Symbol),
            (r"'", Operator),
            (r"`", Operator),

            # decimal numbers
            (r'[-+]?\d+\.?' + terminated, Number.Integer),
            (r'[-+]?\d+/\d+' + terminated, Number),
            (r'[-+]?(\d*\.\d+([defls][-+]?\d+)?|\d+(\.\d*)?[defls][-+]?\d+)' +
             terminated, Number.Float),

            # sharpsign strings and characters
            (r"#\\." + terminated, String.Char),
            (r"#\\" + symbol, String.Char),

            # vector
            (r'#\(', Operator, 'body'),

            # bitstring
            (r'#\d*\*[01]*', Literal.Other),

            # uninterned symbol
            (r'#:' + symbol, String.Symbol),

            # read-time and load-time evaluation
            (r'#[.,]', Operator),

            # function shorthand
            (r'#\'', Name.Function),

            # binary rational
            (r'#b[+-]?[01]+(/[01]+)?', Number.Bin),

            # octal rational
            (r'#o[+-]?[0-7]+(/[0-7]+)?', Number.Oct),

            # hex rational
            (r'#x[+-]?[0-9a-f]+(/[0-9a-f]+)?', Number.Hex),

            # radix rational
            (r'#\d+r[+-]?[0-9a-z]+(/[0-9a-z]+)?', Number),

            # complex
            (r'(#c)(\()', bygroups(Number, Punctuation), 'body'),

            # array
            (r'(#\d+a)(\()', bygroups(Literal.Other, Punctuation), 'body'),

            # structure
            (r'(#s)(\()', bygroups(Literal.Other, Punctuation), 'body'),

            # path
            (r'#p?"(\\.|[^"])*"', Literal.Other),

            # reference
            (r'#\d+=', Operator),
            (r'#\d+#', Operator),

            # read-time comment
            (r'#+nil' + terminated + r'\s*\(', Comment.Preproc, 'commented-form'),

            # read-time conditional
            (r'#[+-]', Operator),

            # special operators that should have been parsed already
            (r'(,@|,|\.)', Operator),

            # special constants
            (r'(t|nil)' + terminated, Name.Constant),

            # functions and variables
            (r'\*' + symbol + r'\*', Name.Variable.Global),
            (symbol, Name.Variable),

            # parentheses
            (r'\(', Punctuation, 'body'),
            (r'\)', Punctuation, '#pop'),
        ],
    }


class HyLexer(RegexLexer):
    """
    Lexer for `Hy <http://hylang.org/>`_ source code.

    .. versionadded:: 2.0
    """
    name = 'Hy'
    aliases = ['hylang']
    filenames = ['*.hy']
    mimetypes = ['text/x-hy', 'application/x-hy']

    special_forms = (
        'cond', 'for', '->', '->>', 'car',
        'cdr', 'first', 'rest', 'let', 'when', 'unless',
        'import', 'do', 'progn', 'get', 'slice', 'assoc', 'with-decorator',
        ',', 'list_comp', 'kwapply', '~', 'is', 'in', 'is-not', 'not-in',
        'quasiquote', 'unquote', 'unquote-splice', 'quote', '|', '<<=', '>>=',
        'foreach', 'while',
        'eval-and-compile', 'eval-when-compile'
    )

    declarations = (
        'def', 'defn', 'defun', 'defmacro', 'defclass', 'lambda', 'fn', 'setv'
    )

    hy_builtins = ()

    hy_core = (
        'cycle', 'dec', 'distinct', 'drop', 'even?', 'filter', 'inc',
        'instance?', 'iterable?', 'iterate', 'iterator?', 'neg?',
        'none?', 'nth', 'numeric?', 'odd?', 'pos?', 'remove', 'repeat',
        'repeatedly', 'take', 'take_nth', 'take_while', 'zero?'
    )

    builtins = hy_builtins + hy_core

    # valid names for identifiers
    # well, names can only not consist fully of numbers
    # but this should be good enough for now
    valid_name = r'(?!#)[\w!$%*+<=>?/.#-:]+'

    def _multi_escape(entries):
        return words(entries, suffix=' ')

    tokens = {
        'root': [
            # the comments - always starting with semicolon
            # and going to the end of the line
            (r';.*$', Comment.Single),

            # whitespaces - usually not relevant
            (r'[,\s]+', Text),

            # numbers
            (r'-?\d+\.\d+', Number.Float),
            (r'-?\d+', Number.Integer),
            (r'0[0-7]+j?', Number.Oct),
            (r'0[xX][a-fA-F0-9]+', Number.Hex),

            # strings, symbols and characters
            (r'"(\\\\|\\"|[^"])*"', String),
            (r"'" + valid_name, String.Symbol),
            (r"\\(.|[a-z]+)", String.Char),
            (r'^(\s*)([rRuU]{,2}"""(?:.|\n)*?""")', bygroups(Text, String.Doc)),
            (r"^(\s*)([rRuU]{,2}'''(?:.|\n)*?''')", bygroups(Text, String.Doc)),

            # keywords
            (r'::?' + valid_name, String.Symbol),

            # special operators
            (r'~@|[`\'#^~&@]', Operator),

            include('py-keywords'),
            include('py-builtins'),

            # highlight the special forms
            (_multi_escape(special_forms), Keyword),

            # Technically, only the special forms are 'keywords'. The problem
            # is that only treating them as keywords means that things like
            # 'defn' and 'ns' need to be highlighted as builtins. This is ugly
            # and weird for most styles. So, as a compromise we're going to
            # highlight them as Keyword.Declarations.
            (_multi_escape(declarations), Keyword.Declaration),

            # highlight the builtins
            (_multi_escape(builtins), Name.Builtin),

            # the remaining functions
            (r'(?<=\()' + valid_name, Name.Function),

            # find the remaining variables
            (valid_name, Name.Variable),

            # Hy accepts vector notation
            (r'(\[|\])', Punctuation),

            # Hy accepts map notation
            (r'(\{|\})', Punctuation),

            # the famous parentheses!
            (r'(\(|\))', Punctuation),

        ],
        'py-keywords': PythonLexer.tokens['keywords'],
        'py-builtins': PythonLexer.tokens['builtins'],
    }

    def analyse_text(text):
        if '(import ' in text or '(defn ' in text:
            return 0.9


class RacketLexer(RegexLexer):
    """
    Lexer for `Racket <http://racket-lang.org/>`_ source code (formerly
    known as PLT Scheme).

    .. versionadded:: 1.6
    """

    name = 'Racket'
    aliases = ['racket', 'rkt']
    filenames = ['*.rkt', '*.rktd', '*.rktl']
    mimetypes = ['text/x-racket', 'application/x-racket']

    # Generated by example.rkt
    _keywords = (
        u'#%app', u'#%datum', u'#%declare', u'#%expression', u'#%module-begin',
        u'#%plain-app', u'#%plain-lambda', u'#%plain-module-begin',
        u'#%printing-module-begin', u'#%provide', u'#%require',
        u'#%stratified-body', u'#%top', u'#%top-interaction',
        u'#%variable-reference', u'->', u'->*', u'->*m', u'->d', u'->dm', u'->i',
        u'->m', u'...', u':do-in', u'==', u'=>', u'_', u'absent', u'abstract',
        u'all-defined-out', u'all-from-out', u'and', u'any', u'augment', u'augment*',
        u'augment-final', u'augment-final*', u'augride', u'augride*', u'begin',
        u'begin-for-syntax', u'begin0', u'case', u'case->', u'case->m',
        u'case-lambda', u'class', u'class*', u'class-field-accessor',
        u'class-field-mutator', u'class/c', u'class/derived', u'combine-in',
        u'combine-out', u'command-line', u'compound-unit', u'compound-unit/infer',
        u'cond', u'cons/dc', u'contract', u'contract-out', u'contract-struct',
        u'contracted', u'define', u'define-compound-unit',
        u'define-compound-unit/infer', u'define-contract-struct',
        u'define-custom-hash-types', u'define-custom-set-types',
        u'define-for-syntax', u'define-local-member-name', u'define-logger',
        u'define-match-expander', u'define-member-name',
        u'define-module-boundary-contract', u'define-namespace-anchor',
        u'define-opt/c', u'define-sequence-syntax', u'define-serializable-class',
        u'define-serializable-class*', u'define-signature',
        u'define-signature-form', u'define-struct', u'define-struct/contract',
        u'define-struct/derived', u'define-syntax', u'define-syntax-rule',
        u'define-syntaxes', u'define-unit', u'define-unit-binding',
        u'define-unit-from-context', u'define-unit/contract',
        u'define-unit/new-import-export', u'define-unit/s', u'define-values',
        u'define-values-for-export', u'define-values-for-syntax',
        u'define-values/invoke-unit', u'define-values/invoke-unit/infer',
        u'define/augment', u'define/augment-final', u'define/augride',
        u'define/contract', u'define/final-prop', u'define/match',
        u'define/overment', u'define/override', u'define/override-final',
        u'define/private', u'define/public', u'define/public-final',
        u'define/pubment', u'define/subexpression-pos-prop',
        u'define/subexpression-pos-prop/name', u'delay', u'delay/idle',
        u'delay/name', u'delay/strict', u'delay/sync', u'delay/thread', u'do',
        u'else', u'except', u'except-in', u'except-out', u'export', u'extends',
        u'failure-cont', u'false', u'false/c', u'field', u'field-bound?', u'file',
        u'flat-murec-contract', u'flat-rec-contract', u'for', u'for*', u'for*/and',
        u'for*/async', u'for*/first', u'for*/fold', u'for*/fold/derived',
        u'for*/hash', u'for*/hasheq', u'for*/hasheqv', u'for*/last', u'for*/list',
        u'for*/lists', u'for*/mutable-set', u'for*/mutable-seteq',
        u'for*/mutable-seteqv', u'for*/or', u'for*/product', u'for*/set',
        u'for*/seteq', u'for*/seteqv', u'for*/stream', u'for*/sum', u'for*/vector',
        u'for*/weak-set', u'for*/weak-seteq', u'for*/weak-seteqv', u'for-label',
        u'for-meta', u'for-syntax', u'for-template', u'for/and', u'for/async',
        u'for/first', u'for/fold', u'for/fold/derived', u'for/hash', u'for/hasheq',
        u'for/hasheqv', u'for/last', u'for/list', u'for/lists', u'for/mutable-set',
        u'for/mutable-seteq', u'for/mutable-seteqv', u'for/or', u'for/product',
        u'for/set', u'for/seteq', u'for/seteqv', u'for/stream', u'for/sum',
        u'for/vector', u'for/weak-set', u'for/weak-seteq', u'for/weak-seteqv',
        u'gen:custom-write', u'gen:dict', u'gen:equal+hash', u'gen:set',
        u'gen:stream', u'generic', u'get-field', u'hash/dc', u'if', u'implies',
        u'import', u'include', u'include-at/relative-to',
        u'include-at/relative-to/reader', u'include/reader', u'inherit',
        u'inherit-field', u'inherit/inner', u'inherit/super', u'init',
        u'init-depend', u'init-field', u'init-rest', u'inner', u'inspect',
        u'instantiate', u'interface', u'interface*', u'invariant-assertion',
        u'invoke-unit', u'invoke-unit/infer', u'lambda', u'lazy', u'let', u'let*',
        u'let*-values', u'let-syntax', u'let-syntaxes', u'let-values', u'let/cc',
        u'let/ec', u'letrec', u'letrec-syntax', u'letrec-syntaxes',
        u'letrec-syntaxes+values', u'letrec-values', u'lib', u'link', u'local',
        u'local-require', u'log-debug', u'log-error', u'log-fatal', u'log-info',
        u'log-warning', u'match', u'match*', u'match*/derived', u'match-define',
        u'match-define-values', u'match-lambda', u'match-lambda*',
        u'match-lambda**', u'match-let', u'match-let*', u'match-let*-values',
        u'match-let-values', u'match-letrec', u'match-letrec-values',
        u'match/derived', u'match/values', u'member-name-key', u'mixin', u'module',
        u'module*', u'module+', u'nand', u'new', u'nor', u'object-contract',
        u'object/c', u'only', u'only-in', u'only-meta-in', u'open', u'opt/c', u'or',
        u'overment', u'overment*', u'override', u'override*', u'override-final',
        u'override-final*', u'parameterize', u'parameterize*',
        u'parameterize-break', u'parametric->/c', u'place', u'place*',
        u'place/context', u'planet', u'prefix', u'prefix-in', u'prefix-out',
        u'private', u'private*', u'prompt-tag/c', u'protect-out', u'provide',
        u'provide-signature-elements', u'provide/contract', u'public', u'public*',
        u'public-final', u'public-final*', u'pubment', u'pubment*', u'quasiquote',
        u'quasisyntax', u'quasisyntax/loc', u'quote', u'quote-syntax',
        u'quote-syntax/prune', u'recontract-out', u'recursive-contract',
        u'relative-in', u'rename', u'rename-in', u'rename-inner', u'rename-out',
        u'rename-super', u'require', u'send', u'send*', u'send+', u'send-generic',
        u'send/apply', u'send/keyword-apply', u'set!', u'set!-values',
        u'set-field!', u'shared', u'stream', u'stream*', u'stream-cons', u'struct',
        u'struct*', u'struct-copy', u'struct-field-index', u'struct-out',
        u'struct/c', u'struct/ctc', u'struct/dc', u'submod', u'super',
        u'super-instantiate', u'super-make-object', u'super-new', u'syntax',
        u'syntax-case', u'syntax-case*', u'syntax-id-rules', u'syntax-rules',
        u'syntax/loc', u'tag', u'this', u'this%', u'thunk', u'thunk*', u'time',
        u'unconstrained-domain->', u'unit', u'unit-from-context', u'unit/c',
        u'unit/new-import-export', u'unit/s', u'unless', u'unquote',
        u'unquote-splicing', u'unsyntax', u'unsyntax-splicing', u'values/drop',
        u'when', u'with-continuation-mark', u'with-contract',
        u'with-contract-continuation-mark', u'with-handlers', u'with-handlers*',
        u'with-method', u'with-syntax', u'λ'
    )

    # Generated by example.rkt
    _builtins = (
        u'*', u'*list/c', u'+', u'-', u'/', u'<', u'</c', u'<=', u'<=/c', u'=', u'=/c',
        u'>', u'>/c', u'>=', u'>=/c', u'abort-current-continuation', u'abs',
        u'absolute-path?', u'acos', u'add-between', u'add1', u'alarm-evt',
        u'always-evt', u'and/c', u'andmap', u'angle', u'any/c', u'append', u'append*',
        u'append-map', u'apply', u'argmax', u'argmin', u'arithmetic-shift',
        u'arity-at-least', u'arity-at-least-value', u'arity-at-least?',
        u'arity-checking-wrapper', u'arity-includes?', u'arity=?',
        u'arrow-contract-info', u'arrow-contract-info-accepts-arglist',
        u'arrow-contract-info-chaperone-procedure',
        u'arrow-contract-info-check-first-order', u'arrow-contract-info?',
        u'asin', u'assf', u'assoc', u'assq', u'assv', u'atan',
        u'bad-number-of-results', u'banner', u'base->-doms/c', u'base->-rngs/c',
        u'base->?', u'between/c', u'bitwise-and', u'bitwise-bit-field',
        u'bitwise-bit-set?', u'bitwise-ior', u'bitwise-not', u'bitwise-xor',
        u'blame-add-car-context', u'blame-add-cdr-context', u'blame-add-context',
        u'blame-add-missing-party', u'blame-add-nth-arg-context',
        u'blame-add-range-context', u'blame-add-unknown-context',
        u'blame-context', u'blame-contract', u'blame-fmt->-string',
        u'blame-missing-party?', u'blame-negative', u'blame-original?',
        u'blame-positive', u'blame-replace-negative', u'blame-source',
        u'blame-swap', u'blame-swapped?', u'blame-update', u'blame-value',
        u'blame?', u'boolean=?', u'boolean?', u'bound-identifier=?', u'box',
        u'box-cas!', u'box-immutable', u'box-immutable/c', u'box/c', u'box?',
        u'break-enabled', u'break-parameterization?', u'break-thread',
        u'build-chaperone-contract-property', u'build-compound-type-name',
        u'build-contract-property', u'build-flat-contract-property',
        u'build-list', u'build-path', u'build-path/convention-type',
        u'build-string', u'build-vector', u'byte-pregexp', u'byte-pregexp?',
        u'byte-ready?', u'byte-regexp', u'byte-regexp?', u'byte?', u'bytes',
        u'bytes->immutable-bytes', u'bytes->list', u'bytes->path',
        u'bytes->path-element', u'bytes->string/latin-1', u'bytes->string/locale',
        u'bytes->string/utf-8', u'bytes-append', u'bytes-append*',
        u'bytes-close-converter', u'bytes-convert', u'bytes-convert-end',
        u'bytes-converter?', u'bytes-copy', u'bytes-copy!',
        u'bytes-environment-variable-name?', u'bytes-fill!', u'bytes-join',
        u'bytes-length', u'bytes-no-nuls?', u'bytes-open-converter', u'bytes-ref',
        u'bytes-set!', u'bytes-utf-8-index', u'bytes-utf-8-length',
        u'bytes-utf-8-ref', u'bytes<?', u'bytes=?', u'bytes>?', u'bytes?', u'caaaar',
        u'caaadr', u'caaar', u'caadar', u'caaddr', u'caadr', u'caar', u'cadaar',
        u'cadadr', u'cadar', u'caddar', u'cadddr', u'caddr', u'cadr',
        u'call-in-nested-thread', u'call-with-atomic-output-file',
        u'call-with-break-parameterization',
        u'call-with-composable-continuation', u'call-with-continuation-barrier',
        u'call-with-continuation-prompt', u'call-with-current-continuation',
        u'call-with-default-reading-parameterization',
        u'call-with-escape-continuation', u'call-with-exception-handler',
        u'call-with-file-lock/timeout', u'call-with-immediate-continuation-mark',
        u'call-with-input-bytes', u'call-with-input-file',
        u'call-with-input-file*', u'call-with-input-string',
        u'call-with-output-bytes', u'call-with-output-file',
        u'call-with-output-file*', u'call-with-output-string',
        u'call-with-parameterization', u'call-with-semaphore',
        u'call-with-semaphore/enable-break', u'call-with-values', u'call/cc',
        u'call/ec', u'car', u'cartesian-product', u'cdaaar', u'cdaadr', u'cdaar',
        u'cdadar', u'cdaddr', u'cdadr', u'cdar', u'cddaar', u'cddadr', u'cddar',
        u'cdddar', u'cddddr', u'cdddr', u'cddr', u'cdr', u'ceiling', u'channel-get',
        u'channel-put', u'channel-put-evt', u'channel-put-evt?',
        u'channel-try-get', u'channel/c', u'channel?', u'chaperone-box',
        u'chaperone-channel', u'chaperone-continuation-mark-key',
        u'chaperone-contract-property?', u'chaperone-contract?', u'chaperone-evt',
        u'chaperone-hash', u'chaperone-hash-set', u'chaperone-of?',
        u'chaperone-procedure', u'chaperone-procedure*', u'chaperone-prompt-tag',
        u'chaperone-struct', u'chaperone-struct-type', u'chaperone-vector',
        u'chaperone?', u'char->integer', u'char-alphabetic?', u'char-blank?',
        u'char-ci<=?', u'char-ci<?', u'char-ci=?', u'char-ci>=?', u'char-ci>?',
        u'char-downcase', u'char-foldcase', u'char-general-category',
        u'char-graphic?', u'char-in', u'char-in/c', u'char-iso-control?',
        u'char-lower-case?', u'char-numeric?', u'char-punctuation?',
        u'char-ready?', u'char-symbolic?', u'char-title-case?', u'char-titlecase',
        u'char-upcase', u'char-upper-case?', u'char-utf-8-length',
        u'char-whitespace?', u'char<=?', u'char<?', u'char=?', u'char>=?', u'char>?',
        u'char?', u'check-duplicate-identifier', u'check-duplicates',
        u'checked-procedure-check-and-extract', u'choice-evt',
        u'class->interface', u'class-info', u'class-seal', u'class-unseal',
        u'class?', u'cleanse-path', u'close-input-port', u'close-output-port',
        u'coerce-chaperone-contract', u'coerce-chaperone-contracts',
        u'coerce-contract', u'coerce-contract/f', u'coerce-contracts',
        u'coerce-flat-contract', u'coerce-flat-contracts', u'collect-garbage',
        u'collection-file-path', u'collection-path', u'combinations', u'compile',
        u'compile-allow-set!-undefined', u'compile-context-preservation-enabled',
        u'compile-enforce-module-constants', u'compile-syntax',
        u'compiled-expression-recompile', u'compiled-expression?',
        u'compiled-module-expression?', u'complete-path?', u'complex?', u'compose',
        u'compose1', u'conjoin', u'conjugate', u'cons', u'cons/c', u'cons?', u'const',
        u'continuation-mark-key/c', u'continuation-mark-key?',
        u'continuation-mark-set->context', u'continuation-mark-set->list',
        u'continuation-mark-set->list*', u'continuation-mark-set-first',
        u'continuation-mark-set?', u'continuation-marks',
        u'continuation-prompt-available?', u'continuation-prompt-tag?',
        u'continuation?', u'contract-continuation-mark-key',
        u'contract-custom-write-property-proc', u'contract-exercise',
        u'contract-first-order', u'contract-first-order-passes?',
        u'contract-late-neg-projection', u'contract-name', u'contract-proc',
        u'contract-projection', u'contract-property?',
        u'contract-random-generate', u'contract-random-generate-fail',
        u'contract-random-generate-fail?',
        u'contract-random-generate-get-current-environment',
        u'contract-random-generate-stash', u'contract-random-generate/choose',
        u'contract-stronger?', u'contract-struct-exercise',
        u'contract-struct-generate', u'contract-struct-late-neg-projection',
        u'contract-struct-list-contract?', u'contract-val-first-projection',
        u'contract?', u'convert-stream', u'copy-directory/files', u'copy-file',
        u'copy-port', u'cos', u'cosh', u'count', u'current-blame-format',
        u'current-break-parameterization', u'current-code-inspector',
        u'current-command-line-arguments', u'current-compile',
        u'current-compiled-file-roots', u'current-continuation-marks',
        u'current-contract-region', u'current-custodian', u'current-directory',
        u'current-directory-for-user', u'current-drive',
        u'current-environment-variables', u'current-error-port', u'current-eval',
        u'current-evt-pseudo-random-generator',
        u'current-force-delete-permissions', u'current-future',
        u'current-gc-milliseconds', u'current-get-interaction-input-port',
        u'current-inexact-milliseconds', u'current-input-port',
        u'current-inspector', u'current-library-collection-links',
        u'current-library-collection-paths', u'current-load',
        u'current-load-extension', u'current-load-relative-directory',
        u'current-load/use-compiled', u'current-locale', u'current-logger',
        u'current-memory-use', u'current-milliseconds',
        u'current-module-declare-name', u'current-module-declare-source',
        u'current-module-name-resolver', u'current-module-path-for-load',
        u'current-namespace', u'current-output-port', u'current-parameterization',
        u'current-plumber', u'current-preserved-thread-cell-values',
        u'current-print', u'current-process-milliseconds', u'current-prompt-read',
        u'current-pseudo-random-generator', u'current-read-interaction',
        u'current-reader-guard', u'current-readtable', u'current-seconds',
        u'current-security-guard', u'current-subprocess-custodian-mode',
        u'current-thread', u'current-thread-group',
        u'current-thread-initial-stack-size',
        u'current-write-relative-directory', u'curry', u'curryr',
        u'custodian-box-value', u'custodian-box?', u'custodian-limit-memory',
        u'custodian-managed-list', u'custodian-memory-accounting-available?',
        u'custodian-require-memory', u'custodian-shutdown-all', u'custodian?',
        u'custom-print-quotable-accessor', u'custom-print-quotable?',
        u'custom-write-accessor', u'custom-write-property-proc', u'custom-write?',
        u'date', u'date*', u'date*-nanosecond', u'date*-time-zone-name', u'date*?',
        u'date-day', u'date-dst?', u'date-hour', u'date-minute', u'date-month',
        u'date-second', u'date-time-zone-offset', u'date-week-day', u'date-year',
        u'date-year-day', u'date?', u'datum->syntax', u'datum-intern-literal',
        u'default-continuation-prompt-tag', u'degrees->radians',
        u'delete-directory', u'delete-directory/files', u'delete-file',
        u'denominator', u'dict->list', u'dict-can-functional-set?',
        u'dict-can-remove-keys?', u'dict-clear', u'dict-clear!', u'dict-copy',
        u'dict-count', u'dict-empty?', u'dict-for-each', u'dict-has-key?',
        u'dict-implements/c', u'dict-implements?', u'dict-iter-contract',
        u'dict-iterate-first', u'dict-iterate-key', u'dict-iterate-next',
        u'dict-iterate-value', u'dict-key-contract', u'dict-keys', u'dict-map',
        u'dict-mutable?', u'dict-ref', u'dict-ref!', u'dict-remove',
        u'dict-remove!', u'dict-set', u'dict-set!', u'dict-set*', u'dict-set*!',
        u'dict-update', u'dict-update!', u'dict-value-contract', u'dict-values',
        u'dict?', u'directory-exists?', u'directory-list', u'disjoin', u'display',
        u'display-lines', u'display-lines-to-file', u'display-to-file',
        u'displayln', u'double-flonum?', u'drop', u'drop-common-prefix',
        u'drop-right', u'dropf', u'dropf-right', u'dump-memory-stats',
        u'dup-input-port', u'dup-output-port', u'dynamic->*', u'dynamic-get-field',
        u'dynamic-object/c', u'dynamic-place', u'dynamic-place*',
        u'dynamic-require', u'dynamic-require-for-syntax', u'dynamic-send',
        u'dynamic-set-field!', u'dynamic-wind', u'eighth', u'empty',
        u'empty-sequence', u'empty-stream', u'empty?',
        u'environment-variables-copy', u'environment-variables-names',
        u'environment-variables-ref', u'environment-variables-set!',
        u'environment-variables?', u'eof', u'eof-evt', u'eof-object?',
        u'ephemeron-value', u'ephemeron?', u'eprintf', u'eq-contract-val',
        u'eq-contract?', u'eq-hash-code', u'eq?', u'equal-contract-val',
        u'equal-contract?', u'equal-hash-code', u'equal-secondary-hash-code',
        u'equal<%>', u'equal?', u'equal?/recur', u'eqv-hash-code', u'eqv?', u'error',
        u'error-display-handler', u'error-escape-handler',
        u'error-print-context-length', u'error-print-source-location',
        u'error-print-width', u'error-value->string-handler', u'eval',
        u'eval-jit-enabled', u'eval-syntax', u'even?', u'evt/c', u'evt?',
        u'exact->inexact', u'exact-ceiling', u'exact-floor', u'exact-integer?',
        u'exact-nonnegative-integer?', u'exact-positive-integer?', u'exact-round',
        u'exact-truncate', u'exact?', u'executable-yield-handler', u'exit',
        u'exit-handler', u'exn', u'exn-continuation-marks', u'exn-message',
        u'exn:break', u'exn:break-continuation', u'exn:break:hang-up',
        u'exn:break:hang-up?', u'exn:break:terminate', u'exn:break:terminate?',
        u'exn:break?', u'exn:fail', u'exn:fail:contract',
        u'exn:fail:contract:arity', u'exn:fail:contract:arity?',
        u'exn:fail:contract:blame', u'exn:fail:contract:blame-object',
        u'exn:fail:contract:blame?', u'exn:fail:contract:continuation',
        u'exn:fail:contract:continuation?', u'exn:fail:contract:divide-by-zero',
        u'exn:fail:contract:divide-by-zero?',
        u'exn:fail:contract:non-fixnum-result',
        u'exn:fail:contract:non-fixnum-result?', u'exn:fail:contract:variable',
        u'exn:fail:contract:variable-id', u'exn:fail:contract:variable?',
        u'exn:fail:contract?', u'exn:fail:filesystem',
        u'exn:fail:filesystem:errno', u'exn:fail:filesystem:errno-errno',
        u'exn:fail:filesystem:errno?', u'exn:fail:filesystem:exists',
        u'exn:fail:filesystem:exists?', u'exn:fail:filesystem:missing-module',
        u'exn:fail:filesystem:missing-module-path',
        u'exn:fail:filesystem:missing-module?', u'exn:fail:filesystem:version',
        u'exn:fail:filesystem:version?', u'exn:fail:filesystem?',
        u'exn:fail:network', u'exn:fail:network:errno',
        u'exn:fail:network:errno-errno', u'exn:fail:network:errno?',
        u'exn:fail:network?', u'exn:fail:object', u'exn:fail:object?',
        u'exn:fail:out-of-memory', u'exn:fail:out-of-memory?', u'exn:fail:read',
        u'exn:fail:read-srclocs', u'exn:fail:read:eof', u'exn:fail:read:eof?',
        u'exn:fail:read:non-char', u'exn:fail:read:non-char?', u'exn:fail:read?',
        u'exn:fail:syntax', u'exn:fail:syntax-exprs',
        u'exn:fail:syntax:missing-module',
        u'exn:fail:syntax:missing-module-path',
        u'exn:fail:syntax:missing-module?', u'exn:fail:syntax:unbound',
        u'exn:fail:syntax:unbound?', u'exn:fail:syntax?', u'exn:fail:unsupported',
        u'exn:fail:unsupported?', u'exn:fail:user', u'exn:fail:user?',
        u'exn:fail?', u'exn:misc:match?', u'exn:missing-module-accessor',
        u'exn:missing-module?', u'exn:srclocs-accessor', u'exn:srclocs?', u'exn?',
        u'exp', u'expand', u'expand-once', u'expand-syntax', u'expand-syntax-once',
        u'expand-syntax-to-top-form', u'expand-to-top-form', u'expand-user-path',
        u'explode-path', u'expt', u'externalizable<%>', u'failure-result/c',
        u'false?', u'field-names', u'fifth', u'file->bytes', u'file->bytes-lines',
        u'file->lines', u'file->list', u'file->string', u'file->value',
        u'file-exists?', u'file-name-from-path', u'file-or-directory-identity',
        u'file-or-directory-modify-seconds', u'file-or-directory-permissions',
        u'file-position', u'file-position*', u'file-size',
        u'file-stream-buffer-mode', u'file-stream-port?', u'file-truncate',
        u'filename-extension', u'filesystem-change-evt',
        u'filesystem-change-evt-cancel', u'filesystem-change-evt?',
        u'filesystem-root-list', u'filter', u'filter-map', u'filter-not',
        u'filter-read-input-port', u'find-executable-path', u'find-files',
        u'find-library-collection-links', u'find-library-collection-paths',
        u'find-relative-path', u'find-system-path', u'findf', u'first',
        u'first-or/c', u'fixnum?', u'flat-contract', u'flat-contract-predicate',
        u'flat-contract-property?', u'flat-contract?', u'flat-named-contract',
        u'flatten', u'floating-point-bytes->real', u'flonum?', u'floor',
        u'flush-output', u'fold-files', u'foldl', u'foldr', u'for-each', u'force',
        u'format', u'fourth', u'fprintf', u'free-identifier=?',
        u'free-label-identifier=?', u'free-template-identifier=?',
        u'free-transformer-identifier=?', u'fsemaphore-count', u'fsemaphore-post',
        u'fsemaphore-try-wait?', u'fsemaphore-wait', u'fsemaphore?', u'future',
        u'future?', u'futures-enabled?', u'gcd', u'generate-member-key',
        u'generate-temporaries', u'generic-set?', u'generic?', u'gensym',
        u'get-output-bytes', u'get-output-string', u'get-preference',
        u'get/build-late-neg-projection', u'get/build-val-first-projection',
        u'getenv', u'global-port-print-handler', u'group-by', u'group-execute-bit',
        u'group-read-bit', u'group-write-bit', u'guard-evt', u'handle-evt',
        u'handle-evt?', u'has-blame?', u'has-contract?', u'hash', u'hash->list',
        u'hash-clear', u'hash-clear!', u'hash-copy', u'hash-copy-clear',
        u'hash-count', u'hash-empty?', u'hash-eq?', u'hash-equal?', u'hash-eqv?',
        u'hash-for-each', u'hash-has-key?', u'hash-iterate-first',
        u'hash-iterate-key', u'hash-iterate-key+value', u'hash-iterate-next',
        u'hash-iterate-pair', u'hash-iterate-value', u'hash-keys', u'hash-map',
        u'hash-placeholder?', u'hash-ref', u'hash-ref!', u'hash-remove',
        u'hash-remove!', u'hash-set', u'hash-set!', u'hash-set*', u'hash-set*!',
        u'hash-update', u'hash-update!', u'hash-values', u'hash-weak?', u'hash/c',
        u'hash?', u'hasheq', u'hasheqv', u'identifier-binding',
        u'identifier-binding-symbol', u'identifier-label-binding',
        u'identifier-prune-lexical-context',
        u'identifier-prune-to-source-module',
        u'identifier-remove-from-definition-context',
        u'identifier-template-binding', u'identifier-transformer-binding',
        u'identifier?', u'identity', u'if/c', u'imag-part', u'immutable?',
        u'impersonate-box', u'impersonate-channel',
        u'impersonate-continuation-mark-key', u'impersonate-hash',
        u'impersonate-hash-set', u'impersonate-procedure',
        u'impersonate-procedure*', u'impersonate-prompt-tag',
        u'impersonate-struct', u'impersonate-vector', u'impersonator-contract?',
        u'impersonator-ephemeron', u'impersonator-of?',
        u'impersonator-prop:application-mark', u'impersonator-prop:blame',
        u'impersonator-prop:contracted',
        u'impersonator-property-accessor-procedure?', u'impersonator-property?',
        u'impersonator?', u'implementation?', u'implementation?/c', u'in-bytes',
        u'in-bytes-lines', u'in-combinations', u'in-cycle', u'in-dict',
        u'in-dict-keys', u'in-dict-pairs', u'in-dict-values', u'in-directory',
        u'in-hash', u'in-hash-keys', u'in-hash-pairs', u'in-hash-values',
        u'in-immutable-hash', u'in-immutable-hash-keys',
        u'in-immutable-hash-pairs', u'in-immutable-hash-values',
        u'in-immutable-set', u'in-indexed', u'in-input-port-bytes',
        u'in-input-port-chars', u'in-lines', u'in-list', u'in-mlist',
        u'in-mutable-hash', u'in-mutable-hash-keys', u'in-mutable-hash-pairs',
        u'in-mutable-hash-values', u'in-mutable-set', u'in-naturals',
        u'in-parallel', u'in-permutations', u'in-port', u'in-producer', u'in-range',
        u'in-sequences', u'in-set', u'in-slice', u'in-stream', u'in-string',
        u'in-syntax', u'in-value', u'in-values*-sequence', u'in-values-sequence',
        u'in-vector', u'in-weak-hash', u'in-weak-hash-keys', u'in-weak-hash-pairs',
        u'in-weak-hash-values', u'in-weak-set', u'inexact->exact',
        u'inexact-real?', u'inexact?', u'infinite?', u'input-port-append',
        u'input-port?', u'inspector?', u'instanceof/c', u'integer->char',
        u'integer->integer-bytes', u'integer-bytes->integer', u'integer-in',
        u'integer-length', u'integer-sqrt', u'integer-sqrt/remainder', u'integer?',
        u'interface->method-names', u'interface-extension?', u'interface?',
        u'internal-definition-context-binding-identifiers',
        u'internal-definition-context-introduce',
        u'internal-definition-context-seal', u'internal-definition-context?',
        u'is-a?', u'is-a?/c', u'keyword->string', u'keyword-apply', u'keyword<?',
        u'keyword?', u'keywords-match', u'kill-thread', u'last', u'last-pair',
        u'lcm', u'length', u'liberal-define-context?', u'link-exists?', u'list',
        u'list*', u'list*of', u'list->bytes', u'list->mutable-set',
        u'list->mutable-seteq', u'list->mutable-seteqv', u'list->set',
        u'list->seteq', u'list->seteqv', u'list->string', u'list->vector',
        u'list->weak-set', u'list->weak-seteq', u'list->weak-seteqv',
        u'list-contract?', u'list-prefix?', u'list-ref', u'list-set', u'list-tail',
        u'list-update', u'list/c', u'list?', u'listen-port-number?', u'listof',
        u'load', u'load-extension', u'load-on-demand-enabled', u'load-relative',
        u'load-relative-extension', u'load/cd', u'load/use-compiled',
        u'local-expand', u'local-expand/capture-lifts',
        u'local-transformer-expand', u'local-transformer-expand/capture-lifts',
        u'locale-string-encoding', u'log', u'log-all-levels', u'log-level-evt',
        u'log-level?', u'log-max-level', u'log-message', u'log-receiver?',
        u'logger-name', u'logger?', u'magnitude', u'make-arity-at-least',
        u'make-base-empty-namespace', u'make-base-namespace', u'make-bytes',
        u'make-channel', u'make-chaperone-contract',
        u'make-continuation-mark-key', u'make-continuation-prompt-tag',
        u'make-contract', u'make-custodian', u'make-custodian-box',
        u'make-custom-hash', u'make-custom-hash-types', u'make-custom-set',
        u'make-custom-set-types', u'make-date', u'make-date*',
        u'make-derived-parameter', u'make-directory', u'make-directory*',
        u'make-do-sequence', u'make-empty-namespace',
        u'make-environment-variables', u'make-ephemeron', u'make-exn',
        u'make-exn:break', u'make-exn:break:hang-up', u'make-exn:break:terminate',
        u'make-exn:fail', u'make-exn:fail:contract',
        u'make-exn:fail:contract:arity', u'make-exn:fail:contract:blame',
        u'make-exn:fail:contract:continuation',
        u'make-exn:fail:contract:divide-by-zero',
        u'make-exn:fail:contract:non-fixnum-result',
        u'make-exn:fail:contract:variable', u'make-exn:fail:filesystem',
        u'make-exn:fail:filesystem:errno', u'make-exn:fail:filesystem:exists',
        u'make-exn:fail:filesystem:missing-module',
        u'make-exn:fail:filesystem:version', u'make-exn:fail:network',
        u'make-exn:fail:network:errno', u'make-exn:fail:object',
        u'make-exn:fail:out-of-memory', u'make-exn:fail:read',
        u'make-exn:fail:read:eof', u'make-exn:fail:read:non-char',
        u'make-exn:fail:syntax', u'make-exn:fail:syntax:missing-module',
        u'make-exn:fail:syntax:unbound', u'make-exn:fail:unsupported',
        u'make-exn:fail:user', u'make-file-or-directory-link',
        u'make-flat-contract', u'make-fsemaphore', u'make-generic',
        u'make-handle-get-preference-locked', u'make-hash',
        u'make-hash-placeholder', u'make-hasheq', u'make-hasheq-placeholder',
        u'make-hasheqv', u'make-hasheqv-placeholder',
        u'make-immutable-custom-hash', u'make-immutable-hash',
        u'make-immutable-hasheq', u'make-immutable-hasheqv',
        u'make-impersonator-property', u'make-input-port',
        u'make-input-port/read-to-peek', u'make-inspector',
        u'make-keyword-procedure', u'make-known-char-range-list',
        u'make-limited-input-port', u'make-list', u'make-lock-file-name',
        u'make-log-receiver', u'make-logger', u'make-mixin-contract',
        u'make-mutable-custom-set', u'make-none/c', u'make-object',
        u'make-output-port', u'make-parameter', u'make-parent-directory*',
        u'make-phantom-bytes', u'make-pipe', u'make-pipe-with-specials',
        u'make-placeholder', u'make-plumber', u'make-polar', u'make-prefab-struct',
        u'make-primitive-class', u'make-proj-contract',
        u'make-pseudo-random-generator', u'make-reader-graph', u'make-readtable',
        u'make-rectangular', u'make-rename-transformer',
        u'make-resolved-module-path', u'make-security-guard', u'make-semaphore',
        u'make-set!-transformer', u'make-shared-bytes', u'make-sibling-inspector',
        u'make-special-comment', u'make-srcloc', u'make-string',
        u'make-struct-field-accessor', u'make-struct-field-mutator',
        u'make-struct-type', u'make-struct-type-property',
        u'make-syntax-delta-introducer', u'make-syntax-introducer',
        u'make-temporary-file', u'make-tentative-pretty-print-output-port',
        u'make-thread-cell', u'make-thread-group', u'make-vector',
        u'make-weak-box', u'make-weak-custom-hash', u'make-weak-custom-set',
        u'make-weak-hash', u'make-weak-hasheq', u'make-weak-hasheqv',
        u'make-will-executor', u'map', u'match-equality-test',
        u'matches-arity-exactly?', u'max', u'mcar', u'mcdr', u'mcons', u'member',
        u'member-name-key-hash-code', u'member-name-key=?', u'member-name-key?',
        u'memf', u'memq', u'memv', u'merge-input', u'method-in-interface?', u'min',
        u'mixin-contract', u'module->exports', u'module->imports',
        u'module->language-info', u'module->namespace',
        u'module-compiled-cross-phase-persistent?', u'module-compiled-exports',
        u'module-compiled-imports', u'module-compiled-language-info',
        u'module-compiled-name', u'module-compiled-submodules',
        u'module-declared?', u'module-path-index-join',
        u'module-path-index-resolve', u'module-path-index-split',
        u'module-path-index-submodule', u'module-path-index?', u'module-path?',
        u'module-predefined?', u'module-provide-protected?', u'modulo', u'mpair?',
        u'mutable-set', u'mutable-seteq', u'mutable-seteqv', u'n->th',
        u'nack-guard-evt', u'namespace-anchor->empty-namespace',
        u'namespace-anchor->namespace', u'namespace-anchor?',
        u'namespace-attach-module', u'namespace-attach-module-declaration',
        u'namespace-base-phase', u'namespace-mapped-symbols',
        u'namespace-module-identifier', u'namespace-module-registry',
        u'namespace-require', u'namespace-require/constant',
        u'namespace-require/copy', u'namespace-require/expansion-time',
        u'namespace-set-variable-value!', u'namespace-symbol->identifier',
        u'namespace-syntax-introduce', u'namespace-undefine-variable!',
        u'namespace-unprotect-module', u'namespace-variable-value', u'namespace?',
        u'nan?', u'natural-number/c', u'negate', u'negative?', u'never-evt',
        u'new-∀/c', u'new-∃/c', u'newline', u'ninth', u'non-empty-listof',
        u'non-empty-string?', u'none/c', u'normal-case-path', u'normalize-arity',
        u'normalize-path', u'normalized-arity?', u'not', u'not/c', u'null', u'null?',
        u'number->string', u'number?', u'numerator', u'object%', u'object->vector',
        u'object-info', u'object-interface', u'object-method-arity-includes?',
        u'object-name', u'object-or-false=?', u'object=?', u'object?', u'odd?',
        u'one-of/c', u'open-input-bytes', u'open-input-file',
        u'open-input-output-file', u'open-input-string', u'open-output-bytes',
        u'open-output-file', u'open-output-nowhere', u'open-output-string',
        u'or/c', u'order-of-magnitude', u'ormap', u'other-execute-bit',
        u'other-read-bit', u'other-write-bit', u'output-port?', u'pair?',
        u'parameter-procedure=?', u'parameter/c', u'parameter?',
        u'parameterization?', u'parse-command-line', u'partition', u'path->bytes',
        u'path->complete-path', u'path->directory-path', u'path->string',
        u'path-add-suffix', u'path-convention-type', u'path-element->bytes',
        u'path-element->string', u'path-element?', u'path-for-some-system?',
        u'path-list-string->path-list', u'path-only', u'path-replace-suffix',
        u'path-string?', u'path<?', u'path?', u'pathlist-closure', u'peek-byte',
        u'peek-byte-or-special', u'peek-bytes', u'peek-bytes!', u'peek-bytes!-evt',
        u'peek-bytes-avail!', u'peek-bytes-avail!*', u'peek-bytes-avail!-evt',
        u'peek-bytes-avail!/enable-break', u'peek-bytes-evt', u'peek-char',
        u'peek-char-or-special', u'peek-string', u'peek-string!',
        u'peek-string!-evt', u'peek-string-evt', u'peeking-input-port',
        u'permutations', u'phantom-bytes?', u'pi', u'pi.f', u'pipe-content-length',
        u'place-break', u'place-channel', u'place-channel-get',
        u'place-channel-put', u'place-channel-put/get', u'place-channel?',
        u'place-dead-evt', u'place-enabled?', u'place-kill', u'place-location?',
        u'place-message-allowed?', u'place-sleep', u'place-wait', u'place?',
        u'placeholder-get', u'placeholder-set!', u'placeholder?',
        u'plumber-add-flush!', u'plumber-flush-all',
        u'plumber-flush-handle-remove!', u'plumber-flush-handle?', u'plumber?',
        u'poll-guard-evt', u'port->bytes', u'port->bytes-lines', u'port->lines',
        u'port->list', u'port->string', u'port-closed-evt', u'port-closed?',
        u'port-commit-peeked', u'port-count-lines!', u'port-count-lines-enabled',
        u'port-counts-lines?', u'port-display-handler', u'port-file-identity',
        u'port-file-unlock', u'port-next-location', u'port-number?',
        u'port-print-handler', u'port-progress-evt',
        u'port-provides-progress-evts?', u'port-read-handler',
        u'port-try-file-lock?', u'port-write-handler', u'port-writes-atomic?',
        u'port-writes-special?', u'port?', u'positive?', u'predicate/c',
        u'prefab-key->struct-type', u'prefab-key?', u'prefab-struct-key',
        u'preferences-lock-file-mode', u'pregexp', u'pregexp?', u'pretty-display',
        u'pretty-format', u'pretty-print', u'pretty-print-.-symbol-without-bars',
        u'pretty-print-abbreviate-read-macros', u'pretty-print-columns',
        u'pretty-print-current-style-table', u'pretty-print-depth',
        u'pretty-print-exact-as-decimal', u'pretty-print-extend-style-table',
        u'pretty-print-handler', u'pretty-print-newline',
        u'pretty-print-post-print-hook', u'pretty-print-pre-print-hook',
        u'pretty-print-print-hook', u'pretty-print-print-line',
        u'pretty-print-remap-stylable', u'pretty-print-show-inexactness',
        u'pretty-print-size-hook', u'pretty-print-style-table?',
        u'pretty-printing', u'pretty-write', u'primitive-closure?',
        u'primitive-result-arity', u'primitive?', u'print', u'print-as-expression',
        u'print-boolean-long-form', u'print-box', u'print-graph',
        u'print-hash-table', u'print-mpair-curly-braces',
        u'print-pair-curly-braces', u'print-reader-abbreviations',
        u'print-struct', u'print-syntax-width', u'print-unreadable',
        u'print-vector-length', u'printable/c', u'printable<%>', u'printf',
        u'println', u'procedure->method', u'procedure-arity',
        u'procedure-arity-includes/c', u'procedure-arity-includes?',
        u'procedure-arity?', u'procedure-closure-contents-eq?',
        u'procedure-extract-target', u'procedure-keywords',
        u'procedure-reduce-arity', u'procedure-reduce-keyword-arity',
        u'procedure-rename', u'procedure-result-arity', u'procedure-specialize',
        u'procedure-struct-type?', u'procedure?', u'process', u'process*',
        u'process*/ports', u'process/ports', u'processor-count', u'progress-evt?',
        u'promise-forced?', u'promise-running?', u'promise/c', u'promise/name?',
        u'promise?', u'prop:arity-string', u'prop:arrow-contract',
        u'prop:arrow-contract-get-info', u'prop:arrow-contract?', u'prop:blame',
        u'prop:chaperone-contract', u'prop:checked-procedure', u'prop:contract',
        u'prop:contracted', u'prop:custom-print-quotable', u'prop:custom-write',
        u'prop:dict', u'prop:dict/contract', u'prop:equal+hash', u'prop:evt',
        u'prop:exn:missing-module', u'prop:exn:srclocs',
        u'prop:expansion-contexts', u'prop:flat-contract',
        u'prop:impersonator-of', u'prop:input-port',
        u'prop:liberal-define-context', u'prop:object-name',
        u'prop:opt-chaperone-contract', u'prop:opt-chaperone-contract-get-test',
        u'prop:opt-chaperone-contract?', u'prop:orc-contract',
        u'prop:orc-contract-get-subcontracts', u'prop:orc-contract?',
        u'prop:output-port', u'prop:place-location', u'prop:procedure',
        u'prop:recursive-contract', u'prop:recursive-contract-unroll',
        u'prop:recursive-contract?', u'prop:rename-transformer', u'prop:sequence',
        u'prop:set!-transformer', u'prop:stream', u'proper-subset?',
        u'pseudo-random-generator->vector', u'pseudo-random-generator-vector?',
        u'pseudo-random-generator?', u'put-preferences', u'putenv', u'quotient',
        u'quotient/remainder', u'radians->degrees', u'raise',
        u'raise-argument-error', u'raise-arguments-error', u'raise-arity-error',
        u'raise-blame-error', u'raise-contract-error', u'raise-mismatch-error',
        u'raise-not-cons-blame-error', u'raise-range-error',
        u'raise-result-error', u'raise-syntax-error', u'raise-type-error',
        u'raise-user-error', u'random', u'random-seed', u'range', u'rational?',
        u'rationalize', u'read', u'read-accept-bar-quote', u'read-accept-box',
        u'read-accept-compiled', u'read-accept-dot', u'read-accept-graph',
        u'read-accept-infix-dot', u'read-accept-lang', u'read-accept-quasiquote',
        u'read-accept-reader', u'read-byte', u'read-byte-or-special',
        u'read-bytes', u'read-bytes!', u'read-bytes!-evt', u'read-bytes-avail!',
        u'read-bytes-avail!*', u'read-bytes-avail!-evt',
        u'read-bytes-avail!/enable-break', u'read-bytes-evt', u'read-bytes-line',
        u'read-bytes-line-evt', u'read-case-sensitive', u'read-cdot', u'read-char',
        u'read-char-or-special', u'read-curly-brace-as-paren',
        u'read-curly-brace-with-tag', u'read-decimal-as-inexact',
        u'read-eval-print-loop', u'read-language', u'read-line', u'read-line-evt',
        u'read-on-demand-source', u'read-square-bracket-as-paren',
        u'read-square-bracket-with-tag', u'read-string', u'read-string!',
        u'read-string!-evt', u'read-string-evt', u'read-syntax',
        u'read-syntax/recursive', u'read/recursive', u'readtable-mapping',
        u'readtable?', u'real->decimal-string', u'real->double-flonum',
        u'real->floating-point-bytes', u'real->single-flonum', u'real-in',
        u'real-part', u'real?', u'reencode-input-port', u'reencode-output-port',
        u'regexp', u'regexp-match', u'regexp-match*', u'regexp-match-evt',
        u'regexp-match-exact?', u'regexp-match-peek',
        u'regexp-match-peek-immediate', u'regexp-match-peek-positions',
        u'regexp-match-peek-positions*',
        u'regexp-match-peek-positions-immediate',
        u'regexp-match-peek-positions-immediate/end',
        u'regexp-match-peek-positions/end', u'regexp-match-positions',
        u'regexp-match-positions*', u'regexp-match-positions/end',
        u'regexp-match/end', u'regexp-match?', u'regexp-max-lookbehind',
        u'regexp-quote', u'regexp-replace', u'regexp-replace*',
        u'regexp-replace-quote', u'regexp-replaces', u'regexp-split',
        u'regexp-try-match', u'regexp?', u'relative-path?', u'relocate-input-port',
        u'relocate-output-port', u'remainder', u'remf', u'remf*', u'remove',
        u'remove*', u'remove-duplicates', u'remq', u'remq*', u'remv', u'remv*',
        u'rename-contract', u'rename-file-or-directory',
        u'rename-transformer-target', u'rename-transformer?', u'replace-evt',
        u'reroot-path', u'resolve-path', u'resolved-module-path-name',
        u'resolved-module-path?', u'rest', u'reverse', u'round', u'second',
        u'seconds->date', u'security-guard?', u'semaphore-peek-evt',
        u'semaphore-peek-evt?', u'semaphore-post', u'semaphore-try-wait?',
        u'semaphore-wait', u'semaphore-wait/enable-break', u'semaphore?',
        u'sequence->list', u'sequence->stream', u'sequence-add-between',
        u'sequence-andmap', u'sequence-append', u'sequence-count',
        u'sequence-filter', u'sequence-fold', u'sequence-for-each',
        u'sequence-generate', u'sequence-generate*', u'sequence-length',
        u'sequence-map', u'sequence-ormap', u'sequence-ref', u'sequence-tail',
        u'sequence/c', u'sequence?', u'set', u'set!-transformer-procedure',
        u'set!-transformer?', u'set->list', u'set->stream', u'set-add', u'set-add!',
        u'set-box!', u'set-clear', u'set-clear!', u'set-copy', u'set-copy-clear',
        u'set-count', u'set-empty?', u'set-eq?', u'set-equal?', u'set-eqv?',
        u'set-first', u'set-for-each', u'set-implements/c', u'set-implements?',
        u'set-intersect', u'set-intersect!', u'set-map', u'set-mcar!', u'set-mcdr!',
        u'set-member?', u'set-mutable?', u'set-phantom-bytes!',
        u'set-port-next-location!', u'set-remove', u'set-remove!', u'set-rest',
        u'set-some-basic-contracts!', u'set-subtract', u'set-subtract!',
        u'set-symmetric-difference', u'set-symmetric-difference!', u'set-union',
        u'set-union!', u'set-weak?', u'set/c', u'set=?', u'set?', u'seteq', u'seteqv',
        u'seventh', u'sgn', u'shared-bytes', u'shell-execute', u'shrink-path-wrt',
        u'shuffle', u'simple-form-path', u'simplify-path', u'sin',
        u'single-flonum?', u'sinh', u'sixth', u'skip-projection-wrapper?', u'sleep',
        u'some-system-path->string', u'sort', u'special-comment-value',
        u'special-comment?', u'special-filter-input-port', u'split-at',
        u'split-at-right', u'split-common-prefix', u'split-path', u'splitf-at',
        u'splitf-at-right', u'sqr', u'sqrt', u'srcloc', u'srcloc->string',
        u'srcloc-column', u'srcloc-line', u'srcloc-position', u'srcloc-source',
        u'srcloc-span', u'srcloc?', u'stop-after', u'stop-before', u'stream->list',
        u'stream-add-between', u'stream-andmap', u'stream-append', u'stream-count',
        u'stream-empty?', u'stream-filter', u'stream-first', u'stream-fold',
        u'stream-for-each', u'stream-length', u'stream-map', u'stream-ormap',
        u'stream-ref', u'stream-rest', u'stream-tail', u'stream/c', u'stream?',
        u'string', u'string->bytes/latin-1', u'string->bytes/locale',
        u'string->bytes/utf-8', u'string->immutable-string', u'string->keyword',
        u'string->list', u'string->number', u'string->path',
        u'string->path-element', u'string->some-system-path', u'string->symbol',
        u'string->uninterned-symbol', u'string->unreadable-symbol',
        u'string-append', u'string-append*', u'string-ci<=?', u'string-ci<?',
        u'string-ci=?', u'string-ci>=?', u'string-ci>?', u'string-contains?',
        u'string-copy', u'string-copy!', u'string-downcase',
        u'string-environment-variable-name?', u'string-fill!', u'string-foldcase',
        u'string-join', u'string-len/c', u'string-length', u'string-locale-ci<?',
        u'string-locale-ci=?', u'string-locale-ci>?', u'string-locale-downcase',
        u'string-locale-upcase', u'string-locale<?', u'string-locale=?',
        u'string-locale>?', u'string-no-nuls?', u'string-normalize-nfc',
        u'string-normalize-nfd', u'string-normalize-nfkc',
        u'string-normalize-nfkd', u'string-normalize-spaces', u'string-port?',
        u'string-prefix?', u'string-ref', u'string-replace', u'string-set!',
        u'string-split', u'string-suffix?', u'string-titlecase', u'string-trim',
        u'string-upcase', u'string-utf-8-length', u'string<=?', u'string<?',
        u'string=?', u'string>=?', u'string>?', u'string?', u'struct->vector',
        u'struct-accessor-procedure?', u'struct-constructor-procedure?',
        u'struct-info', u'struct-mutator-procedure?',
        u'struct-predicate-procedure?', u'struct-type-info',
        u'struct-type-make-constructor', u'struct-type-make-predicate',
        u'struct-type-property-accessor-procedure?', u'struct-type-property/c',
        u'struct-type-property?', u'struct-type?', u'struct:arity-at-least',
        u'struct:arrow-contract-info', u'struct:date', u'struct:date*',
        u'struct:exn', u'struct:exn:break', u'struct:exn:break:hang-up',
        u'struct:exn:break:terminate', u'struct:exn:fail',
        u'struct:exn:fail:contract', u'struct:exn:fail:contract:arity',
        u'struct:exn:fail:contract:blame',
        u'struct:exn:fail:contract:continuation',
        u'struct:exn:fail:contract:divide-by-zero',
        u'struct:exn:fail:contract:non-fixnum-result',
        u'struct:exn:fail:contract:variable', u'struct:exn:fail:filesystem',
        u'struct:exn:fail:filesystem:errno',
        u'struct:exn:fail:filesystem:exists',
        u'struct:exn:fail:filesystem:missing-module',
        u'struct:exn:fail:filesystem:version', u'struct:exn:fail:network',
        u'struct:exn:fail:network:errno', u'struct:exn:fail:object',
        u'struct:exn:fail:out-of-memory', u'struct:exn:fail:read',
        u'struct:exn:fail:read:eof', u'struct:exn:fail:read:non-char',
        u'struct:exn:fail:syntax', u'struct:exn:fail:syntax:missing-module',
        u'struct:exn:fail:syntax:unbound', u'struct:exn:fail:unsupported',
        u'struct:exn:fail:user', u'struct:srcloc',
        u'struct:wrapped-extra-arg-arrow', u'struct?', u'sub1', u'subbytes',
        u'subclass?', u'subclass?/c', u'subprocess', u'subprocess-group-enabled',
        u'subprocess-kill', u'subprocess-pid', u'subprocess-status',
        u'subprocess-wait', u'subprocess?', u'subset?', u'substring', u'suggest/c',
        u'symbol->string', u'symbol-interned?', u'symbol-unreadable?', u'symbol<?',
        u'symbol=?', u'symbol?', u'symbols', u'sync', u'sync/enable-break',
        u'sync/timeout', u'sync/timeout/enable-break', u'syntax->datum',
        u'syntax->list', u'syntax-arm', u'syntax-column', u'syntax-debug-info',
        u'syntax-disarm', u'syntax-e', u'syntax-line',
        u'syntax-local-bind-syntaxes', u'syntax-local-certifier',
        u'syntax-local-context', u'syntax-local-expand-expression',
        u'syntax-local-get-shadower', u'syntax-local-identifier-as-binding',
        u'syntax-local-introduce', u'syntax-local-lift-context',
        u'syntax-local-lift-expression', u'syntax-local-lift-module',
        u'syntax-local-lift-module-end-declaration',
        u'syntax-local-lift-provide', u'syntax-local-lift-require',
        u'syntax-local-lift-values-expression',
        u'syntax-local-make-definition-context',
        u'syntax-local-make-delta-introducer',
        u'syntax-local-module-defined-identifiers',
        u'syntax-local-module-exports',
        u'syntax-local-module-required-identifiers', u'syntax-local-name',
        u'syntax-local-phase-level', u'syntax-local-submodules',
        u'syntax-local-transforming-module-provides?', u'syntax-local-value',
        u'syntax-local-value/immediate', u'syntax-original?', u'syntax-position',
        u'syntax-property', u'syntax-property-preserved?',
        u'syntax-property-symbol-keys', u'syntax-protect', u'syntax-rearm',
        u'syntax-recertify', u'syntax-shift-phase-level', u'syntax-source',
        u'syntax-source-module', u'syntax-span', u'syntax-taint',
        u'syntax-tainted?', u'syntax-track-origin',
        u'syntax-transforming-module-expression?',
        u'syntax-transforming-with-lifts?', u'syntax-transforming?', u'syntax/c',
        u'syntax?', u'system', u'system*', u'system*/exit-code',
        u'system-big-endian?', u'system-idle-evt', u'system-language+country',
        u'system-library-subpath', u'system-path-convention-type', u'system-type',
        u'system/exit-code', u'tail-marks-match?', u'take', u'take-common-prefix',
        u'take-right', u'takef', u'takef-right', u'tan', u'tanh',
        u'tcp-abandon-port', u'tcp-accept', u'tcp-accept-evt',
        u'tcp-accept-ready?', u'tcp-accept/enable-break', u'tcp-addresses',
        u'tcp-close', u'tcp-connect', u'tcp-connect/enable-break', u'tcp-listen',
        u'tcp-listener?', u'tcp-port?', u'tentative-pretty-print-port-cancel',
        u'tentative-pretty-print-port-transfer', u'tenth', u'terminal-port?',
        u'the-unsupplied-arg', u'third', u'thread', u'thread-cell-ref',
        u'thread-cell-set!', u'thread-cell-values?', u'thread-cell?',
        u'thread-dead-evt', u'thread-dead?', u'thread-group?', u'thread-receive',
        u'thread-receive-evt', u'thread-resume', u'thread-resume-evt',
        u'thread-rewind-receive', u'thread-running?', u'thread-send',
        u'thread-suspend', u'thread-suspend-evt', u'thread-try-receive',
        u'thread-wait', u'thread/suspend-to-kill', u'thread?', u'time-apply',
        u'touch', u'transplant-input-port', u'transplant-output-port', u'true',
        u'truncate', u'udp-addresses', u'udp-bind!', u'udp-bound?', u'udp-close',
        u'udp-connect!', u'udp-connected?', u'udp-multicast-interface',
        u'udp-multicast-join-group!', u'udp-multicast-leave-group!',
        u'udp-multicast-loopback?', u'udp-multicast-set-interface!',
        u'udp-multicast-set-loopback!', u'udp-multicast-set-ttl!',
        u'udp-multicast-ttl', u'udp-open-socket', u'udp-receive!',
        u'udp-receive!*', u'udp-receive!-evt', u'udp-receive!/enable-break',
        u'udp-receive-ready-evt', u'udp-send', u'udp-send*', u'udp-send-evt',
        u'udp-send-ready-evt', u'udp-send-to', u'udp-send-to*', u'udp-send-to-evt',
        u'udp-send-to/enable-break', u'udp-send/enable-break', u'udp?', u'unbox',
        u'uncaught-exception-handler', u'unit?', u'unspecified-dom',
        u'unsupplied-arg?', u'use-collection-link-paths',
        u'use-compiled-file-paths', u'use-user-specific-search-paths',
        u'user-execute-bit', u'user-read-bit', u'user-write-bit', u'value-blame',
        u'value-contract', u'values', u'variable-reference->empty-namespace',
        u'variable-reference->module-base-phase',
        u'variable-reference->module-declaration-inspector',
        u'variable-reference->module-path-index',
        u'variable-reference->module-source', u'variable-reference->namespace',
        u'variable-reference->phase',
        u'variable-reference->resolved-module-path',
        u'variable-reference-constant?', u'variable-reference?', u'vector',
        u'vector->immutable-vector', u'vector->list',
        u'vector->pseudo-random-generator', u'vector->pseudo-random-generator!',
        u'vector->values', u'vector-append', u'vector-argmax', u'vector-argmin',
        u'vector-copy', u'vector-copy!', u'vector-count', u'vector-drop',
        u'vector-drop-right', u'vector-fill!', u'vector-filter',
        u'vector-filter-not', u'vector-immutable', u'vector-immutable/c',
        u'vector-immutableof', u'vector-length', u'vector-map', u'vector-map!',
        u'vector-member', u'vector-memq', u'vector-memv', u'vector-ref',
        u'vector-set!', u'vector-set*!', u'vector-set-performance-stats!',
        u'vector-split-at', u'vector-split-at-right', u'vector-take',
        u'vector-take-right', u'vector/c', u'vector?', u'vectorof', u'version',
        u'void', u'void?', u'weak-box-value', u'weak-box?', u'weak-set',
        u'weak-seteq', u'weak-seteqv', u'will-execute', u'will-executor?',
        u'will-register', u'will-try-execute', u'with-input-from-bytes',
        u'with-input-from-file', u'with-input-from-string',
        u'with-output-to-bytes', u'with-output-to-file', u'with-output-to-string',
        u'would-be-future', u'wrap-evt', u'wrapped-extra-arg-arrow',
        u'wrapped-extra-arg-arrow-extra-neg-party-argument',
        u'wrapped-extra-arg-arrow-real-func', u'wrapped-extra-arg-arrow?',
        u'writable<%>', u'write', u'write-byte', u'write-bytes',
        u'write-bytes-avail', u'write-bytes-avail*', u'write-bytes-avail-evt',
        u'write-bytes-avail/enable-break', u'write-char', u'write-special',
        u'write-special-avail*', u'write-special-evt', u'write-string',
        u'write-to-file', u'writeln', u'xor', u'zero?', u'~.a', u'~.s', u'~.v', u'~a',
        u'~e', u'~r', u'~s', u'~v'
    )

    _opening_parenthesis = r'[([{]'
    _closing_parenthesis = r'[)\]}]'
    _delimiters = r'()[\]{}",\'`;\s'
    _symbol = r'(?:\|[^|]*\||\\[\w\W]|[^|\\%s]+)+' % _delimiters
    _exact_decimal_prefix = r'(?:#e)?(?:#d)?(?:#e)?'
    _exponent = r'(?:[defls][-+]?\d+)'
    _inexact_simple_no_hashes = r'(?:\d+(?:/\d+|\.\d*)?|\.\d+)'
    _inexact_simple = (r'(?:%s|(?:\d+#+(?:\.#*|/\d+#*)?|\.\d+#+|'
                       r'\d+(?:\.\d*#+|/\d+#+)))' % _inexact_simple_no_hashes)
    _inexact_normal_no_hashes = r'(?:%s%s?)' % (_inexact_simple_no_hashes,
                                                _exponent)
    _inexact_normal = r'(?:%s%s?)' % (_inexact_simple, _exponent)
    _inexact_special = r'(?:(?:inf|nan)\.[0f])'
    _inexact_real = r'(?:[-+]?%s|[-+]%s)' % (_inexact_normal,
                                             _inexact_special)
    _inexact_unsigned = r'(?:%s|%s)' % (_inexact_normal, _inexact_special)

    tokens = {
        'root': [
            (_closing_parenthesis, Error),
            (r'(?!\Z)', Text, 'unquoted-datum')
        ],
        'datum': [
            (r'(?s)#;|#![ /]([^\\\n]|\\.)*', Comment),
            (u';[^\\n\\r\x85\u2028\u2029]*', Comment.Single),
            (r'#\|', Comment.Multiline, 'block-comment'),

            # Whitespaces
            (r'(?u)\s+', Text),

            # Numbers: Keep in mind Racket reader hash prefixes, which
            # can denote the base or the type. These don't map neatly
            # onto Pygments token types; some judgment calls here.

            # #d or no prefix
            (r'(?i)%s[-+]?\d+(?=[%s])' % (_exact_decimal_prefix, _delimiters),
             Number.Integer, '#pop'),
            (r'(?i)%s[-+]?(\d+(\.\d*)?|\.\d+)([deflst][-+]?\d+)?(?=[%s])' %
             (_exact_decimal_prefix, _delimiters), Number.Float, '#pop'),
            (r'(?i)%s[-+]?(%s([-+]%s?i)?|[-+]%s?i)(?=[%s])' %
             (_exact_decimal_prefix, _inexact_normal_no_hashes,
              _inexact_normal_no_hashes, _inexact_normal_no_hashes,
              _delimiters), Number, '#pop'),

            # Inexact without explicit #i
            (r'(?i)(#d)?(%s([-+]%s?i)?|[-+]%s?i|%s@%s)(?=[%s])' %
             (_inexact_real, _inexact_unsigned, _inexact_unsigned,
              _inexact_real, _inexact_real, _delimiters), Number.Float,
             '#pop'),

            # The remaining extflonums
            (r'(?i)(([-+]?%st[-+]?\d+)|[-+](inf|nan)\.t)(?=[%s])' %
             (_inexact_simple, _delimiters), Number.Float, '#pop'),

            # #b
            (r'(?iu)(#[ei])?#b%s' % _symbol, Number.Bin, '#pop'),

            # #o
            (r'(?iu)(#[ei])?#o%s' % _symbol, Number.Oct, '#pop'),

            # #x
            (r'(?iu)(#[ei])?#x%s' % _symbol, Number.Hex, '#pop'),

            # #i is always inexact, i.e. float
            (r'(?iu)(#d)?#i%s' % _symbol, Number.Float, '#pop'),

            # Strings and characters
            (r'#?"', String.Double, ('#pop', 'string')),
            (r'#<<(.+)\n(^(?!\1$).*$\n)*^\1$', String.Heredoc, '#pop'),
            (r'#\\(u[\da-fA-F]{1,4}|U[\da-fA-F]{1,8})', String.Char, '#pop'),
            (r'(?is)#\\([0-7]{3}|[a-z]+|.)', String.Char, '#pop'),
            (r'(?s)#[pr]x#?"(\\?.)*?"', String.Regex, '#pop'),

            # Constants
            (r'#(true|false|[tTfF])', Name.Constant, '#pop'),

            # Keyword argument names (e.g. #:keyword)
            (r'(?u)#:%s' % _symbol, Keyword.Declaration, '#pop'),

            # Reader extensions
            (r'(#lang |#!)(\S+)',
             bygroups(Keyword.Namespace, Name.Namespace)),
            (r'#reader', Keyword.Namespace, 'quoted-datum'),

            # Other syntax
            (r"(?i)\.(?=[%s])|#c[is]|#['`]|#,@?" % _delimiters, Operator),
            (r"'|#[s&]|#hash(eqv?)?|#\d*(?=%s)" % _opening_parenthesis,
             Operator, ('#pop', 'quoted-datum'))
        ],
        'datum*': [
            (r'`|,@?', Operator),
            (_symbol, String.Symbol, '#pop'),
            (r'[|\\]', Error),
            default('#pop')
        ],
        'list': [
            (_closing_parenthesis, Punctuation, '#pop')
        ],
        'unquoted-datum': [
            include('datum'),
            (r'quote(?=[%s])' % _delimiters, Keyword,
             ('#pop', 'quoted-datum')),
            (r'`', Operator, ('#pop', 'quasiquoted-datum')),
            (r'quasiquote(?=[%s])' % _delimiters, Keyword,
             ('#pop', 'quasiquoted-datum')),
            (_opening_parenthesis, Punctuation, ('#pop', 'unquoted-list')),
            (words(_keywords, prefix='(?u)', suffix='(?=[%s])' % _delimiters),
             Keyword, '#pop'),
            (words(_builtins, prefix='(?u)', suffix='(?=[%s])' % _delimiters),
             Name.Builtin, '#pop'),
            (_symbol, Name, '#pop'),
            include('datum*')
        ],
        'unquoted-list': [
            include('list'),
            (r'(?!\Z)', Text, 'unquoted-datum')
        ],
        'quasiquoted-datum': [
            include('datum'),
            (r',@?', Operator, ('#pop', 'unquoted-datum')),
            (r'unquote(-splicing)?(?=[%s])' % _delimiters, Keyword,
             ('#pop', 'unquoted-datum')),
            (_opening_parenthesis, Punctuation, ('#pop', 'quasiquoted-list')),
            include('datum*')
        ],
        'quasiquoted-list': [
            include('list'),
            (r'(?!\Z)', Text, 'quasiquoted-datum')
        ],
        'quoted-datum': [
            include('datum'),
            (_opening_parenthesis, Punctuation, ('#pop', 'quoted-list')),
            include('datum*')
        ],
        'quoted-list': [
            include('list'),
            (r'(?!\Z)', Text, 'quoted-datum')
        ],
        'block-comment': [
            (r'#\|', Comment.Multiline, '#push'),
            (r'\|#', Comment.Multiline, '#pop'),
            (r'[^#|]+|.', Comment.Multiline)
        ],
        'string': [
            (r'"', String.Double, '#pop'),
            (r'(?s)\\([0-7]{1,3}|x[\da-fA-F]{1,2}|u[\da-fA-F]{1,4}|'
             r'U[\da-fA-F]{1,8}|.)', String.Escape),
            (r'[^\\"]+', String.Double)
        ]
    }


class NewLispLexer(RegexLexer):
    """
    For `newLISP. <www.newlisp.org>`_ source code (version 10.3.0).

    .. versionadded:: 1.5
    """

    name = 'NewLisp'
    aliases = ['newlisp']
    filenames = ['*.lsp', '*.nl', '*.kif']
    mimetypes = ['text/x-newlisp', 'application/x-newlisp']

    flags = re.IGNORECASE | re.MULTILINE | re.UNICODE

    # list of built-in functions for newLISP version 10.3
    builtins = (
        '^', '--', '-', ':', '!', '!=', '?', '@', '*', '/', '&', '%', '+', '++',
        '<', '<<', '<=', '=', '>', '>=', '>>', '|', '~', '$', '$0', '$1', '$10',
        '$11', '$12', '$13', '$14', '$15', '$2', '$3', '$4', '$5', '$6', '$7',
        '$8', '$9', '$args', '$idx', '$it', '$main-args', 'abort', 'abs',
        'acos', 'acosh', 'add', 'address', 'amb', 'and',  'append-file',
        'append', 'apply', 'args', 'array-list', 'array?', 'array', 'asin',
        'asinh', 'assoc', 'atan', 'atan2', 'atanh', 'atom?', 'base64-dec',
        'base64-enc', 'bayes-query', 'bayes-train', 'begin',
        'beta', 'betai', 'bind', 'binomial', 'bits', 'callback',
        'case', 'catch', 'ceil', 'change-dir', 'char', 'chop', 'Class', 'clean',
        'close', 'command-event', 'cond', 'cons', 'constant',
        'context?', 'context', 'copy-file', 'copy', 'cos', 'cosh', 'count',
        'cpymem', 'crc32', 'crit-chi2', 'crit-z', 'current-line', 'curry',
        'date-list', 'date-parse', 'date-value', 'date', 'debug', 'dec',
        'def-new', 'default', 'define-macro', 'define',
        'delete-file', 'delete-url', 'delete', 'destroy', 'det', 'device',
        'difference', 'directory?', 'directory', 'div', 'do-until', 'do-while',
        'doargs',  'dolist',  'dostring', 'dotimes',  'dotree', 'dump', 'dup',
        'empty?', 'encrypt', 'ends-with', 'env', 'erf', 'error-event',
        'eval-string', 'eval', 'exec', 'exists', 'exit', 'exp', 'expand',
        'explode', 'extend', 'factor', 'fft', 'file-info', 'file?', 'filter',
        'find-all', 'find', 'first', 'flat', 'float?', 'float', 'floor', 'flt',
        'fn', 'for-all', 'for', 'fork', 'format', 'fv', 'gammai', 'gammaln',
        'gcd', 'get-char', 'get-float', 'get-int', 'get-long', 'get-string',
        'get-url', 'global?', 'global', 'if-not', 'if', 'ifft', 'import', 'inc',
        'index', 'inf?', 'int', 'integer?', 'integer', 'intersect', 'invert',
        'irr', 'join', 'lambda-macro', 'lambda?', 'lambda', 'last-error',
        'last', 'legal?', 'length', 'let', 'letex', 'letn',
        'list?', 'list', 'load', 'local', 'log', 'lookup',
        'lower-case', 'macro?', 'main-args', 'MAIN', 'make-dir', 'map', 'mat',
        'match', 'max', 'member', 'min', 'mod', 'module', 'mul', 'multiply',
        'NaN?', 'net-accept', 'net-close', 'net-connect', 'net-error',
        'net-eval', 'net-interface', 'net-ipv', 'net-listen', 'net-local',
        'net-lookup', 'net-packet', 'net-peek', 'net-peer', 'net-ping',
        'net-receive-from', 'net-receive-udp', 'net-receive', 'net-select',
        'net-send-to', 'net-send-udp', 'net-send', 'net-service',
        'net-sessions', 'new', 'nil?', 'nil', 'normal', 'not', 'now', 'nper',
        'npv', 'nth', 'null?', 'number?', 'open', 'or', 'ostype', 'pack',
        'parse-date', 'parse', 'peek', 'pipe', 'pmt', 'pop-assoc', 'pop',
        'post-url', 'pow', 'prefix', 'pretty-print', 'primitive?', 'print',
        'println', 'prob-chi2', 'prob-z', 'process', 'prompt-event',
        'protected?', 'push', 'put-url', 'pv', 'quote?', 'quote', 'rand',
        'random', 'randomize', 'read', 'read-char', 'read-expr', 'read-file',
        'read-key', 'read-line', 'read-utf8', 'reader-event',
        'real-path', 'receive', 'ref-all', 'ref', 'regex-comp', 'regex',
        'remove-dir', 'rename-file', 'replace', 'reset', 'rest', 'reverse',
        'rotate', 'round', 'save', 'search', 'seed', 'seek', 'select', 'self',
        'semaphore', 'send', 'sequence', 'series', 'set-locale', 'set-ref-all',
        'set-ref', 'set', 'setf',  'setq', 'sgn', 'share', 'signal', 'silent',
        'sin', 'sinh', 'sleep', 'slice', 'sort', 'source', 'spawn', 'sqrt',
        'starts-with', 'string?', 'string', 'sub', 'swap', 'sym', 'symbol?',
        'symbols', 'sync', 'sys-error', 'sys-info', 'tan', 'tanh', 'term',
        'throw-error', 'throw', 'time-of-day', 'time', 'timer', 'title-case',
        'trace-highlight', 'trace', 'transpose', 'Tree', 'trim', 'true?',
        'true', 'unicode', 'unify', 'unique', 'unless', 'unpack', 'until',
        'upper-case', 'utf8', 'utf8len', 'uuid', 'wait-pid', 'when', 'while',
        'write', 'write-char', 'write-file', 'write-line',
        'xfer-event', 'xml-error', 'xml-parse', 'xml-type-tags', 'zero?',
    )

    # valid names
    valid_name = r'([\w!$%&*+.,/<=>?@^~|-])+|(\[.*?\])+'

    tokens = {
        'root': [
            # shebang
            (r'#!(.*?)$', Comment.Preproc),
            # comments starting with semicolon
            (r';.*$', Comment.Single),
            # comments starting with #
            (r'#.*$', Comment.Single),

            # whitespace
            (r'\s+', Text),

            # strings, symbols and characters
            (r'"(\\\\|\\"|[^"])*"', String),

            # braces
            (r'\{', String, "bracestring"),

            # [text] ... [/text] delimited strings
            (r'\[text\]*', String, "tagstring"),

            # 'special' operators...
            (r"('|:)", Operator),

            # highlight the builtins
            (words(builtins, suffix=r'\b'),
             Keyword),

            # the remaining functions
            (r'(?<=\()' + valid_name, Name.Variable),

            # the remaining variables
            (valid_name, String.Symbol),

            # parentheses
            (r'(\(|\))', Punctuation),
        ],

        # braced strings...
        'bracestring': [
            (r'\{', String, "#push"),
            (r'\}', String, "#pop"),
            ('[^{}]+', String),
        ],

        # tagged [text]...[/text] delimited strings...
        'tagstring': [
            (r'(?s)(.*?)(\[/text\])', String, '#pop'),
        ],
    }


class EmacsLispLexer(RegexLexer):
    """
    An ELisp lexer, parsing a stream and outputting the tokens
    needed to highlight elisp code.

    .. versionadded:: 2.1
    """
    name = 'EmacsLisp'
    aliases = ['emacs', 'elisp', 'emacs-lisp']
    filenames = ['*.el']
    mimetypes = ['text/x-elisp', 'application/x-elisp']

    flags = re.MULTILINE

    # couple of useful regexes

    # characters that are not macro-characters and can be used to begin a symbol
    nonmacro = r'\\.|[\w!$%&*+-/<=>?@^{}~|]'
    constituent = nonmacro + '|[#.:]'
    terminated = r'(?=[ "()\]\'\n,;`])'  # whitespace or terminating macro characters

    # symbol token, reverse-engineered from hyperspec
    # Take a deep breath...
    symbol = r'((?:%s)(?:%s)*)' % (nonmacro, constituent)

    macros = set((
        'atomic-change-group', 'case', 'block', 'cl-block', 'cl-callf', 'cl-callf2',
        'cl-case', 'cl-decf', 'cl-declaim', 'cl-declare',
        'cl-define-compiler-macro', 'cl-defmacro', 'cl-defstruct',
        'cl-defsubst', 'cl-deftype', 'cl-defun', 'cl-destructuring-bind',
        'cl-do', 'cl-do*', 'cl-do-all-symbols', 'cl-do-symbols', 'cl-dolist',
        'cl-dotimes', 'cl-ecase', 'cl-etypecase', 'eval-when', 'cl-eval-when', 'cl-flet',
        'cl-flet*', 'cl-function', 'cl-incf', 'cl-labels', 'cl-letf',
        'cl-letf*', 'cl-load-time-value', 'cl-locally', 'cl-loop',
        'cl-macrolet', 'cl-multiple-value-bind', 'cl-multiple-value-setq',
        'cl-progv', 'cl-psetf', 'cl-psetq', 'cl-pushnew', 'cl-remf',
        'cl-return', 'cl-return-from', 'cl-rotatef', 'cl-shiftf',
        'cl-symbol-macrolet', 'cl-tagbody', 'cl-the', 'cl-typecase',
        'combine-after-change-calls', 'condition-case-unless-debug', 'decf',
        'declaim', 'declare', 'declare-function', 'def-edebug-spec',
        'defadvice', 'defclass', 'defcustom', 'defface', 'defgeneric',
        'defgroup', 'define-advice', 'define-alternatives',
        'define-compiler-macro', 'define-derived-mode', 'define-generic-mode',
        'define-global-minor-mode', 'define-globalized-minor-mode',
        'define-minor-mode', 'define-modify-macro',
        'define-obsolete-face-alias', 'define-obsolete-function-alias',
        'define-obsolete-variable-alias', 'define-setf-expander',
        'define-skeleton', 'defmacro', 'defmethod', 'defsetf', 'defstruct',
        'defsubst', 'deftheme', 'deftype', 'defun', 'defvar-local',
        'delay-mode-hooks', 'destructuring-bind', 'do', 'do*',
        'do-all-symbols', 'do-symbols', 'dolist', 'dont-compile', 'dotimes',
        'dotimes-with-progress-reporter', 'ecase', 'ert-deftest', 'etypecase',
        'eval-and-compile', 'eval-when-compile', 'flet', 'ignore-errors',
        'incf', 'labels', 'lambda', 'letrec', 'lexical-let', 'lexical-let*',
        'loop', 'multiple-value-bind', 'multiple-value-setq', 'noreturn',
        'oref', 'oref-default', 'oset', 'oset-default', 'pcase',
        'pcase-defmacro', 'pcase-dolist', 'pcase-exhaustive', 'pcase-let',
        'pcase-let*', 'pop', 'psetf', 'psetq', 'push', 'pushnew', 'remf',
        'return', 'rotatef', 'rx', 'save-match-data', 'save-selected-window',
        'save-window-excursion', 'setf', 'setq-local', 'shiftf',
        'track-mouse', 'typecase', 'unless', 'use-package', 'when',
        'while-no-input', 'with-case-table', 'with-category-table',
        'with-coding-priority', 'with-current-buffer', 'with-demoted-errors',
        'with-eval-after-load', 'with-file-modes', 'with-local-quit',
        'with-output-to-string', 'with-output-to-temp-buffer',
        'with-parsed-tramp-file-name', 'with-selected-frame',
        'with-selected-window', 'with-silent-modifications', 'with-slots',
        'with-syntax-table', 'with-temp-buffer', 'with-temp-file',
        'with-temp-message', 'with-timeout', 'with-tramp-connection-property',
        'with-tramp-file-property', 'with-tramp-progress-reporter',
        'with-wrapper-hook', 'load-time-value', 'locally', 'macrolet', 'progv',
        'return-from',
    ))

    special_forms = set((
        'and', 'catch', 'cond', 'condition-case', 'defconst', 'defvar',
        'function', 'if', 'interactive', 'let', 'let*', 'or', 'prog1',
        'prog2', 'progn', 'quote', 'save-current-buffer', 'save-excursion',
        'save-restriction', 'setq', 'setq-default', 'subr-arity',
        'unwind-protect', 'while',
    ))

    builtin_function = set((
        '%', '*', '+', '-', '/', '/=', '1+', '1-', '<', '<=', '=', '>', '>=',
        'Snarf-documentation', 'abort-recursive-edit', 'abs',
        'accept-process-output', 'access-file', 'accessible-keymaps', 'acos',
        'active-minibuffer-window', 'add-face-text-property',
        'add-name-to-file', 'add-text-properties', 'all-completions',
        'append', 'apply', 'apropos-internal', 'aref', 'arrayp', 'aset',
        'ash', 'asin', 'assoc', 'assoc-string', 'assq', 'atan', 'atom',
        'autoload', 'autoload-do-load', 'backtrace', 'backtrace--locals',
        'backtrace-debug', 'backtrace-eval', 'backtrace-frame',
        'backward-char', 'backward-prefix-chars', 'barf-if-buffer-read-only',
        'base64-decode-region', 'base64-decode-string',
        'base64-encode-region', 'base64-encode-string', 'beginning-of-line',
        'bidi-find-overridden-directionality', 'bidi-resolved-levels',
        'bitmap-spec-p', 'bobp', 'bolp', 'bool-vector',
        'bool-vector-count-consecutive', 'bool-vector-count-population',
        'bool-vector-exclusive-or', 'bool-vector-intersection',
        'bool-vector-not', 'bool-vector-p', 'bool-vector-set-difference',
        'bool-vector-subsetp', 'bool-vector-union', 'boundp',
        'buffer-base-buffer', 'buffer-chars-modified-tick',
        'buffer-enable-undo', 'buffer-file-name', 'buffer-has-markers-at',
        'buffer-list', 'buffer-live-p', 'buffer-local-value',
        'buffer-local-variables', 'buffer-modified-p', 'buffer-modified-tick',
        'buffer-name', 'buffer-size', 'buffer-string', 'buffer-substring',
        'buffer-substring-no-properties', 'buffer-swap-text', 'bufferp',
        'bury-buffer-internal', 'byte-code', 'byte-code-function-p',
        'byte-to-position', 'byte-to-string', 'byteorder',
        'call-interactively', 'call-last-kbd-macro', 'call-process',
        'call-process-region', 'cancel-kbd-macro-events', 'capitalize',
        'capitalize-region', 'capitalize-word', 'car', 'car-less-than-car',
        'car-safe', 'case-table-p', 'category-docstring',
        'category-set-mnemonics', 'category-table', 'category-table-p',
        'ccl-execute', 'ccl-execute-on-string', 'ccl-program-p', 'cdr',
        'cdr-safe', 'ceiling', 'char-after', 'char-before',
        'char-category-set', 'char-charset', 'char-equal', 'char-or-string-p',
        'char-resolve-modifiers', 'char-syntax', 'char-table-extra-slot',
        'char-table-p', 'char-table-parent', 'char-table-range',
        'char-table-subtype', 'char-to-string', 'char-width', 'characterp',
        'charset-after', 'charset-id-internal', 'charset-plist',
        'charset-priority-list', 'charsetp', 'check-coding-system',
        'check-coding-systems-region', 'clear-buffer-auto-save-failure',
        'clear-charset-maps', 'clear-face-cache', 'clear-font-cache',
        'clear-image-cache', 'clear-string', 'clear-this-command-keys',
        'close-font', 'clrhash', 'coding-system-aliases',
        'coding-system-base', 'coding-system-eol-type', 'coding-system-p',
        'coding-system-plist', 'coding-system-priority-list',
        'coding-system-put', 'color-distance', 'color-gray-p',
        'color-supported-p', 'combine-after-change-execute',
        'command-error-default-function', 'command-remapping', 'commandp',
        'compare-buffer-substrings', 'compare-strings',
        'compare-window-configurations', 'completing-read',
        'compose-region-internal', 'compose-string-internal',
        'composition-get-gstring', 'compute-motion', 'concat', 'cons',
        'consp', 'constrain-to-field', 'continue-process',
        'controlling-tty-p', 'coordinates-in-window-p', 'copy-alist',
        'copy-category-table', 'copy-file', 'copy-hash-table', 'copy-keymap',
        'copy-marker', 'copy-sequence', 'copy-syntax-table', 'copysign',
        'cos', 'current-active-maps', 'current-bidi-paragraph-direction',
        'current-buffer', 'current-case-table', 'current-column',
        'current-global-map', 'current-idle-time', 'current-indentation',
        'current-input-mode', 'current-local-map', 'current-message',
        'current-minor-mode-maps', 'current-time', 'current-time-string',
        'current-time-zone', 'current-window-configuration',
        'cygwin-convert-file-name-from-windows',
        'cygwin-convert-file-name-to-windows', 'daemon-initialized',
        'daemonp', 'dbus--init-bus', 'dbus-get-unique-name',
        'dbus-message-internal', 'debug-timer-check', 'declare-equiv-charset',
        'decode-big5-char', 'decode-char', 'decode-coding-region',
        'decode-coding-string', 'decode-sjis-char', 'decode-time',
        'default-boundp', 'default-file-modes', 'default-printer-name',
        'default-toplevel-value', 'default-value', 'define-category',
        'define-charset-alias', 'define-charset-internal',
        'define-coding-system-alias', 'define-coding-system-internal',
        'define-fringe-bitmap', 'define-hash-table-test', 'define-key',
        'define-prefix-command', 'delete',
        'delete-all-overlays', 'delete-and-extract-region', 'delete-char',
        'delete-directory-internal', 'delete-field', 'delete-file',
        'delete-frame', 'delete-other-windows-internal', 'delete-overlay',
        'delete-process', 'delete-region', 'delete-terminal',
        'delete-window-internal', 'delq', 'describe-buffer-bindings',
        'describe-vector', 'destroy-fringe-bitmap', 'detect-coding-region',
        'detect-coding-string', 'ding', 'directory-file-name',
        'directory-files', 'directory-files-and-attributes', 'discard-input',
        'display-supports-face-attributes-p', 'do-auto-save', 'documentation',
        'documentation-property', 'downcase', 'downcase-region',
        'downcase-word', 'draw-string', 'dump-colors', 'dump-emacs',
        'dump-face', 'dump-frame-glyph-matrix', 'dump-glyph-matrix',
        'dump-glyph-row', 'dump-redisplay-history', 'dump-tool-bar-row',
        'elt', 'emacs-pid', 'encode-big5-char', 'encode-char',
        'encode-coding-region', 'encode-coding-string', 'encode-sjis-char',
        'encode-time', 'end-kbd-macro', 'end-of-line', 'eobp', 'eolp', 'eq',
        'eql', 'equal', 'equal-including-properties', 'erase-buffer',
        'error-message-string', 'eval', 'eval-buffer', 'eval-region',
        'event-convert-list', 'execute-kbd-macro', 'exit-recursive-edit',
        'exp', 'expand-file-name', 'expt', 'external-debugging-output',
        'face-attribute-relative-p', 'face-attributes-as-vector', 'face-font',
        'fboundp', 'fceiling', 'fetch-bytecode', 'ffloor',
        'field-beginning', 'field-end', 'field-string',
        'field-string-no-properties', 'file-accessible-directory-p',
        'file-acl', 'file-attributes', 'file-attributes-lessp',
        'file-directory-p', 'file-executable-p', 'file-exists-p',
        'file-locked-p', 'file-modes', 'file-name-absolute-p',
        'file-name-all-completions', 'file-name-as-directory',
        'file-name-completion', 'file-name-directory',
        'file-name-nondirectory', 'file-newer-than-file-p', 'file-readable-p',
        'file-regular-p', 'file-selinux-context', 'file-symlink-p',
        'file-system-info', 'file-system-info', 'file-writable-p',
        'fillarray', 'find-charset-region', 'find-charset-string',
        'find-coding-systems-region-internal', 'find-composition-internal',
        'find-file-name-handler', 'find-font', 'find-operation-coding-system',
        'float', 'float-time', 'floatp', 'floor', 'fmakunbound',
        'following-char', 'font-at', 'font-drive-otf', 'font-face-attributes',
        'font-family-list', 'font-get', 'font-get-glyphs',
        'font-get-system-font', 'font-get-system-normal-font', 'font-info',
        'font-match-p', 'font-otf-alternates', 'font-put',
        'font-shape-gstring', 'font-spec', 'font-variation-glyphs',
        'font-xlfd-name', 'fontp', 'fontset-font', 'fontset-info',
        'fontset-list', 'fontset-list-all', 'force-mode-line-update',
        'force-window-update', 'format', 'format-mode-line',
        'format-network-address', 'format-time-string', 'forward-char',
        'forward-comment', 'forward-line', 'forward-word',
        'frame-border-width', 'frame-bottom-divider-width',
        'frame-can-run-window-configuration-change-hook', 'frame-char-height',
        'frame-char-width', 'frame-face-alist', 'frame-first-window',
        'frame-focus', 'frame-font-cache', 'frame-fringe-width', 'frame-list',
        'frame-live-p', 'frame-or-buffer-changed-p', 'frame-parameter',
        'frame-parameters', 'frame-pixel-height', 'frame-pixel-width',
        'frame-pointer-visible-p', 'frame-right-divider-width',
        'frame-root-window', 'frame-scroll-bar-height',
        'frame-scroll-bar-width', 'frame-selected-window', 'frame-terminal',
        'frame-text-cols', 'frame-text-height', 'frame-text-lines',
        'frame-text-width', 'frame-total-cols', 'frame-total-lines',
        'frame-visible-p', 'framep', 'frexp', 'fringe-bitmaps-at-pos',
        'fround', 'fset', 'ftruncate', 'funcall', 'funcall-interactively',
        'function-equal', 'functionp', 'gap-position', 'gap-size',
        'garbage-collect', 'gc-status', 'generate-new-buffer-name', 'get',
        'get-buffer', 'get-buffer-create', 'get-buffer-process',
        'get-buffer-window', 'get-byte', 'get-char-property',
        'get-char-property-and-overlay', 'get-file-buffer', 'get-file-char',
        'get-internal-run-time', 'get-load-suffixes', 'get-pos-property',
        'get-process', 'get-screen-color', 'get-text-property',
        'get-unicode-property-internal', 'get-unused-category',
        'get-unused-iso-final-char', 'getenv-internal', 'gethash',
        'gfile-add-watch', 'gfile-rm-watch', 'global-key-binding',
        'gnutls-available-p', 'gnutls-boot', 'gnutls-bye', 'gnutls-deinit',
        'gnutls-error-fatalp', 'gnutls-error-string', 'gnutls-errorp',
        'gnutls-get-initstage', 'gnutls-peer-status',
        'gnutls-peer-status-warning-describe', 'goto-char', 'gpm-mouse-start',
        'gpm-mouse-stop', 'group-gid', 'group-real-gid',
        'handle-save-session', 'handle-switch-frame', 'hash-table-count',
        'hash-table-p', 'hash-table-rehash-size',
        'hash-table-rehash-threshold', 'hash-table-size', 'hash-table-test',
        'hash-table-weakness', 'iconify-frame', 'identity', 'image-flush',
        'image-mask-p', 'image-metadata', 'image-size', 'imagemagick-types',
        'imagep', 'indent-to', 'indirect-function', 'indirect-variable',
        'init-image-library', 'inotify-add-watch', 'inotify-rm-watch',
        'input-pending-p', 'insert', 'insert-and-inherit',
        'insert-before-markers', 'insert-before-markers-and-inherit',
        'insert-buffer-substring', 'insert-byte', 'insert-char',
        'insert-file-contents', 'insert-startup-screen', 'int86',
        'integer-or-marker-p', 'integerp', 'interactive-form', 'intern',
        'intern-soft', 'internal--track-mouse', 'internal-char-font',
        'internal-complete-buffer', 'internal-copy-lisp-face',
        'internal-default-process-filter',
        'internal-default-process-sentinel', 'internal-describe-syntax-value',
        'internal-event-symbol-parse-modifiers',
        'internal-face-x-get-resource', 'internal-get-lisp-face-attribute',
        'internal-lisp-face-attribute-values', 'internal-lisp-face-empty-p',
        'internal-lisp-face-equal-p', 'internal-lisp-face-p',
        'internal-make-lisp-face', 'internal-make-var-non-special',
        'internal-merge-in-global-face',
        'internal-set-alternative-font-family-alist',
        'internal-set-alternative-font-registry-alist',
        'internal-set-font-selection-order',
        'internal-set-lisp-face-attribute',
        'internal-set-lisp-face-attribute-from-resource',
        'internal-show-cursor', 'internal-show-cursor-p', 'interrupt-process',
        'invisible-p', 'invocation-directory', 'invocation-name', 'isnan',
        'iso-charset', 'key-binding', 'key-description',
        'keyboard-coding-system', 'keymap-parent', 'keymap-prompt', 'keymapp',
        'keywordp', 'kill-all-local-variables', 'kill-buffer', 'kill-emacs',
        'kill-local-variable', 'kill-process', 'last-nonminibuffer-frame',
        'lax-plist-get', 'lax-plist-put', 'ldexp', 'length',
        'libxml-parse-html-region', 'libxml-parse-xml-region',
        'line-beginning-position', 'line-end-position', 'line-pixel-height',
        'list', 'list-fonts', 'list-system-processes', 'listp', 'load',
        'load-average', 'local-key-binding', 'local-variable-if-set-p',
        'local-variable-p', 'locale-info', 'locate-file-internal',
        'lock-buffer', 'log', 'logand', 'logb', 'logior', 'lognot', 'logxor',
        'looking-at', 'lookup-image', 'lookup-image-map', 'lookup-key',
        'lower-frame', 'lsh', 'macroexpand', 'make-bool-vector',
        'make-byte-code', 'make-category-set', 'make-category-table',
        'make-char', 'make-char-table', 'make-directory-internal',
        'make-frame-invisible', 'make-frame-visible', 'make-hash-table',
        'make-indirect-buffer', 'make-keymap', 'make-list',
        'make-local-variable', 'make-marker', 'make-network-process',
        'make-overlay', 'make-serial-process', 'make-sparse-keymap',
        'make-string', 'make-symbol', 'make-symbolic-link', 'make-temp-name',
        'make-terminal-frame', 'make-variable-buffer-local',
        'make-variable-frame-local', 'make-vector', 'makunbound',
        'map-char-table', 'map-charset-chars', 'map-keymap',
        'map-keymap-internal', 'mapatoms', 'mapc', 'mapcar', 'mapconcat',
        'maphash', 'mark-marker', 'marker-buffer', 'marker-insertion-type',
        'marker-position', 'markerp', 'match-beginning', 'match-data',
        'match-end', 'matching-paren', 'max', 'max-char', 'md5', 'member',
        'memory-info', 'memory-limit', 'memory-use-counts', 'memq', 'memql',
        'menu-bar-menu-at-x-y', 'menu-or-popup-active-p',
        'menu-or-popup-active-p', 'merge-face-attribute', 'message',
        'message-box', 'message-or-box', 'min',
        'minibuffer-completion-contents', 'minibuffer-contents',
        'minibuffer-contents-no-properties', 'minibuffer-depth',
        'minibuffer-prompt', 'minibuffer-prompt-end',
        'minibuffer-selected-window', 'minibuffer-window', 'minibufferp',
        'minor-mode-key-binding', 'mod', 'modify-category-entry',
        'modify-frame-parameters', 'modify-syntax-entry',
        'mouse-pixel-position', 'mouse-position', 'move-overlay',
        'move-point-visually', 'move-to-column', 'move-to-window-line',
        'msdos-downcase-filename', 'msdos-long-file-names', 'msdos-memget',
        'msdos-memput', 'msdos-mouse-disable', 'msdos-mouse-enable',
        'msdos-mouse-init', 'msdos-mouse-p', 'msdos-remember-default-colors',
        'msdos-set-keyboard', 'msdos-set-mouse-buttons',
        'multibyte-char-to-unibyte', 'multibyte-string-p', 'narrow-to-region',
        'natnump', 'nconc', 'network-interface-info',
        'network-interface-list', 'new-fontset', 'newline-cache-check',
        'next-char-property-change', 'next-frame', 'next-overlay-change',
        'next-property-change', 'next-read-file-uses-dialog-p',
        'next-single-char-property-change', 'next-single-property-change',
        'next-window', 'nlistp', 'nreverse', 'nth', 'nthcdr', 'null',
        'number-or-marker-p', 'number-to-string', 'numberp',
        'open-dribble-file', 'open-font', 'open-termscript',
        'optimize-char-table', 'other-buffer', 'other-window-for-scrolling',
        'overlay-buffer', 'overlay-end', 'overlay-get', 'overlay-lists',
        'overlay-properties', 'overlay-put', 'overlay-recenter',
        'overlay-start', 'overlayp', 'overlays-at', 'overlays-in',
        'parse-partial-sexp', 'play-sound-internal', 'plist-get',
        'plist-member', 'plist-put', 'point', 'point-marker', 'point-max',
        'point-max-marker', 'point-min', 'point-min-marker',
        'pos-visible-in-window-p', 'position-bytes', 'posix-looking-at',
        'posix-search-backward', 'posix-search-forward', 'posix-string-match',
        'posn-at-point', 'posn-at-x-y', 'preceding-char',
        'prefix-numeric-value', 'previous-char-property-change',
        'previous-frame', 'previous-overlay-change',
        'previous-property-change', 'previous-single-char-property-change',
        'previous-single-property-change', 'previous-window', 'prin1',
        'prin1-to-string', 'princ', 'print', 'process-attributes',
        'process-buffer', 'process-coding-system', 'process-command',
        'process-connection', 'process-contact', 'process-datagram-address',
        'process-exit-status', 'process-filter', 'process-filter-multibyte-p',
        'process-id', 'process-inherit-coding-system-flag', 'process-list',
        'process-mark', 'process-name', 'process-plist',
        'process-query-on-exit-flag', 'process-running-child-p',
        'process-send-eof', 'process-send-region', 'process-send-string',
        'process-sentinel', 'process-status', 'process-tty-name',
        'process-type', 'processp', 'profiler-cpu-log',
        'profiler-cpu-running-p', 'profiler-cpu-start', 'profiler-cpu-stop',
        'profiler-memory-log', 'profiler-memory-running-p',
        'profiler-memory-start', 'profiler-memory-stop', 'propertize',
        'purecopy', 'put', 'put-text-property',
        'put-unicode-property-internal', 'puthash', 'query-font',
        'query-fontset', 'quit-process', 'raise-frame', 'random', 'rassoc',
        'rassq', 're-search-backward', 're-search-forward', 'read',
        'read-buffer', 'read-char', 'read-char-exclusive',
        'read-coding-system', 'read-command', 'read-event',
        'read-from-minibuffer', 'read-from-string', 'read-function',
        'read-key-sequence', 'read-key-sequence-vector',
        'read-no-blanks-input', 'read-non-nil-coding-system', 'read-string',
        'read-variable', 'recent-auto-save-p', 'recent-doskeys',
        'recent-keys', 'recenter', 'recursion-depth', 'recursive-edit',
        'redirect-debugging-output', 'redirect-frame-focus', 'redisplay',
        'redraw-display', 'redraw-frame', 'regexp-quote', 'region-beginning',
        'region-end', 'register-ccl-program', 'register-code-conversion-map',
        'remhash', 'remove-list-of-text-properties', 'remove-text-properties',
        'rename-buffer', 'rename-file', 'replace-match',
        'reset-this-command-lengths', 'resize-mini-window-internal',
        'restore-buffer-modified-p', 'resume-tty', 'reverse', 'round',
        'run-hook-with-args', 'run-hook-with-args-until-failure',
        'run-hook-with-args-until-success', 'run-hook-wrapped', 'run-hooks',
        'run-window-configuration-change-hook', 'run-window-scroll-functions',
        'safe-length', 'scan-lists', 'scan-sexps', 'scroll-down',
        'scroll-left', 'scroll-other-window', 'scroll-right', 'scroll-up',
        'search-backward', 'search-forward', 'secure-hash', 'select-frame',
        'select-window', 'selected-frame', 'selected-window',
        'self-insert-command', 'send-string-to-terminal', 'sequencep',
        'serial-process-configure', 'set', 'set-buffer',
        'set-buffer-auto-saved', 'set-buffer-major-mode',
        'set-buffer-modified-p', 'set-buffer-multibyte', 'set-case-table',
        'set-category-table', 'set-char-table-extra-slot',
        'set-char-table-parent', 'set-char-table-range', 'set-charset-plist',
        'set-charset-priority', 'set-coding-system-priority',
        'set-cursor-size', 'set-default', 'set-default-file-modes',
        'set-default-toplevel-value', 'set-file-acl', 'set-file-modes',
        'set-file-selinux-context', 'set-file-times', 'set-fontset-font',
        'set-frame-height', 'set-frame-position', 'set-frame-selected-window',
        'set-frame-size', 'set-frame-width', 'set-fringe-bitmap-face',
        'set-input-interrupt-mode', 'set-input-meta-mode', 'set-input-mode',
        'set-keyboard-coding-system-internal', 'set-keymap-parent',
        'set-marker', 'set-marker-insertion-type', 'set-match-data',
        'set-message-beep', 'set-minibuffer-window',
        'set-mouse-pixel-position', 'set-mouse-position',
        'set-network-process-option', 'set-output-flow-control',
        'set-process-buffer', 'set-process-coding-system',
        'set-process-datagram-address', 'set-process-filter',
        'set-process-filter-multibyte',
        'set-process-inherit-coding-system-flag', 'set-process-plist',
        'set-process-query-on-exit-flag', 'set-process-sentinel',
        'set-process-window-size', 'set-quit-char',
        'set-safe-terminal-coding-system-internal', 'set-screen-color',
        'set-standard-case-table', 'set-syntax-table',
        'set-terminal-coding-system-internal', 'set-terminal-local-value',
        'set-terminal-parameter', 'set-text-properties', 'set-time-zone-rule',
        'set-visited-file-modtime', 'set-window-buffer',
        'set-window-combination-limit', 'set-window-configuration',
        'set-window-dedicated-p', 'set-window-display-table',
        'set-window-fringes', 'set-window-hscroll', 'set-window-margins',
        'set-window-new-normal', 'set-window-new-pixel',
        'set-window-new-total', 'set-window-next-buffers',
        'set-window-parameter', 'set-window-point', 'set-window-prev-buffers',
        'set-window-redisplay-end-trigger', 'set-window-scroll-bars',
        'set-window-start', 'set-window-vscroll', 'setcar', 'setcdr',
        'setplist', 'show-face-resources', 'signal', 'signal-process', 'sin',
        'single-key-description', 'skip-chars-backward', 'skip-chars-forward',
        'skip-syntax-backward', 'skip-syntax-forward', 'sleep-for', 'sort',
        'sort-charsets', 'special-variable-p', 'split-char',
        'split-window-internal', 'sqrt', 'standard-case-table',
        'standard-category-table', 'standard-syntax-table', 'start-kbd-macro',
        'start-process', 'stop-process', 'store-kbd-macro-event', 'string',
        'string-as-multibyte', 'string-as-unibyte', 'string-bytes',
        'string-collate-equalp', 'string-collate-lessp', 'string-equal',
        'string-lessp', 'string-make-multibyte', 'string-make-unibyte',
        'string-match', 'string-to-char', 'string-to-multibyte',
        'string-to-number', 'string-to-syntax', 'string-to-unibyte',
        'string-width', 'stringp', 'subr-name', 'subrp',
        'subst-char-in-region', 'substitute-command-keys',
        'substitute-in-file-name', 'substring', 'substring-no-properties',
        'suspend-emacs', 'suspend-tty', 'suspicious-object', 'sxhash',
        'symbol-function', 'symbol-name', 'symbol-plist', 'symbol-value',
        'symbolp', 'syntax-table', 'syntax-table-p', 'system-groups',
        'system-move-file-to-trash', 'system-name', 'system-users', 'tan',
        'terminal-coding-system', 'terminal-list', 'terminal-live-p',
        'terminal-local-value', 'terminal-name', 'terminal-parameter',
        'terminal-parameters', 'terpri', 'test-completion',
        'text-char-description', 'text-properties-at', 'text-property-any',
        'text-property-not-all', 'this-command-keys',
        'this-command-keys-vector', 'this-single-command-keys',
        'this-single-command-raw-keys', 'time-add', 'time-less-p',
        'time-subtract', 'tool-bar-get-system-style', 'tool-bar-height',
        'tool-bar-pixel-width', 'top-level', 'trace-redisplay',
        'trace-to-stderr', 'translate-region-internal', 'transpose-regions',
        'truncate', 'try-completion', 'tty-display-color-cells',
        'tty-display-color-p', 'tty-no-underline',
        'tty-suppress-bold-inverse-default-colors', 'tty-top-frame',
        'tty-type', 'type-of', 'undo-boundary', 'unencodable-char-position',
        'unhandled-file-name-directory', 'unibyte-char-to-multibyte',
        'unibyte-string', 'unicode-property-table-internal', 'unify-charset',
        'unintern', 'unix-sync', 'unlock-buffer', 'upcase', 'upcase-initials',
        'upcase-initials-region', 'upcase-region', 'upcase-word',
        'use-global-map', 'use-local-map', 'user-full-name',
        'user-login-name', 'user-real-login-name', 'user-real-uid',
        'user-uid', 'variable-binding-locus', 'vconcat', 'vector',
        'vector-or-char-table-p', 'vectorp', 'verify-visited-file-modtime',
        'vertical-motion', 'visible-frame-list', 'visited-file-modtime',
        'w16-get-clipboard-data', 'w16-selection-exists-p',
        'w16-set-clipboard-data', 'w32-battery-status',
        'w32-default-color-map', 'w32-define-rgb-color',
        'w32-display-monitor-attributes-list', 'w32-frame-menu-bar-size',
        'w32-frame-rect', 'w32-get-clipboard-data',
        'w32-get-codepage-charset', 'w32-get-console-codepage',
        'w32-get-console-output-codepage', 'w32-get-current-locale-id',
        'w32-get-default-locale-id', 'w32-get-keyboard-layout',
        'w32-get-locale-info', 'w32-get-valid-codepages',
        'w32-get-valid-keyboard-layouts', 'w32-get-valid-locale-ids',
        'w32-has-winsock', 'w32-long-file-name', 'w32-reconstruct-hot-key',
        'w32-register-hot-key', 'w32-registered-hot-keys',
        'w32-selection-exists-p', 'w32-send-sys-command',
        'w32-set-clipboard-data', 'w32-set-console-codepage',
        'w32-set-console-output-codepage', 'w32-set-current-locale',
        'w32-set-keyboard-layout', 'w32-set-process-priority',
        'w32-shell-execute', 'w32-short-file-name', 'w32-toggle-lock-key',
        'w32-unload-winsock', 'w32-unregister-hot-key', 'w32-window-exists-p',
        'w32notify-add-watch', 'w32notify-rm-watch',
        'waiting-for-user-input-p', 'where-is-internal', 'widen',
        'widget-apply', 'widget-get', 'widget-put',
        'window-absolute-pixel-edges', 'window-at', 'window-body-height',
        'window-body-width', 'window-bottom-divider-width', 'window-buffer',
        'window-combination-limit', 'window-configuration-frame',
        'window-configuration-p', 'window-dedicated-p',
        'window-display-table', 'window-edges', 'window-end', 'window-frame',
        'window-fringes', 'window-header-line-height', 'window-hscroll',
        'window-inside-absolute-pixel-edges', 'window-inside-edges',
        'window-inside-pixel-edges', 'window-left-child',
        'window-left-column', 'window-line-height', 'window-list',
        'window-list-1', 'window-live-p', 'window-margins',
        'window-minibuffer-p', 'window-mode-line-height', 'window-new-normal',
        'window-new-pixel', 'window-new-total', 'window-next-buffers',
        'window-next-sibling', 'window-normal-size', 'window-old-point',
        'window-parameter', 'window-parameters', 'window-parent',
        'window-pixel-edges', 'window-pixel-height', 'window-pixel-left',
        'window-pixel-top', 'window-pixel-width', 'window-point',
        'window-prev-buffers', 'window-prev-sibling',
        'window-redisplay-end-trigger', 'window-resize-apply',
        'window-resize-apply-total', 'window-right-divider-width',
        'window-scroll-bar-height', 'window-scroll-bar-width',
        'window-scroll-bars', 'window-start', 'window-system',
        'window-text-height', 'window-text-pixel-size', 'window-text-width',
        'window-top-child', 'window-top-line', 'window-total-height',
        'window-total-width', 'window-use-time', 'window-valid-p',
        'window-vscroll', 'windowp', 'write-char', 'write-region',
        'x-backspace-delete-keys-p', 'x-change-window-property',
        'x-change-window-property', 'x-close-connection',
        'x-close-connection', 'x-create-frame', 'x-create-frame',
        'x-delete-window-property', 'x-delete-window-property',
        'x-disown-selection-internal', 'x-display-backing-store',
        'x-display-backing-store', 'x-display-color-cells',
        'x-display-color-cells', 'x-display-grayscale-p',
        'x-display-grayscale-p', 'x-display-list', 'x-display-list',
        'x-display-mm-height', 'x-display-mm-height', 'x-display-mm-width',
        'x-display-mm-width', 'x-display-monitor-attributes-list',
        'x-display-pixel-height', 'x-display-pixel-height',
        'x-display-pixel-width', 'x-display-pixel-width', 'x-display-planes',
        'x-display-planes', 'x-display-save-under', 'x-display-save-under',
        'x-display-screens', 'x-display-screens', 'x-display-visual-class',
        'x-display-visual-class', 'x-family-fonts', 'x-file-dialog',
        'x-file-dialog', 'x-file-dialog', 'x-focus-frame', 'x-frame-geometry',
        'x-frame-geometry', 'x-get-atom-name', 'x-get-resource',
        'x-get-selection-internal', 'x-hide-tip', 'x-hide-tip',
        'x-list-fonts', 'x-load-color-file', 'x-menu-bar-open-internal',
        'x-menu-bar-open-internal', 'x-open-connection', 'x-open-connection',
        'x-own-selection-internal', 'x-parse-geometry', 'x-popup-dialog',
        'x-popup-menu', 'x-register-dnd-atom', 'x-select-font',
        'x-select-font', 'x-selection-exists-p', 'x-selection-owner-p',
        'x-send-client-message', 'x-server-max-request-size',
        'x-server-max-request-size', 'x-server-vendor', 'x-server-vendor',
        'x-server-version', 'x-server-version', 'x-show-tip', 'x-show-tip',
        'x-synchronize', 'x-synchronize', 'x-uses-old-gtk-dialog',
        'x-window-property', 'x-window-property', 'x-wm-set-size-hint',
        'xw-color-defined-p', 'xw-color-defined-p', 'xw-color-values',
        'xw-color-values', 'xw-display-color-p', 'xw-display-color-p',
        'yes-or-no-p', 'zlib-available-p', 'zlib-decompress-region',
        'forward-point',
    ))

    builtin_function_highlighted = set((
        'defvaralias', 'provide', 'require',
        'with-no-warnings', 'define-widget', 'with-electric-help',
        'throw', 'defalias', 'featurep'
    ))

    lambda_list_keywords = set((
        '&allow-other-keys', '&aux', '&body', '&environment', '&key', '&optional',
        '&rest', '&whole',
    ))

    error_keywords = set((
        'cl-assert', 'cl-check-type', 'error', 'signal',
        'user-error', 'warn',
    ))

    def get_tokens_unprocessed(self, text):
        stack = ['root']
        for index, token, value in RegexLexer.get_tokens_unprocessed(self, text, stack):
            if token is Name.Variable:
                if value in EmacsLispLexer.builtin_function:
                    yield index, Name.Function, value
                    continue
                if value in EmacsLispLexer.special_forms:
                    yield index, Keyword, value
                    continue
                if value in EmacsLispLexer.error_keywords:
                    yield index, Name.Exception, value
                    continue
                if value in EmacsLispLexer.builtin_function_highlighted:
                    yield index, Name.Builtin, value
                    continue
                if value in EmacsLispLexer.macros:
                    yield index, Name.Builtin, value
                    continue
                if value in EmacsLispLexer.lambda_list_keywords:
                    yield index, Keyword.Pseudo, value
                    continue
            yield index, token, value

    tokens = {
        'root': [
            default('body'),
        ],
        'body': [
            # whitespace
            (r'\s+', Text),

            # single-line comment
            (r';.*$', Comment.Single),

            # strings and characters
            (r'"', String, 'string'),
            (r'\?([^\\]|\\.)', String.Char),
            # quoting
            (r":" + symbol, Name.Builtin),
            (r"::" + symbol, String.Symbol),
            (r"'" + symbol, String.Symbol),
            (r"'", Operator),
            (r"`", Operator),

            # decimal numbers
            (r'[-+]?\d+\.?' + terminated, Number.Integer),
            (r'[-+]?\d+/\d+' + terminated, Number),
            (r'[-+]?(\d*\.\d+([defls][-+]?\d+)?|\d+(\.\d*)?[defls][-+]?\d+)' +
             terminated, Number.Float),

            # vectors
            (r'\[|\]', Punctuation),

            # uninterned symbol
            (r'#:' + symbol, String.Symbol),

            # read syntax for char tables
            (r'#\^\^?', Operator),

            # function shorthand
            (r'#\'', Name.Function),

            # binary rational
            (r'#[bB][+-]?[01]+(/[01]+)?', Number.Bin),

            # octal rational
            (r'#[oO][+-]?[0-7]+(/[0-7]+)?', Number.Oct),

            # hex rational
            (r'#[xX][+-]?[0-9a-fA-F]+(/[0-9a-fA-F]+)?', Number.Hex),

            # radix rational
            (r'#\d+r[+-]?[0-9a-zA-Z]+(/[0-9a-zA-Z]+)?', Number),

            # reference
            (r'#\d+=', Operator),
            (r'#\d+#', Operator),

            # special operators that should have been parsed already
            (r'(,@|,|\.|:)', Operator),

            # special constants
            (r'(t|nil)' + terminated, Name.Constant),

            # functions and variables
            (r'\*' + symbol + r'\*', Name.Variable.Global),
            (symbol, Name.Variable),

            # parentheses
            (r'#\(', Operator, 'body'),
            (r'\(', Punctuation, 'body'),
            (r'\)', Punctuation, '#pop'),
        ],
        'string': [
            (r'[^"\\`]+', String),
            (r'`%s\'' % symbol, String.Symbol),
            (r'`', String),
            (r'\\.', String),
            (r'\\\n', String),
            (r'"', String, '#pop'),
        ],
    }


class ShenLexer(RegexLexer):
    """
    Lexer for `Shen <http://shenlanguage.org/>`_ source code.

    .. versionadded:: 2.1
    """
    name = 'Shen'
    aliases = ['shen']
    filenames = ['*.shen']
    mimetypes = ['text/x-shen', 'application/x-shen']

    DECLARATIONS = (
        'datatype', 'define', 'defmacro', 'defprolog', 'defcc',
        'synonyms', 'declare', 'package', 'type', 'function',
    )

    SPECIAL_FORMS = (
        'lambda', 'get', 'let', 'if', 'cases', 'cond', 'put', 'time', 'freeze',
        'value', 'load', '$', 'protect', 'or', 'and', 'not', 'do', 'output',
        'prolog?', 'trap-error', 'error', 'make-string', '/.', 'set', '@p',
        '@s', '@v',
    )

    BUILTINS = (
        '==', '=', '*', '+', '-', '/', '<', '>', '>=', '<=', '<-address',
        '<-vector', 'abort', 'absvector', 'absvector?', 'address->', 'adjoin',
        'append', 'arity', 'assoc', 'bind', 'boolean?', 'bound?', 'call', 'cd',
        'close', 'cn', 'compile', 'concat', 'cons', 'cons?', 'cut', 'destroy',
        'difference', 'element?', 'empty?', 'enable-type-theory',
        'error-to-string', 'eval', 'eval-kl', 'exception', 'explode', 'external',
        'fail', 'fail-if', 'file', 'findall', 'fix', 'fst', 'fwhen', 'gensym',
        'get-time', 'hash', 'hd', 'hdstr', 'hdv', 'head', 'identical',
        'implementation', 'in', 'include', 'include-all-but', 'inferences',
        'input', 'input+', 'integer?', 'intern', 'intersection', 'is', 'kill',
        'language', 'length', 'limit', 'lineread', 'loaded', 'macro', 'macroexpand',
        'map', 'mapcan', 'maxinferences', 'mode', 'n->string', 'nl', 'nth', 'null',
        'number?', 'occurrences', 'occurs-check', 'open', 'os', 'out', 'port',
        'porters', 'pos', 'pr', 'preclude', 'preclude-all-but', 'print', 'profile',
        'profile-results', 'ps', 'quit', 'read', 'read+', 'read-byte', 'read-file',
        'read-file-as-bytelist', 'read-file-as-string', 'read-from-string',
        'release', 'remove', 'return', 'reverse', 'run', 'save', 'set',
        'simple-error', 'snd', 'specialise', 'spy', 'step', 'stinput', 'stoutput',
        'str', 'string->n', 'string->symbol', 'string?', 'subst', 'symbol?',
        'systemf', 'tail', 'tc', 'tc?', 'thaw', 'tl', 'tlstr', 'tlv', 'track',
        'tuple?', 'undefmacro', 'unify', 'unify!', 'union', 'unprofile',
        'unspecialise', 'untrack', 'variable?', 'vector', 'vector->', 'vector?',
        'verified', 'version', 'warn', 'when', 'write-byte', 'write-to-file',
        'y-or-n?',
    )

    BUILTINS_ANYWHERE = ('where', 'skip', '>>', '_', '!', '<e>', '<!>')

    MAPPINGS = dict((s, Keyword) for s in DECLARATIONS)
    MAPPINGS.update((s, Name.Builtin) for s in BUILTINS)
    MAPPINGS.update((s, Keyword) for s in SPECIAL_FORMS)

    valid_symbol_chars = r'[\w!$%*+,<=>?/.\'@&#:-]'
    valid_name = '%s+' % valid_symbol_chars
    symbol_name = r'[a-z!$%%*+,<=>?/.\'@&#_-]%s*' % valid_symbol_chars
    variable = r'[A-Z]%s*' % valid_symbol_chars

    tokens = {
        'string': [
            (r'"', String, '#pop'),
            (r'c#\d{1,3};', String.Escape),
            (r'~[ARS%]', String.Interpol),
            (r'(?s).', String),
        ],

        'root': [
            (r'(?s)\\\*.*?\*\\', Comment.Multiline),  # \* ... *\
            (r'\\\\.*', Comment.Single),              # \\ ...
            (r'\s+', Text),
            (r'_{5,}', Punctuation),
            (r'={5,}', Punctuation),
            (r'(;|:=|\||--?>|<--?)', Punctuation),
            (r'(:-|:|\{|\})', Literal),
            (r'[+-]*\d*\.\d+(e[+-]?\d+)?', Number.Float),
            (r'[+-]*\d+', Number.Integer),
            (r'"', String, 'string'),
            (variable, Name.Variable),
            (r'(true|false|<>|\[\])', Keyword.Pseudo),
            (symbol_name, Literal),
            (r'(\[|\]|\(|\))', Punctuation),
        ],
    }

    def get_tokens_unprocessed(self, text):
        tokens = RegexLexer.get_tokens_unprocessed(self, text)
        tokens = self._process_symbols(tokens)
        tokens = self._process_declarations(tokens)
        return tokens

    def _relevant(self, token):
        return token not in (Text, Comment.Single, Comment.Multiline)

    def _process_declarations(self, tokens):
        opening_paren = False
        for index, token, value in tokens:
            yield index, token, value
            if self._relevant(token):
                if opening_paren and token == Keyword and value in self.DECLARATIONS:
                    declaration = value
                    for index, token, value in \
                            self._process_declaration(declaration, tokens):
                        yield index, token, value
                opening_paren = value == '(' and token == Punctuation

    def _process_symbols(self, tokens):
        opening_paren = False
        for index, token, value in tokens:
            if opening_paren and token in (Literal, Name.Variable):
                token = self.MAPPINGS.get(value, Name.Function)
            elif token == Literal and value in self.BUILTINS_ANYWHERE:
                token = Name.Builtin
            opening_paren = value == '(' and token == Punctuation
            yield index, token, value

    def _process_declaration(self, declaration, tokens):
        for index, token, value in tokens:
            if self._relevant(token):
                break
            yield index, token, value

        if declaration == 'datatype':
            prev_was_colon = False
            token = Keyword.Type if token == Literal else token
            yield index, token, value
            for index, token, value in tokens:
                if prev_was_colon and token == Literal:
                    token = Keyword.Type
                yield index, token, value
                if self._relevant(token):
                    prev_was_colon = token == Literal and value == ':'
        elif declaration == 'package':
            token = Name.Namespace if token == Literal else token
            yield index, token, value
        elif declaration == 'define':
            token = Name.Function if token == Literal else token
            yield index, token, value
            for index, token, value in tokens:
                if self._relevant(token):
                    break
                yield index, token, value
            if value == '{' and token == Literal:
                yield index, Punctuation, value
                for index, token, value in self._process_signature(tokens):
                    yield index, token, value
            else:
                yield index, token, value
        else:
            token = Name.Function if token == Literal else token
            yield index, token, value

        return

    def _process_signature(self, tokens):
        for index, token, value in tokens:
            if token == Literal and value == '}':
                yield index, Punctuation, value
                return
            elif token in (Literal, Name.Function):
                token = Name.Variable if value.istitle() else Keyword.Type
            yield index, token, value


class CPSALexer(SchemeLexer):
    """
    A CPSA lexer based on the CPSA language as of version 2.2.12

    .. versionadded:: 2.1
    """
    name = 'CPSA'
    aliases = ['cpsa']
    filenames = ['*.cpsa']
    mimetypes = []

    # list of known keywords and builtins taken form vim 6.4 scheme.vim
    # syntax file.
    _keywords = (
        'herald', 'vars', 'defmacro', 'include', 'defprotocol', 'defrole',
        'defskeleton', 'defstrand', 'deflistener', 'non-orig', 'uniq-orig',
        'pen-non-orig', 'precedes', 'trace', 'send', 'recv', 'name', 'text',
        'skey', 'akey', 'data', 'mesg',
    )
    _builtins = (
        'cat', 'enc', 'hash', 'privk', 'pubk', 'invk', 'ltk', 'gen', 'exp',
    )

    # valid names for identifiers
    # well, names can only not consist fully of numbers
    # but this should be good enough for now
    valid_name = r'[\w!$%&*+,/:<=>?@^~|-]+'

    tokens = {
        'root': [
            # the comments - always starting with semicolon
            # and going to the end of the line
            (r';.*$', Comment.Single),

            # whitespaces - usually not relevant
            (r'\s+', Text),

            # numbers
            (r'-?\d+\.\d+', Number.Float),
            (r'-?\d+', Number.Integer),
            # support for uncommon kinds of numbers -
            # have to figure out what the characters mean
            # (r'(#e|#i|#b|#o|#d|#x)[\d.]+', Number),

            # strings, symbols and characters
            (r'"(\\\\|\\"|[^"])*"', String),
            (r"'" + valid_name, String.Symbol),
            (r"#\\([()/'\"._!§$%& ?=+-]|[a-zA-Z0-9]+)", String.Char),

            # constants
            (r'(#t|#f)', Name.Constant),

            # special operators
            (r"('|#|`|,@|,|\.)", Operator),

            # highlight the keywords
            (words(_keywords, suffix=r'\b'), Keyword),

            # first variable in a quoted string like
            # '(this is syntactic sugar)
            (r"(?<='\()" + valid_name, Name.Variable),
            (r"(?<=#\()" + valid_name, Name.Variable),

            # highlight the builtins
            (words(_builtins, prefix=r'(?<=\()', suffix=r'\b'), Name.Builtin),

            # the remaining functions
            (r'(?<=\()' + valid_name, Name.Function),
            # find the remaining variables
            (valid_name, Name.Variable),

            # the famous parentheses!
            (r'(\(|\))', Punctuation),
            (r'(\[|\])', Punctuation),
        ],
    }


class XtlangLexer(RegexLexer):
    """An xtlang lexer for the `Extempore programming environment
    <http://extempore.moso.com.au>`_.

    This is a mixture of Scheme and xtlang, really. Keyword lists are
    taken from the Extempore Emacs mode
    (https://github.com/extemporelang/extempore-emacs-mode)

    .. versionadded:: 2.2
    """
    name = 'xtlang'
    aliases = ['extempore']
    filenames = ['*.xtm']
    mimetypes = []

    common_keywords = (
        'lambda', 'define', 'if', 'else', 'cond', 'and',
        'or', 'let', 'begin', 'set!', 'map', 'for-each',
    )
    scheme_keywords = (
        'do', 'delay', 'quasiquote', 'unquote', 'unquote-splicing', 'eval',
        'case', 'let*', 'letrec', 'quote',
    )
    xtlang_bind_keywords = (
        'bind-func', 'bind-val', 'bind-lib', 'bind-type', 'bind-alias',
        'bind-poly', 'bind-dylib', 'bind-lib-func', 'bind-lib-val',
    )
    xtlang_keywords = (
        'letz', 'memzone', 'cast', 'convert', 'dotimes', 'doloop',
    )
    common_functions = (
        '*', '+', '-', '/', '<', '<=', '=', '>', '>=', '%', 'abs', 'acos',
        'angle', 'append', 'apply', 'asin', 'assoc', 'assq', 'assv',
        'atan', 'boolean?', 'caaaar', 'caaadr', 'caaar', 'caadar',
        'caaddr', 'caadr', 'caar', 'cadaar', 'cadadr', 'cadar',
        'caddar', 'cadddr', 'caddr', 'cadr', 'car', 'cdaaar',
        'cdaadr', 'cdaar', 'cdadar', 'cdaddr', 'cdadr', 'cdar',
        'cddaar', 'cddadr', 'cddar', 'cdddar', 'cddddr', 'cdddr',
        'cddr', 'cdr', 'ceiling', 'cons', 'cos', 'floor', 'length',
        'list', 'log', 'max', 'member', 'min', 'modulo', 'not',
        'reverse', 'round', 'sin', 'sqrt', 'substring', 'tan',
        'println', 'random', 'null?', 'callback', 'now',
    )
    scheme_functions = (
        'call-with-current-continuation', 'call-with-input-file',
        'call-with-output-file', 'call-with-values', 'call/cc',
        'char->integer', 'char-alphabetic?', 'char-ci<=?', 'char-ci<?',
        'char-ci=?', 'char-ci>=?', 'char-ci>?', 'char-downcase',
        'char-lower-case?', 'char-numeric?', 'char-ready?',
        'char-upcase', 'char-upper-case?', 'char-whitespace?',
        'char<=?', 'char<?', 'char=?', 'char>=?', 'char>?', 'char?',
        'close-input-port', 'close-output-port', 'complex?',
        'current-input-port', 'current-output-port', 'denominator',
        'display', 'dynamic-wind', 'eof-object?', 'eq?', 'equal?',
        'eqv?', 'even?', 'exact->inexact', 'exact?', 'exp', 'expt',
        'force', 'gcd', 'imag-part', 'inexact->exact', 'inexact?',
        'input-port?', 'integer->char', 'integer?',
        'interaction-environment', 'lcm', 'list->string',
        'list->vector', 'list-ref', 'list-tail', 'list?', 'load',
        'magnitude', 'make-polar', 'make-rectangular', 'make-string',
        'make-vector', 'memq', 'memv', 'negative?', 'newline',
        'null-environment', 'number->string', 'number?',
        'numerator', 'odd?', 'open-input-file', 'open-output-file',
        'output-port?', 'pair?', 'peek-char', 'port?', 'positive?',
        'procedure?', 'quotient', 'rational?', 'rationalize', 'read',
        'read-char', 'real-part', 'real?',
        'remainder', 'scheme-report-environment', 'set-car!', 'set-cdr!',
        'string', 'string->list', 'string->number', 'string->symbol',
        'string-append', 'string-ci<=?', 'string-ci<?', 'string-ci=?',
        'string-ci>=?', 'string-ci>?', 'string-copy', 'string-fill!',
        'string-length', 'string-ref', 'string-set!', 'string<=?',
        'string<?', 'string=?', 'string>=?', 'string>?', 'string?',
        'symbol->string', 'symbol?', 'transcript-off', 'transcript-on',
        'truncate', 'values', 'vector', 'vector->list', 'vector-fill!',
        'vector-length', 'vector?',
        'with-input-from-file', 'with-output-to-file', 'write',
        'write-char', 'zero?',
    )
    xtlang_functions = (
        'toString', 'afill!', 'pfill!', 'tfill!', 'tbind', 'vfill!',
        'array-fill!', 'pointer-fill!', 'tuple-fill!', 'vector-fill!', 'free',
        'array', 'tuple', 'list', '~', 'cset!', 'cref', '&', 'bor',
        'ang-names', '<<', '>>', 'nil', 'printf', 'sprintf', 'null', 'now',
        'pset!', 'pref-ptr', 'vset!', 'vref', 'aset!', 'aref', 'aref-ptr',
        'tset!', 'tref', 'tref-ptr', 'salloc', 'halloc', 'zalloc', 'alloc',
        'schedule', 'exp', 'log', 'sin', 'cos', 'tan', 'asin', 'acos', 'atan',
        'sqrt', 'expt', 'floor', 'ceiling', 'truncate', 'round',
        'llvm_printf', 'push_zone', 'pop_zone', 'memzone', 'callback',
        'llvm_sprintf', 'make-array', 'array-set!', 'array-ref',
        'array-ref-ptr', 'pointer-set!', 'pointer-ref', 'pointer-ref-ptr',
        'stack-alloc', 'heap-alloc', 'zone-alloc', 'make-tuple', 'tuple-set!',
        'tuple-ref', 'tuple-ref-ptr', 'closure-set!', 'closure-ref', 'pref',
        'pdref', 'impc_null', 'bitcast', 'void', 'ifret', 'ret->', 'clrun->',
        'make-env-zone', 'make-env', '<>', 'dtof', 'ftod', 'i1tof',
        'i1tod', 'i1toi8', 'i1toi32', 'i1toi64', 'i8tof', 'i8tod',
        'i8toi1', 'i8toi32', 'i8toi64', 'i32tof', 'i32tod', 'i32toi1',
        'i32toi8', 'i32toi64', 'i64tof', 'i64tod', 'i64toi1',
        'i64toi8', 'i64toi32',
    )

    # valid names for Scheme identifiers (names cannot consist fully
    # of numbers, but this should be good enough for now)
    valid_scheme_name = r'[\w!$%&*+,/:<=>?@^~|-]+'

    # valid characters in xtlang names & types
    valid_xtlang_name = r'[\w.!-]+'
    valid_xtlang_type = r'[]{}[\w<>,*/|!-]+'

    tokens = {
        # keep track of when we're exiting the xtlang form
        'xtlang': [
            (r'\(', Punctuation, '#push'),
            (r'\)', Punctuation, '#pop'),

            (r'(?<=bind-func\s)' + valid_xtlang_name, Name.Function),
            (r'(?<=bind-val\s)' + valid_xtlang_name, Name.Function),
            (r'(?<=bind-type\s)' + valid_xtlang_name, Name.Function),
            (r'(?<=bind-alias\s)' + valid_xtlang_name, Name.Function),
            (r'(?<=bind-poly\s)' + valid_xtlang_name, Name.Function),
            (r'(?<=bind-lib\s)' + valid_xtlang_name, Name.Function),
            (r'(?<=bind-dylib\s)' + valid_xtlang_name, Name.Function),
            (r'(?<=bind-lib-func\s)' + valid_xtlang_name, Name.Function),
            (r'(?<=bind-lib-val\s)' + valid_xtlang_name, Name.Function),

            # type annotations
            (r':' + valid_xtlang_type, Keyword.Type),

            # types
            (r'(<' + valid_xtlang_type + r'>|\|' + valid_xtlang_type + r'\||/' +
             valid_xtlang_type + r'/|' + valid_xtlang_type + r'\*)\**',
             Keyword.Type),

            # keywords
            (words(xtlang_keywords, prefix=r'(?<=\()'), Keyword),

            # builtins
            (words(xtlang_functions, prefix=r'(?<=\()'), Name.Function),

            include('common'),

            # variables
            (valid_xtlang_name, Name.Variable),
        ],
        'scheme': [
            # quoted symbols
            (r"'" + valid_scheme_name, String.Symbol),

            # char literals
            (r"#\\([()/'\"._!§$%& ?=+-]|[a-zA-Z0-9]+)", String.Char),

            # special operators
            (r"('|#|`|,@|,|\.)", Operator),

            # keywords
            (words(scheme_keywords, prefix=r'(?<=\()'), Keyword),

            # builtins
            (words(scheme_functions, prefix=r'(?<=\()'), Name.Function),

            include('common'),

            # variables
            (valid_scheme_name, Name.Variable),
        ],
        # common to both xtlang and Scheme
        'common': [
            # comments
            (r';.*$', Comment.Single),

            # whitespaces - usually not relevant
            (r'\s+', Text),

            # numbers
            (r'-?\d+\.\d+', Number.Float),
            (r'-?\d+', Number.Integer),

            # binary/oct/hex literals
            (r'(#b|#o|#x)[\d.]+', Number),

            # strings
            (r'"(\\\\|\\"|[^"])*"', String),

            # true/false constants
            (r'(#t|#f)', Name.Constant),

            # keywords
            (words(common_keywords, prefix=r'(?<=\()'), Keyword),

            # builtins
            (words(common_functions, prefix=r'(?<=\()'), Name.Function),

            # the famous parentheses!
            (r'(\(|\))', Punctuation),
        ],
        'root': [
            # go into xtlang mode
            (words(xtlang_bind_keywords, prefix=r'(?<=\()', suffix=r'\b'),
             Keyword, 'xtlang'),

            include('scheme')
        ],
    }


class FennelLexer(RegexLexer):
    """A lexer for the `Fennel programming language <https://fennel-lang.org>`_.

    Fennel compiles to Lua, so all the Lua builtins are recognized as well
    as the special forms that are particular to the Fennel compiler.

    .. versionadded:: 2.3
    """
    name = 'Fennel'
    aliases = ['fennel', 'fnl']
    filenames = ['*.fnl']

    # these two lists are taken from fennel-mode.el:
    # https://gitlab.com/technomancy/fennel-mode
    # this list is current as of Fennel version 0.1.0.
    special_forms = (
        u'require-macros', u'eval-compiler',
        u'do', u'values', u'if', u'when', u'each', u'for', u'fn', u'lambda',
        u'λ', u'set', u'global', u'var', u'local', u'let', u'tset', u'doto',
        u'set-forcibly!', u'defn', u'partial', u'while', u'or', u'and', u'true',
        u'false', u'nil', u'.', u'+', u'..', u'^', u'-', u'*', u'%', u'/', u'>',
        u'<', u'>=', u'<=', u'=', u'~=', u'#', u'...', u':', u'->', u'->>',
    )

    # Might be nicer to use the list from _lua_builtins.py but it's unclear how?
    builtins = (
        u'_G', u'_VERSION', u'arg', u'assert', u'bit32', u'collectgarbage',
        u'coroutine', u'debug', u'dofile', u'error', u'getfenv',
        u'getmetatable', u'io', u'ipairs', u'load', u'loadfile', u'loadstring',
        u'math', u'next', u'os', u'package', u'pairs', u'pcall', u'print',
        u'rawequal', u'rawget', u'rawlen', u'rawset', u'require', u'select',
        u'setfenv', u'setmetatable', u'string', u'table', u'tonumber',
        u'tostring', u'type', u'unpack', u'xpcall'
    )

    # based on the scheme definition, but disallowing leading digits and commas
    valid_name = r'[a-zA-Z_!$%&*+/:<=>?@^~|-][\w!$%&*+/:<=>?@^~|\.-]*'

    tokens = {
        'root': [
            # the only comment form is a semicolon; goes to the end of the line
            (r';.*$', Comment.Single),

            (r'[,\s]+', Text),
            (r'-?\d+\.\d+', Number.Float),
            (r'-?\d+', Number.Integer),

            (r'"(\\\\|\\"|[^"])*"', String),
            (r"'(\\\\|\\'|[^'])*'", String),

            # these are technically strings, but it's worth visually
            # distinguishing them because their intent is different
            # from regular strings.
            (r':' + valid_name, String.Symbol),

            # special forms are keywords
            (words(special_forms, suffix=' '), Keyword),
            # lua standard library are builtins
            (words(builtins, suffix=' '), Name.Builtin),
            # special-case the vararg symbol
            (r'\.\.\.', Name.Variable),
            # regular identifiers
            (valid_name, Name.Variable),

            # all your normal paired delimiters for your programming enjoyment
            (r'(\(|\))', Punctuation),
            (r'(\[|\])', Punctuation),
            (r'(\{|\})', Punctuation),
        ]
    }
