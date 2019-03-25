# -*- coding: utf-8 -*-
"""
    pygments.lexers.c_cpp
    ~~~~~~~~~~~~~~~~~~~~~

    Lexers for C/C++ languages.

    :copyright: Copyright 2006-2017 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from pygments.lexer import RegexLexer, include, bygroups, using, \
    this, inherit, default, words
from pygments.util import get_bool_opt
from pygments.token import Text, Comment, Operator, Keyword, Name, String, \
    Number, Punctuation, Error

__all__ = ['CLexer', 'CppLexer']


class CFamilyLexer(RegexLexer):
    """
    For C family source code.  This is used as a base class to avoid repetitious
    definitions.
    """

    #: optional Comment or Whitespace
    _ws = r'(?:\s|//.*?\n|/[*].*?[*]/)+'

    # The trailing ?, rather than *, avoids a geometric performance drop here.
    #: only one /* */ style comment
    _ws1 = r'\s*(?:/[*].*?[*]/\s*)?'

    tokens = {
        'whitespace': [
            # preprocessor directives: without whitespace
            (r'^#if\s+0', Comment.Preproc, 'if0'),
            ('^#', Comment.Preproc, 'macro'),
            # or with whitespace
            ('^(' + _ws1 + r')(#if\s+0)',
             bygroups(using(this), Comment.Preproc), 'if0'),
            ('^(' + _ws1 + ')(#)',
             bygroups(using(this), Comment.Preproc), 'macro'),
            (r'\n', Text),
            (r'\s+', Text),
            (r'\\\n', Text),  # line continuation
            (r'//(\n|[\w\W]*?[^\\]\n)', Comment.Single),
            (r'/(\\\n)?[*][\w\W]*?[*](\\\n)?/', Comment.Multiline),
            # Open until EOF, so no ending delimeter
            (r'/(\\\n)?[*][\w\W]*', Comment.Multiline),
        ],
        'statements': [
            (r'(L?)(")', bygroups(String.Affix, String), 'string'),
            (r"(L?)(')(\\.|\\[0-7]{1,3}|\\x[a-fA-F0-9]{1,2}|[^\\\'\n])(')",
             bygroups(String.Affix, String.Char, String.Char, String.Char)),
            (r'(\d+\.\d*|\.\d+|\d+)[eE][+-]?\d+[LlUu]*', Number.Float),
            (r'(\d+\.\d*|\.\d+|\d+[fF])[fF]?', Number.Float),
            (r'0x[0-9a-fA-F]+[LlUu]*', Number.Hex),
            (r'0[0-7]+[LlUu]*', Number.Oct),
            (r'\d+[LlUu]*', Number.Integer),
            (r'\*/', Error),
            (r'[~!%^&*+=|?:<>/-]', Operator),
            (r'[()\[\],.]', Punctuation),
            (words(('asm', 'auto', 'break', 'case', 'const', 'continue',
                    'default', 'do', 'else', 'enum', 'extern', 'for', 'goto',
                    'if', 'register', 'restricted', 'return', 'sizeof',
                    'static', 'struct', 'switch', 'typedef', 'union',
                    'volatile', 'while'),
                   suffix=r'\b'), Keyword),
            (r'(bool|int|long|float|short|double|char|unsigned|signed|void)\b',
             Keyword.Type),
            (words(('inline', '_inline', '__inline', 'naked', 'restrict',
                    'thread', 'typename'), suffix=r'\b'), Keyword.Reserved),
            # Vector intrinsics
            (r'(__m(128i|128d|128|64))\b', Keyword.Reserved),
            # Microsoft-isms
            (words((
                'asm', 'int8', 'based', 'except', 'int16', 'stdcall', 'cdecl',
                'fastcall', 'int32', 'declspec', 'finally', 'int64', 'try',
                'leave', 'wchar_t', 'w64', 'unaligned', 'raise', 'noop',
                'identifier', 'forceinline', 'assume'),
                prefix=r'__', suffix=r'\b'), Keyword.Reserved),
            (r'(true|false|NULL)\b', Name.Builtin),
            (r'([a-zA-Z_]\w*)(\s*)(:)(?!:)', bygroups(Name.Label, Text, Punctuation)),
            (r'[a-zA-Z_]\w*', Name),
        ],
        'root': [
            include('whitespace'),
            # functions
            (r'((?:[\w*\s])+?(?:\s|[*]))'  # return arguments
             r'([a-zA-Z_]\w*)'             # method name
             r'(\s*\([^;]*?\))'            # signature
             r'([^;{]*)(\{)',
             bygroups(using(this), Name.Function, using(this), using(this),
                      Punctuation),
             'function'),
            # function declarations
            (r'((?:[\w*\s])+?(?:\s|[*]))'  # return arguments
             r'([a-zA-Z_]\w*)'             # method name
             r'(\s*\([^;]*?\))'            # signature
             r'([^;]*)(;)',
             bygroups(using(this), Name.Function, using(this), using(this),
                      Punctuation)),
            default('statement'),
        ],
        'statement': [
            include('whitespace'),
            include('statements'),
            ('[{}]', Punctuation),
            (';', Punctuation, '#pop'),
        ],
        'function': [
            include('whitespace'),
            include('statements'),
            (';', Punctuation),
            (r'\{', Punctuation, '#push'),
            (r'\}', Punctuation, '#pop'),
        ],
        'string': [
            (r'"', String, '#pop'),
            (r'\\([\\abfnrtv"\']|x[a-fA-F0-9]{2,4}|'
             r'u[a-fA-F0-9]{4}|U[a-fA-F0-9]{8}|[0-7]{1,3})', String.Escape),
            (r'[^\\"\n]+', String),  # all other characters
            (r'\\\n', String),  # line continuation
            (r'\\', String),  # stray backslash
        ],
        'macro': [
            (r'(include)(' + _ws1 + r')([^\n]+)',
             bygroups(Comment.Preproc, Text, Comment.PreprocFile)),
            (r'[^/\n]+', Comment.Preproc),
            (r'/[*](.|\n)*?[*]/', Comment.Multiline),
            (r'//.*?\n', Comment.Single, '#pop'),
            (r'/', Comment.Preproc),
            (r'(?<=\\)\n', Comment.Preproc),
            (r'\n', Comment.Preproc, '#pop'),
        ],
        'if0': [
            (r'^\s*#if.*?(?<!\\)\n', Comment.Preproc, '#push'),
            (r'^\s*#el(?:se|if).*\n', Comment.Preproc, '#pop'),
            (r'^\s*#endif.*?(?<!\\)\n', Comment.Preproc, '#pop'),
            (r'.*?\n', Comment),
        ]
    }

    stdlib_types = set((
        'size_t', 'ssize_t', 'off_t', 'wchar_t', 'ptrdiff_t', 'sig_atomic_t', 'fpos_t',
        'clock_t', 'time_t', 'va_list', 'jmp_buf', 'FILE', 'DIR', 'div_t', 'ldiv_t',
        'mbstate_t', 'wctrans_t', 'wint_t', 'wctype_t'))
    c99_types = set((
        '_Bool', '_Complex', 'int8_t', 'int16_t', 'int32_t', 'int64_t', 'uint8_t',
        'uint16_t', 'uint32_t', 'uint64_t', 'int_least8_t', 'int_least16_t',
        'int_least32_t', 'int_least64_t', 'uint_least8_t', 'uint_least16_t',
        'uint_least32_t', 'uint_least64_t', 'int_fast8_t', 'int_fast16_t', 'int_fast32_t',
        'int_fast64_t', 'uint_fast8_t', 'uint_fast16_t', 'uint_fast32_t', 'uint_fast64_t',
        'intptr_t', 'uintptr_t', 'intmax_t', 'uintmax_t'))
    linux_types = set((
        'clockid_t', 'cpu_set_t', 'cpumask_t', 'dev_t', 'gid_t', 'id_t', 'ino_t', 'key_t',
        'mode_t', 'nfds_t', 'pid_t', 'rlim_t', 'sig_t', 'sighandler_t', 'siginfo_t',
        'sigset_t', 'sigval_t', 'socklen_t', 'timer_t', 'uid_t'))

    def __init__(self, **options):
        self.stdlibhighlighting = get_bool_opt(options, 'stdlibhighlighting', True)
        self.c99highlighting = get_bool_opt(options, 'c99highlighting', True)
        self.platformhighlighting = get_bool_opt(options, 'platformhighlighting', True)
        RegexLexer.__init__(self, **options)

    def get_tokens_unprocessed(self, text):
        for index, token, value in \
                RegexLexer.get_tokens_unprocessed(self, text):
            if token is Name:
                if self.stdlibhighlighting and value in self.stdlib_types:
                    token = Keyword.Type
                elif self.c99highlighting and value in self.c99_types:
                    token = Keyword.Type
                elif self.platformhighlighting and value in self.linux_types:
                    token = Keyword.Type
            yield index, token, value


class CLexer(CFamilyLexer):
    """
    For C source code with preprocessor directives.
    """
    name = 'C'
    aliases = ['c']
    filenames = ['*.c', '*.h', '*.idc']
    mimetypes = ['text/x-chdr', 'text/x-csrc']
    priority = 0.1

    def analyse_text(text):
        if re.search(r'^\s*#include [<"]', text, re.MULTILINE):
            return 0.1
        if re.search(r'^\s*#ifn?def ', text, re.MULTILINE):
            return 0.1


class CppLexer(CFamilyLexer):
    """
    For C++ source code with preprocessor directives.
    """
    name = 'C++'
    aliases = ['cpp', 'c++']
    filenames = ['*.cpp', '*.hpp', '*.c++', '*.h++',
                 '*.cc', '*.hh', '*.cxx', '*.hxx',
                 '*.C', '*.H', '*.cp', '*.CPP']
    mimetypes = ['text/x-c++hdr', 'text/x-c++src']
    priority = 0.1

    tokens = {
        'statements': [
            (words((
                'catch', 'const_cast', 'delete', 'dynamic_cast', 'explicit',
                'export', 'friend', 'mutable', 'namespace', 'new', 'operator',
                'private', 'protected', 'public', 'reinterpret_cast',
                'restrict', 'static_cast', 'template', 'this', 'throw', 'throws',
                'try', 'typeid', 'typename', 'using', 'virtual',
                'constexpr', 'nullptr', 'decltype', 'thread_local',
                'alignas', 'alignof', 'static_assert', 'noexcept', 'override',
                'final'), suffix=r'\b'), Keyword),
            (r'char(16_t|32_t)\b', Keyword.Type),
            (r'(class)(\s+)', bygroups(Keyword, Text), 'classname'),
            # C++11 raw strings
            (r'(R)(")([^\\()\s]{,16})(\()((?:.|\n)*?)(\)\3)(")',
             bygroups(String.Affix, String, String.Delimiter, String.Delimiter,
                      String, String.Delimiter, String)),
            # C++11 UTF-8/16/32 strings
            (r'(u8|u|U)(")', bygroups(String.Affix, String), 'string'),
            inherit,
        ],
        'root': [
            inherit,
            # C++ Microsoft-isms
            (words(('virtual_inheritance', 'uuidof', 'super', 'single_inheritance',
                    'multiple_inheritance', 'interface', 'event'),
                   prefix=r'__', suffix=r'\b'), Keyword.Reserved),
            # Offload C++ extensions, http://offload.codeplay.com/
            (r'__(offload|blockingoffload|outer)\b', Keyword.Pseudo),
        ],
        'classname': [
            (r'[a-zA-Z_]\w*', Name.Class, '#pop'),
            # template specification
            (r'\s*(?=>)', Text, '#pop'),
        ],
    }

    def analyse_text(text):
        if re.search('#include <[a-z_]+>', text):
            return 0.2
        if re.search('using namespace ', text):
            return 0.4
