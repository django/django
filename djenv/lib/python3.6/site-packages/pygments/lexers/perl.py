# -*- coding: utf-8 -*-
"""
    pygments.lexers.perl
    ~~~~~~~~~~~~~~~~~~~~

    Lexers for Perl and related languages.

    :copyright: Copyright 2006-2017 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from pygments.lexer import RegexLexer, ExtendedRegexLexer, include, bygroups, \
    using, this, default, words
from pygments.token import Text, Comment, Operator, Keyword, Name, String, \
    Number, Punctuation
from pygments.util import shebang_matches

__all__ = ['PerlLexer', 'Perl6Lexer']


class PerlLexer(RegexLexer):
    """
    For `Perl <http://www.perl.org>`_ source code.
    """

    name = 'Perl'
    aliases = ['perl', 'pl']
    filenames = ['*.pl', '*.pm', '*.t']
    mimetypes = ['text/x-perl', 'application/x-perl']

    flags = re.DOTALL | re.MULTILINE
    # TODO: give this to a perl guy who knows how to parse perl...
    tokens = {
        'balanced-regex': [
            (r'/(\\\\|\\[^\\]|[^\\/])*/[egimosx]*', String.Regex, '#pop'),
            (r'!(\\\\|\\[^\\]|[^\\!])*![egimosx]*', String.Regex, '#pop'),
            (r'\\(\\\\|[^\\])*\\[egimosx]*', String.Regex, '#pop'),
            (r'\{(\\\\|\\[^\\]|[^\\}])*\}[egimosx]*', String.Regex, '#pop'),
            (r'<(\\\\|\\[^\\]|[^\\>])*>[egimosx]*', String.Regex, '#pop'),
            (r'\[(\\\\|\\[^\\]|[^\\\]])*\][egimosx]*', String.Regex, '#pop'),
            (r'\((\\\\|\\[^\\]|[^\\)])*\)[egimosx]*', String.Regex, '#pop'),
            (r'@(\\\\|\\[^\\]|[^\\@])*@[egimosx]*', String.Regex, '#pop'),
            (r'%(\\\\|\\[^\\]|[^\\%])*%[egimosx]*', String.Regex, '#pop'),
            (r'\$(\\\\|\\[^\\]|[^\\$])*\$[egimosx]*', String.Regex, '#pop'),
        ],
        'root': [
            (r'\A\#!.+?$', Comment.Hashbang),
            (r'\#.*?$', Comment.Single),
            (r'^=[a-zA-Z0-9]+\s+.*?\n=cut', Comment.Multiline),
            (words((
                'case', 'continue', 'do', 'else', 'elsif', 'for', 'foreach',
                'if', 'last', 'my', 'next', 'our', 'redo', 'reset', 'then',
                'unless', 'until', 'while', 'print', 'new', 'BEGIN',
                'CHECK', 'INIT', 'END', 'return'), suffix=r'\b'),
             Keyword),
            (r'(format)(\s+)(\w+)(\s*)(=)(\s*\n)',
             bygroups(Keyword, Text, Name, Text, Punctuation, Text), 'format'),
            (r'(eq|lt|gt|le|ge|ne|not|and|or|cmp)\b', Operator.Word),
            # common delimiters
            (r's/(\\\\|\\[^\\]|[^\\/])*/(\\\\|\\[^\\]|[^\\/])*/[egimosx]*',
                String.Regex),
            (r's!(\\\\|\\!|[^!])*!(\\\\|\\!|[^!])*![egimosx]*', String.Regex),
            (r's\\(\\\\|[^\\])*\\(\\\\|[^\\])*\\[egimosx]*', String.Regex),
            (r's@(\\\\|\\[^\\]|[^\\@])*@(\\\\|\\[^\\]|[^\\@])*@[egimosx]*',
                String.Regex),
            (r's%(\\\\|\\[^\\]|[^\\%])*%(\\\\|\\[^\\]|[^\\%])*%[egimosx]*',
                String.Regex),
            # balanced delimiters
            (r's\{(\\\\|\\[^\\]|[^\\}])*\}\s*', String.Regex, 'balanced-regex'),
            (r's<(\\\\|\\[^\\]|[^\\>])*>\s*', String.Regex, 'balanced-regex'),
            (r's\[(\\\\|\\[^\\]|[^\\\]])*\]\s*', String.Regex,
                'balanced-regex'),
            (r's\((\\\\|\\[^\\]|[^\\)])*\)\s*', String.Regex,
                'balanced-regex'),

            (r'm?/(\\\\|\\[^\\]|[^\\/\n])*/[gcimosx]*', String.Regex),
            (r'm(?=[/!\\{<\[(@%$])', String.Regex, 'balanced-regex'),
            (r'((?<==~)|(?<=\())\s*/(\\\\|\\[^\\]|[^\\/])*/[gcimosx]*',
                String.Regex),
            (r'\s+', Text),
            (words((
                'abs', 'accept', 'alarm', 'atan2', 'bind', 'binmode', 'bless', 'caller', 'chdir',
                'chmod', 'chomp', 'chop', 'chown', 'chr', 'chroot', 'close', 'closedir', 'connect',
                'continue', 'cos', 'crypt', 'dbmclose', 'dbmopen', 'defined', 'delete', 'die',
                'dump', 'each', 'endgrent', 'endhostent', 'endnetent', 'endprotoent',
                'endpwent', 'endservent', 'eof', 'eval', 'exec', 'exists', 'exit', 'exp', 'fcntl',
                'fileno', 'flock', 'fork', 'format', 'formline', 'getc', 'getgrent', 'getgrgid',
                'getgrnam', 'gethostbyaddr', 'gethostbyname', 'gethostent', 'getlogin',
                'getnetbyaddr', 'getnetbyname', 'getnetent', 'getpeername', 'getpgrp',
                'getppid', 'getpriority', 'getprotobyname', 'getprotobynumber',
                'getprotoent', 'getpwent', 'getpwnam', 'getpwuid', 'getservbyname',
                'getservbyport', 'getservent', 'getsockname', 'getsockopt', 'glob', 'gmtime',
                'goto', 'grep', 'hex', 'import', 'index', 'int', 'ioctl', 'join', 'keys', 'kill', 'last',
                'lc', 'lcfirst', 'length', 'link', 'listen', 'local', 'localtime', 'log', 'lstat',
                'map', 'mkdir', 'msgctl', 'msgget', 'msgrcv', 'msgsnd', 'my', 'next', 'oct', 'open',
                'opendir', 'ord', 'our', 'pack', 'pipe', 'pop', 'pos', 'printf',
                'prototype', 'push', 'quotemeta', 'rand', 'read', 'readdir',
                'readline', 'readlink', 'readpipe', 'recv', 'redo', 'ref', 'rename',
                'reverse', 'rewinddir', 'rindex', 'rmdir', 'scalar', 'seek', 'seekdir',
                'select', 'semctl', 'semget', 'semop', 'send', 'setgrent', 'sethostent', 'setnetent',
                'setpgrp', 'setpriority', 'setprotoent', 'setpwent', 'setservent',
                'setsockopt', 'shift', 'shmctl', 'shmget', 'shmread', 'shmwrite', 'shutdown',
                'sin', 'sleep', 'socket', 'socketpair', 'sort', 'splice', 'split', 'sprintf', 'sqrt',
                'srand', 'stat', 'study', 'substr', 'symlink', 'syscall', 'sysopen', 'sysread',
                'sysseek', 'system', 'syswrite', 'tell', 'telldir', 'tie', 'tied', 'time', 'times', 'tr',
                'truncate', 'uc', 'ucfirst', 'umask', 'undef', 'unlink', 'unpack', 'unshift', 'untie',
                'utime', 'values', 'vec', 'wait', 'waitpid', 'wantarray', 'warn', 'write'), suffix=r'\b'),
             Name.Builtin),
            (r'((__(DATA|DIE|WARN)__)|(STD(IN|OUT|ERR)))\b', Name.Builtin.Pseudo),
            (r'(<<)([\'"]?)([a-zA-Z_]\w*)(\2;?\n.*?\n)(\3)(\n)',
             bygroups(String, String, String.Delimiter, String, String.Delimiter, Text)),
            (r'__END__', Comment.Preproc, 'end-part'),
            (r'\$\^[ADEFHILMOPSTWX]', Name.Variable.Global),
            (r"\$[\\\"\[\]'&`+*.,;=%~?@$!<>(^|/-](?!\w)", Name.Variable.Global),
            (r'[$@%#]+', Name.Variable, 'varname'),
            (r'0_?[0-7]+(_[0-7]+)*', Number.Oct),
            (r'0x[0-9A-Fa-f]+(_[0-9A-Fa-f]+)*', Number.Hex),
            (r'0b[01]+(_[01]+)*', Number.Bin),
            (r'(?i)(\d*(_\d*)*\.\d+(_\d*)*|\d+(_\d*)*\.\d+(_\d*)*)(e[+-]?\d+)?',
             Number.Float),
            (r'(?i)\d+(_\d*)*e[+-]?\d+(_\d*)*', Number.Float),
            (r'\d+(_\d+)*', Number.Integer),
            (r"'(\\\\|\\[^\\]|[^'\\])*'", String),
            (r'"(\\\\|\\[^\\]|[^"\\])*"', String),
            (r'`(\\\\|\\[^\\]|[^`\\])*`', String.Backtick),
            (r'<([^\s>]+)>', String.Regex),
            (r'(q|qq|qw|qr|qx)\{', String.Other, 'cb-string'),
            (r'(q|qq|qw|qr|qx)\(', String.Other, 'rb-string'),
            (r'(q|qq|qw|qr|qx)\[', String.Other, 'sb-string'),
            (r'(q|qq|qw|qr|qx)\<', String.Other, 'lt-string'),
            (r'(q|qq|qw|qr|qx)([\W_])(.|\n)*?\2', String.Other),
            (r'(package)(\s+)([a-zA-Z_]\w*(?:::[a-zA-Z_]\w*)*)',
             bygroups(Keyword, Text, Name.Namespace)),
            (r'(use|require|no)(\s+)([a-zA-Z_]\w*(?:::[a-zA-Z_]\w*)*)',
             bygroups(Keyword, Text, Name.Namespace)),
            (r'(sub)(\s+)', bygroups(Keyword, Text), 'funcname'),
            (words((
                'no', 'package', 'require', 'use'), suffix=r'\b'),
             Keyword),
            (r'(\[\]|\*\*|::|<<|>>|>=|<=>|<=|={3}|!=|=~|'
             r'!~|&&?|\|\||\.{1,3})', Operator),
            (r'[-+/*%=<>&^|!\\~]=?', Operator),
            (r'[()\[\]:;,<>/?{}]', Punctuation),  # yes, there's no shortage
                                                  # of punctuation in Perl!
            (r'(?=\w)', Name, 'name'),
        ],
        'format': [
            (r'\.\n', String.Interpol, '#pop'),
            (r'[^\n]*\n', String.Interpol),
        ],
        'varname': [
            (r'\s+', Text),
            (r'\{', Punctuation, '#pop'),    # hash syntax?
            (r'\)|,', Punctuation, '#pop'),  # argument specifier
            (r'\w+::', Name.Namespace),
            (r'[\w:]+', Name.Variable, '#pop'),
        ],
        'name': [
            (r'[a-zA-Z_]\w*(::[a-zA-Z_]\w*)*(::)?(?=\s*->)', Name.Namespace, '#pop'),
            (r'[a-zA-Z_]\w*(::[a-zA-Z_]\w*)*::', Name.Namespace, '#pop'),
            (r'[\w:]+', Name, '#pop'),
            (r'[A-Z_]+(?=\W)', Name.Constant, '#pop'),
            (r'(?=\W)', Text, '#pop'),
        ],
        'funcname': [
            (r'[a-zA-Z_]\w*[!?]?', Name.Function),
            (r'\s+', Text),
            # argument declaration
            (r'(\([$@%]*\))(\s*)', bygroups(Punctuation, Text)),
            (r';', Punctuation, '#pop'),
            (r'.*?\{', Punctuation, '#pop'),
        ],
        'cb-string': [
            (r'\\[{}\\]', String.Other),
            (r'\\', String.Other),
            (r'\{', String.Other, 'cb-string'),
            (r'\}', String.Other, '#pop'),
            (r'[^{}\\]+', String.Other)
        ],
        'rb-string': [
            (r'\\[()\\]', String.Other),
            (r'\\', String.Other),
            (r'\(', String.Other, 'rb-string'),
            (r'\)', String.Other, '#pop'),
            (r'[^()]+', String.Other)
        ],
        'sb-string': [
            (r'\\[\[\]\\]', String.Other),
            (r'\\', String.Other),
            (r'\[', String.Other, 'sb-string'),
            (r'\]', String.Other, '#pop'),
            (r'[^\[\]]+', String.Other)
        ],
        'lt-string': [
            (r'\\[<>\\]', String.Other),
            (r'\\', String.Other),
            (r'\<', String.Other, 'lt-string'),
            (r'\>', String.Other, '#pop'),
            (r'[^<>]+', String.Other)
        ],
        'end-part': [
            (r'.+', Comment.Preproc, '#pop')
        ]
    }

    def analyse_text(text):
        if shebang_matches(text, r'perl'):
            return True
        if re.search(r'(?:my|our)\s+[$@%(]', text):
            return 0.9


class Perl6Lexer(ExtendedRegexLexer):
    """
    For `Perl 6 <http://www.perl6.org>`_ source code.

    .. versionadded:: 2.0
    """

    name = 'Perl6'
    aliases = ['perl6', 'pl6']
    filenames = ['*.pl', '*.pm', '*.nqp', '*.p6', '*.6pl', '*.p6l', '*.pl6',
                 '*.6pm', '*.p6m', '*.pm6', '*.t']
    mimetypes = ['text/x-perl6', 'application/x-perl6']
    flags = re.MULTILINE | re.DOTALL | re.UNICODE

    PERL6_IDENTIFIER_RANGE = r"['\w:-]"

    PERL6_KEYWORDS = (
        'BEGIN', 'CATCH', 'CHECK', 'CONTROL', 'END', 'ENTER', 'FIRST', 'INIT',
        'KEEP', 'LAST', 'LEAVE', 'NEXT', 'POST', 'PRE', 'START', 'TEMP',
        'UNDO', 'as', 'assoc', 'async', 'augment', 'binary', 'break', 'but',
        'cached', 'category', 'class', 'constant', 'contend', 'continue',
        'copy', 'deep', 'default', 'defequiv', 'defer', 'die', 'do', 'else',
        'elsif', 'enum', 'equiv', 'exit', 'export', 'fail', 'fatal', 'for',
        'gather', 'given', 'goto', 'grammar', 'handles', 'has', 'if', 'inline',
        'irs', 'is', 'last', 'leave', 'let', 'lift', 'loop', 'looser', 'macro',
        'make', 'maybe', 'method', 'module', 'multi', 'my', 'next', 'of',
        'ofs', 'only', 'oo', 'ors', 'our', 'package', 'parsed', 'prec',
        'proto', 'readonly', 'redo', 'ref', 'regex', 'reparsed', 'repeat',
        'require', 'required', 'return', 'returns', 'role', 'rule', 'rw',
        'self', 'slang', 'state', 'sub', 'submethod', 'subset', 'supersede',
        'take', 'temp', 'tighter', 'token', 'trusts', 'try', 'unary',
        'unless', 'until', 'use', 'warn', 'when', 'where', 'while', 'will',
    )

    PERL6_BUILTINS = (
        'ACCEPTS', 'HOW', 'REJECTS', 'VAR', 'WHAT', 'WHENCE', 'WHERE', 'WHICH',
        'WHO', 'abs', 'acos', 'acosec', 'acosech', 'acosh', 'acotan', 'acotanh',
        'all', 'any', 'approx', 'arity', 'asec', 'asech', 'asin', 'asinh',
        'assuming', 'atan', 'atan2', 'atanh', 'attr', 'bless', 'body', 'by',
        'bytes', 'caller', 'callsame', 'callwith', 'can', 'capitalize', 'cat',
        'ceiling', 'chars', 'chmod', 'chomp', 'chop', 'chr', 'chroot',
        'circumfix', 'cis', 'classify', 'clone', 'close', 'cmp_ok', 'codes',
        'comb', 'connect', 'contains', 'context', 'cos', 'cosec', 'cosech',
        'cosh', 'cotan', 'cotanh', 'count', 'defined', 'delete', 'diag',
        'dies_ok', 'does', 'e', 'each', 'eager', 'elems', 'end', 'eof', 'eval',
        'eval_dies_ok', 'eval_elsewhere', 'eval_lives_ok', 'evalfile', 'exists',
        'exp', 'first', 'flip', 'floor', 'flunk', 'flush', 'fmt', 'force_todo',
        'fork', 'from', 'getc', 'gethost', 'getlogin', 'getpeername', 'getpw',
        'gmtime', 'graphs', 'grep', 'hints', 'hyper', 'im', 'index', 'infix',
        'invert', 'is_approx', 'is_deeply', 'isa', 'isa_ok', 'isnt', 'iterator',
        'join', 'key', 'keys', 'kill', 'kv', 'lastcall', 'lazy', 'lc', 'lcfirst',
        'like', 'lines', 'link', 'lives_ok', 'localtime', 'log', 'log10', 'map',
        'max', 'min', 'minmax', 'name', 'new', 'nextsame', 'nextwith', 'nfc',
        'nfd', 'nfkc', 'nfkd', 'nok_error', 'nonce', 'none', 'normalize', 'not',
        'nothing', 'ok', 'once', 'one', 'open', 'opendir', 'operator', 'ord',
        'p5chomp', 'p5chop', 'pack', 'pair', 'pairs', 'pass', 'perl', 'pi',
        'pick', 'plan', 'plan_ok', 'polar', 'pop', 'pos', 'postcircumfix',
        'postfix', 'pred', 'prefix', 'print', 'printf', 'push', 'quasi',
        'quotemeta', 'rand', 're', 'read', 'readdir', 'readline', 'reduce',
        'reverse', 'rewind', 'rewinddir', 'rindex', 'roots', 'round',
        'roundrobin', 'run', 'runinstead', 'sameaccent', 'samecase', 'say',
        'sec', 'sech', 'sech', 'seek', 'shape', 'shift', 'sign', 'signature',
        'sin', 'sinh', 'skip', 'skip_rest', 'sleep', 'slurp', 'sort', 'splice',
        'split', 'sprintf', 'sqrt', 'srand', 'strand', 'subst', 'substr', 'succ',
        'sum', 'symlink', 'tan', 'tanh', 'throws_ok', 'time', 'times', 'to',
        'todo', 'trim', 'trim_end', 'trim_start', 'true', 'truncate', 'uc',
        'ucfirst', 'undef', 'undefine', 'uniq', 'unlike', 'unlink', 'unpack',
        'unpolar', 'unshift', 'unwrap', 'use_ok', 'value', 'values', 'vec',
        'version_lt', 'void', 'wait', 'want', 'wrap', 'write', 'zip',
    )

    PERL6_BUILTIN_CLASSES = (
        'Abstraction', 'Any', 'AnyChar', 'Array', 'Associative', 'Bag', 'Bit',
        'Blob', 'Block', 'Bool', 'Buf', 'Byte', 'Callable', 'Capture', 'Char', 'Class',
        'Code', 'Codepoint', 'Comparator', 'Complex', 'Decreasing', 'Exception',
        'Failure', 'False', 'Grammar', 'Grapheme', 'Hash', 'IO', 'Increasing',
        'Int', 'Junction', 'KeyBag', 'KeyExtractor', 'KeyHash', 'KeySet',
        'KitchenSink', 'List', 'Macro', 'Mapping', 'Match', 'Matcher', 'Method',
        'Module', 'Num', 'Object', 'Ordered', 'Ordering', 'OrderingPair',
        'Package', 'Pair', 'Positional', 'Proxy', 'Range', 'Rat', 'Regex',
        'Role', 'Routine', 'Scalar', 'Seq', 'Set', 'Signature', 'Str', 'StrLen',
        'StrPos', 'Sub', 'Submethod', 'True', 'UInt', 'Undef', 'Version', 'Void',
        'Whatever', 'bit', 'bool', 'buf', 'buf1', 'buf16', 'buf2', 'buf32',
        'buf4', 'buf64', 'buf8', 'complex', 'int', 'int1', 'int16', 'int2',
        'int32', 'int4', 'int64', 'int8', 'num', 'rat', 'rat1', 'rat16', 'rat2',
        'rat32', 'rat4', 'rat64', 'rat8', 'uint', 'uint1', 'uint16', 'uint2',
        'uint32', 'uint4', 'uint64', 'uint8', 'utf16', 'utf32', 'utf8',
    )

    PERL6_OPERATORS = (
        'X', 'Z', 'after', 'also', 'and', 'andthen', 'before', 'cmp', 'div',
        'eq', 'eqv', 'extra', 'ff', 'fff', 'ge', 'gt', 'le', 'leg', 'lt', 'm',
        'mm', 'mod', 'ne', 'or', 'orelse', 'rx', 's', 'tr', 'x', 'xor', 'xx',
        '++', '--', '**', '!', '+', '-', '~', '?', '|', '||', '+^', '~^', '?^',
        '^', '*', '/', '%', '%%', '+&', '+<', '+>', '~&', '~<', '~>', '?&',
        'gcd', 'lcm', '+', '-', '+|', '+^', '~|', '~^', '?|', '?^',
        '~', '&', '^', 'but', 'does', '<=>', '..', '..^', '^..', '^..^',
        '!=', '==', '<', '<=', '>', '>=', '~~', '===', '!eqv',
        '&&', '||', '^^', '//', 'min', 'max', '??', '!!', 'ff', 'fff', 'so',
        'not', '<==', '==>', '<<==', '==>>',
    )

    # Perl 6 has a *lot* of possible bracketing characters
    # this list was lifted from STD.pm6 (https://github.com/perl6/std)
    PERL6_BRACKETS = {
        u'\u0028': u'\u0029', u'\u003c': u'\u003e', u'\u005b': u'\u005d',
        u'\u007b': u'\u007d', u'\u00ab': u'\u00bb', u'\u0f3a': u'\u0f3b',
        u'\u0f3c': u'\u0f3d', u'\u169b': u'\u169c', u'\u2018': u'\u2019',
        u'\u201a': u'\u2019', u'\u201b': u'\u2019', u'\u201c': u'\u201d',
        u'\u201e': u'\u201d', u'\u201f': u'\u201d', u'\u2039': u'\u203a',
        u'\u2045': u'\u2046', u'\u207d': u'\u207e', u'\u208d': u'\u208e',
        u'\u2208': u'\u220b', u'\u2209': u'\u220c', u'\u220a': u'\u220d',
        u'\u2215': u'\u29f5', u'\u223c': u'\u223d', u'\u2243': u'\u22cd',
        u'\u2252': u'\u2253', u'\u2254': u'\u2255', u'\u2264': u'\u2265',
        u'\u2266': u'\u2267', u'\u2268': u'\u2269', u'\u226a': u'\u226b',
        u'\u226e': u'\u226f', u'\u2270': u'\u2271', u'\u2272': u'\u2273',
        u'\u2274': u'\u2275', u'\u2276': u'\u2277', u'\u2278': u'\u2279',
        u'\u227a': u'\u227b', u'\u227c': u'\u227d', u'\u227e': u'\u227f',
        u'\u2280': u'\u2281', u'\u2282': u'\u2283', u'\u2284': u'\u2285',
        u'\u2286': u'\u2287', u'\u2288': u'\u2289', u'\u228a': u'\u228b',
        u'\u228f': u'\u2290', u'\u2291': u'\u2292', u'\u2298': u'\u29b8',
        u'\u22a2': u'\u22a3', u'\u22a6': u'\u2ade', u'\u22a8': u'\u2ae4',
        u'\u22a9': u'\u2ae3', u'\u22ab': u'\u2ae5', u'\u22b0': u'\u22b1',
        u'\u22b2': u'\u22b3', u'\u22b4': u'\u22b5', u'\u22b6': u'\u22b7',
        u'\u22c9': u'\u22ca', u'\u22cb': u'\u22cc', u'\u22d0': u'\u22d1',
        u'\u22d6': u'\u22d7', u'\u22d8': u'\u22d9', u'\u22da': u'\u22db',
        u'\u22dc': u'\u22dd', u'\u22de': u'\u22df', u'\u22e0': u'\u22e1',
        u'\u22e2': u'\u22e3', u'\u22e4': u'\u22e5', u'\u22e6': u'\u22e7',
        u'\u22e8': u'\u22e9', u'\u22ea': u'\u22eb', u'\u22ec': u'\u22ed',
        u'\u22f0': u'\u22f1', u'\u22f2': u'\u22fa', u'\u22f3': u'\u22fb',
        u'\u22f4': u'\u22fc', u'\u22f6': u'\u22fd', u'\u22f7': u'\u22fe',
        u'\u2308': u'\u2309', u'\u230a': u'\u230b', u'\u2329': u'\u232a',
        u'\u23b4': u'\u23b5', u'\u2768': u'\u2769', u'\u276a': u'\u276b',
        u'\u276c': u'\u276d', u'\u276e': u'\u276f', u'\u2770': u'\u2771',
        u'\u2772': u'\u2773', u'\u2774': u'\u2775', u'\u27c3': u'\u27c4',
        u'\u27c5': u'\u27c6', u'\u27d5': u'\u27d6', u'\u27dd': u'\u27de',
        u'\u27e2': u'\u27e3', u'\u27e4': u'\u27e5', u'\u27e6': u'\u27e7',
        u'\u27e8': u'\u27e9', u'\u27ea': u'\u27eb', u'\u2983': u'\u2984',
        u'\u2985': u'\u2986', u'\u2987': u'\u2988', u'\u2989': u'\u298a',
        u'\u298b': u'\u298c', u'\u298d': u'\u298e', u'\u298f': u'\u2990',
        u'\u2991': u'\u2992', u'\u2993': u'\u2994', u'\u2995': u'\u2996',
        u'\u2997': u'\u2998', u'\u29c0': u'\u29c1', u'\u29c4': u'\u29c5',
        u'\u29cf': u'\u29d0', u'\u29d1': u'\u29d2', u'\u29d4': u'\u29d5',
        u'\u29d8': u'\u29d9', u'\u29da': u'\u29db', u'\u29f8': u'\u29f9',
        u'\u29fc': u'\u29fd', u'\u2a2b': u'\u2a2c', u'\u2a2d': u'\u2a2e',
        u'\u2a34': u'\u2a35', u'\u2a3c': u'\u2a3d', u'\u2a64': u'\u2a65',
        u'\u2a79': u'\u2a7a', u'\u2a7d': u'\u2a7e', u'\u2a7f': u'\u2a80',
        u'\u2a81': u'\u2a82', u'\u2a83': u'\u2a84', u'\u2a8b': u'\u2a8c',
        u'\u2a91': u'\u2a92', u'\u2a93': u'\u2a94', u'\u2a95': u'\u2a96',
        u'\u2a97': u'\u2a98', u'\u2a99': u'\u2a9a', u'\u2a9b': u'\u2a9c',
        u'\u2aa1': u'\u2aa2', u'\u2aa6': u'\u2aa7', u'\u2aa8': u'\u2aa9',
        u'\u2aaa': u'\u2aab', u'\u2aac': u'\u2aad', u'\u2aaf': u'\u2ab0',
        u'\u2ab3': u'\u2ab4', u'\u2abb': u'\u2abc', u'\u2abd': u'\u2abe',
        u'\u2abf': u'\u2ac0', u'\u2ac1': u'\u2ac2', u'\u2ac3': u'\u2ac4',
        u'\u2ac5': u'\u2ac6', u'\u2acd': u'\u2ace', u'\u2acf': u'\u2ad0',
        u'\u2ad1': u'\u2ad2', u'\u2ad3': u'\u2ad4', u'\u2ad5': u'\u2ad6',
        u'\u2aec': u'\u2aed', u'\u2af7': u'\u2af8', u'\u2af9': u'\u2afa',
        u'\u2e02': u'\u2e03', u'\u2e04': u'\u2e05', u'\u2e09': u'\u2e0a',
        u'\u2e0c': u'\u2e0d', u'\u2e1c': u'\u2e1d', u'\u2e20': u'\u2e21',
        u'\u3008': u'\u3009', u'\u300a': u'\u300b', u'\u300c': u'\u300d',
        u'\u300e': u'\u300f', u'\u3010': u'\u3011', u'\u3014': u'\u3015',
        u'\u3016': u'\u3017', u'\u3018': u'\u3019', u'\u301a': u'\u301b',
        u'\u301d': u'\u301e', u'\ufd3e': u'\ufd3f', u'\ufe17': u'\ufe18',
        u'\ufe35': u'\ufe36', u'\ufe37': u'\ufe38', u'\ufe39': u'\ufe3a',
        u'\ufe3b': u'\ufe3c', u'\ufe3d': u'\ufe3e', u'\ufe3f': u'\ufe40',
        u'\ufe41': u'\ufe42', u'\ufe43': u'\ufe44', u'\ufe47': u'\ufe48',
        u'\ufe59': u'\ufe5a', u'\ufe5b': u'\ufe5c', u'\ufe5d': u'\ufe5e',
        u'\uff08': u'\uff09', u'\uff1c': u'\uff1e', u'\uff3b': u'\uff3d',
        u'\uff5b': u'\uff5d', u'\uff5f': u'\uff60', u'\uff62': u'\uff63',
    }

    def _build_word_match(words, boundary_regex_fragment=None, prefix='', suffix=''):
        if boundary_regex_fragment is None:
            return r'\b(' + prefix + r'|'.join(re.escape(x) for x in words) + \
                suffix + r')\b'
        else:
            return r'(?<!' + boundary_regex_fragment + r')' + prefix + r'(' + \
                r'|'.join(re.escape(x) for x in words) + r')' + suffix + r'(?!' + \
                boundary_regex_fragment + r')'

    def brackets_callback(token_class):
        def callback(lexer, match, context):
            groups = match.groupdict()
            opening_chars = groups['delimiter']
            n_chars = len(opening_chars)
            adverbs = groups.get('adverbs')

            closer = Perl6Lexer.PERL6_BRACKETS.get(opening_chars[0])
            text = context.text

            if closer is None:  # it's not a mirrored character, which means we
                                # just need to look for the next occurrence

                end_pos = text.find(opening_chars, match.start('delimiter') + n_chars)
            else:   # we need to look for the corresponding closing character,
                    # keep nesting in mind
                closing_chars = closer * n_chars
                nesting_level = 1

                search_pos = match.start('delimiter')

                while nesting_level > 0:
                    next_open_pos = text.find(opening_chars, search_pos + n_chars)
                    next_close_pos = text.find(closing_chars, search_pos + n_chars)

                    if next_close_pos == -1:
                        next_close_pos = len(text)
                        nesting_level = 0
                    elif next_open_pos != -1 and next_open_pos < next_close_pos:
                        nesting_level += 1
                        search_pos = next_open_pos
                    else:  # next_close_pos < next_open_pos
                        nesting_level -= 1
                        search_pos = next_close_pos

                end_pos = next_close_pos

            if end_pos < 0:     # if we didn't find a closer, just highlight the
                                # rest of the text in this class
                end_pos = len(text)

            if adverbs is not None and re.search(r':to\b', adverbs):
                heredoc_terminator = text[match.start('delimiter') + n_chars:end_pos]
                end_heredoc = re.search(r'^\s*' + re.escape(heredoc_terminator) +
                                        r'\s*$', text[end_pos:], re.MULTILINE)

                if end_heredoc:
                    end_pos += end_heredoc.end()
                else:
                    end_pos = len(text)

            yield match.start(), token_class, text[match.start():end_pos + n_chars]
            context.pos = end_pos + n_chars

        return callback

    def opening_brace_callback(lexer, match, context):
        stack = context.stack

        yield match.start(), Text, context.text[match.start():match.end()]
        context.pos = match.end()

        # if we encounter an opening brace and we're one level
        # below a token state, it means we need to increment
        # the nesting level for braces so we know later when
        # we should return to the token rules.
        if len(stack) > 2 and stack[-2] == 'token':
            context.perl6_token_nesting_level += 1

    def closing_brace_callback(lexer, match, context):
        stack = context.stack

        yield match.start(), Text, context.text[match.start():match.end()]
        context.pos = match.end()

        # if we encounter a free closing brace and we're one level
        # below a token state, it means we need to check the nesting
        # level to see if we need to return to the token state.
        if len(stack) > 2 and stack[-2] == 'token':
            context.perl6_token_nesting_level -= 1
            if context.perl6_token_nesting_level == 0:
                stack.pop()

    def embedded_perl6_callback(lexer, match, context):
        context.perl6_token_nesting_level = 1
        yield match.start(), Text, context.text[match.start():match.end()]
        context.pos = match.end()
        context.stack.append('root')

    # If you're modifying these rules, be careful if you need to process '{' or '}'
    # characters. We have special logic for processing these characters (due to the fact
    # that you can nest Perl 6 code in regex blocks), so if you need to process one of
    # them, make sure you also process the corresponding one!
    tokens = {
        'common': [
            (r'#[`|=](?P<delimiter>(?P<first_char>[' + ''.join(PERL6_BRACKETS) + r'])(?P=first_char)*)',
             brackets_callback(Comment.Multiline)),
            (r'#[^\n]*$', Comment.Single),
            (r'^(\s*)=begin\s+(\w+)\b.*?^\1=end\s+\2', Comment.Multiline),
            (r'^(\s*)=for.*?\n\s*?\n', Comment.Multiline),
            (r'^=.*?\n\s*?\n', Comment.Multiline),
            (r'(regex|token|rule)(\s*' + PERL6_IDENTIFIER_RANGE + '+:sym)',
             bygroups(Keyword, Name), 'token-sym-brackets'),
            (r'(regex|token|rule)(?!' + PERL6_IDENTIFIER_RANGE + r')(\s*' + PERL6_IDENTIFIER_RANGE + '+)?',
             bygroups(Keyword, Name), 'pre-token'),
            # deal with a special case in the Perl 6 grammar (role q { ... })
            (r'(role)(\s+)(q)(\s*)', bygroups(Keyword, Text, Name, Text)),
            (_build_word_match(PERL6_KEYWORDS, PERL6_IDENTIFIER_RANGE), Keyword),
            (_build_word_match(PERL6_BUILTIN_CLASSES, PERL6_IDENTIFIER_RANGE, suffix='(?::[UD])?'),
             Name.Builtin),
            (_build_word_match(PERL6_BUILTINS, PERL6_IDENTIFIER_RANGE), Name.Builtin),
            # copied from PerlLexer
            (r'[$@%&][.^:?=!~]?' + PERL6_IDENTIFIER_RANGE + u'+(?:<<.*?>>|<.*?>|«.*?»)*',
             Name.Variable),
            (r'\$[!/](?:<<.*?>>|<.*?>|«.*?»)*', Name.Variable.Global),
            (r'::\?\w+', Name.Variable.Global),
            (r'[$@%&]\*' + PERL6_IDENTIFIER_RANGE + u'+(?:<<.*?>>|<.*?>|«.*?»)*',
             Name.Variable.Global),
            (r'\$(?:<.*?>)+', Name.Variable),
            (r'(?:q|qq|Q)[a-zA-Z]?\s*(?P<adverbs>:[\w\s:]+)?\s*(?P<delimiter>(?P<first_char>[^0-9a-zA-Z:\s])'
             r'(?P=first_char)*)', brackets_callback(String)),
            # copied from PerlLexer
            (r'0_?[0-7]+(_[0-7]+)*', Number.Oct),
            (r'0x[0-9A-Fa-f]+(_[0-9A-Fa-f]+)*', Number.Hex),
            (r'0b[01]+(_[01]+)*', Number.Bin),
            (r'(?i)(\d*(_\d*)*\.\d+(_\d*)*|\d+(_\d*)*\.\d+(_\d*)*)(e[+-]?\d+)?',
             Number.Float),
            (r'(?i)\d+(_\d*)*e[+-]?\d+(_\d*)*', Number.Float),
            (r'\d+(_\d+)*', Number.Integer),
            (r'(?<=~~)\s*/(?:\\\\|\\/|.)*?/', String.Regex),
            (r'(?<=[=(,])\s*/(?:\\\\|\\/|.)*?/', String.Regex),
            (r'm\w+(?=\()', Name),
            (r'(?:m|ms|rx)\s*(?P<adverbs>:[\w\s:]+)?\s*(?P<delimiter>(?P<first_char>[^\w:\s])'
             r'(?P=first_char)*)', brackets_callback(String.Regex)),
            (r'(?:s|ss|tr)\s*(?::[\w\s:]+)?\s*/(?:\\\\|\\/|.)*?/(?:\\\\|\\/|.)*?/',
             String.Regex),
            (r'<[^\s=].*?\S>', String),
            (_build_word_match(PERL6_OPERATORS), Operator),
            (r'\w' + PERL6_IDENTIFIER_RANGE + '*', Name),
            (r"'(\\\\|\\[^\\]|[^'\\])*'", String),
            (r'"(\\\\|\\[^\\]|[^"\\])*"', String),
        ],
        'root': [
            include('common'),
            (r'\{', opening_brace_callback),
            (r'\}', closing_brace_callback),
            (r'.+?', Text),
        ],
        'pre-token': [
            include('common'),
            (r'\{', Text, ('#pop', 'token')),
            (r'.+?', Text),
        ],
        'token-sym-brackets': [
            (r'(?P<delimiter>(?P<first_char>[' + ''.join(PERL6_BRACKETS) + '])(?P=first_char)*)',
             brackets_callback(Name), ('#pop', 'pre-token')),
            default(('#pop', 'pre-token')),
        ],
        'token': [
            (r'\}', Text, '#pop'),
            (r'(?<=:)(?:my|our|state|constant|temp|let).*?;', using(this)),
            # make sure that quotes in character classes aren't treated as strings
            (r'<(?:[-!?+.]\s*)?\[.*?\]>', String.Regex),
            # make sure that '#' characters in quotes aren't treated as comments
            (r"(?<!\\)'(\\\\|\\[^\\]|[^'\\])*'", String.Regex),
            (r'(?<!\\)"(\\\\|\\[^\\]|[^"\\])*"', String.Regex),
            (r'#.*?$', Comment.Single),
            (r'\{', embedded_perl6_callback),
            ('.+?', String.Regex),
        ],
    }

    def analyse_text(text):
        def strip_pod(lines):
            in_pod = False
            stripped_lines = []

            for line in lines:
                if re.match(r'^=(?:end|cut)', line):
                    in_pod = False
                elif re.match(r'^=\w+', line):
                    in_pod = True
                elif not in_pod:
                    stripped_lines.append(line)

            return stripped_lines

        # XXX handle block comments
        lines = text.splitlines()
        lines = strip_pod(lines)
        text = '\n'.join(lines)

        if shebang_matches(text, r'perl6|rakudo|niecza|pugs'):
            return True

        saw_perl_decl = False
        rating = False

        # check for my/our/has declarations
        if re.search(r"(?:my|our|has)\s+(?:" + Perl6Lexer.PERL6_IDENTIFIER_RANGE +
                     r"+\s+)?[$@%&(]", text):
            rating = 0.8
            saw_perl_decl = True

        for line in lines:
            line = re.sub('#.*', '', line)
            if re.match(r'^\s*$', line):
                continue

            # match v6; use v6; use v6.0; use v6.0.0;
            if re.match(r'^\s*(?:use\s+)?v6(?:\.\d(?:\.\d)?)?;', line):
                return True
            # match class, module, role, enum, grammar declarations
            class_decl = re.match(r'^\s*(?:(?P<scope>my|our)\s+)?(?:module|class|role|enum|grammar)', line)
            if class_decl:
                if saw_perl_decl or class_decl.group('scope') is not None:
                    return True
                rating = 0.05
                continue
            break

        return rating

    def __init__(self, **options):
        super(Perl6Lexer, self).__init__(**options)
        self.encoding = options.get('encoding', 'utf-8')
