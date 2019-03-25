# -*- coding: utf-8 -*-
"""
    pygments.lexers.esoteric
    ~~~~~~~~~~~~~~~~~~~~~~~~

    Lexers for esoteric languages.

    :copyright: Copyright 2006-2017 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from pygments.lexer import RegexLexer, include, words
from pygments.token import Text, Comment, Operator, Keyword, Name, String, \
    Number, Punctuation, Error

__all__ = ['BrainfuckLexer', 'BefungeLexer', 'RedcodeLexer', 'CAmkESLexer',
           'CapDLLexer', 'AheuiLexer']


class BrainfuckLexer(RegexLexer):
    """
    Lexer for the esoteric `BrainFuck <http://www.muppetlabs.com/~breadbox/bf/>`_
    language.
    """

    name = 'Brainfuck'
    aliases = ['brainfuck', 'bf']
    filenames = ['*.bf', '*.b']
    mimetypes = ['application/x-brainfuck']

    tokens = {
        'common': [
            # use different colors for different instruction types
            (r'[.,]+', Name.Tag),
            (r'[+-]+', Name.Builtin),
            (r'[<>]+', Name.Variable),
            (r'[^.,+\-<>\[\]]+', Comment),
        ],
        'root': [
            (r'\[', Keyword, 'loop'),
            (r'\]', Error),
            include('common'),
        ],
        'loop': [
            (r'\[', Keyword, '#push'),
            (r'\]', Keyword, '#pop'),
            include('common'),
        ]
    }


class BefungeLexer(RegexLexer):
    """
    Lexer for the esoteric `Befunge <http://en.wikipedia.org/wiki/Befunge>`_
    language.

    .. versionadded:: 0.7
    """
    name = 'Befunge'
    aliases = ['befunge']
    filenames = ['*.befunge']
    mimetypes = ['application/x-befunge']

    tokens = {
        'root': [
            (r'[0-9a-f]', Number),
            (r'[+*/%!`-]', Operator),             # Traditional math
            (r'[<>^v?\[\]rxjk]', Name.Variable),  # Move, imperatives
            (r'[:\\$.,n]', Name.Builtin),         # Stack ops, imperatives
            (r'[|_mw]', Keyword),
            (r'[{}]', Name.Tag),                  # Befunge-98 stack ops
            (r'".*?"', String.Double),            # Strings don't appear to allow escapes
            (r'\'.', String.Single),              # Single character
            (r'[#;]', Comment),                   # Trampoline... depends on direction hit
            (r'[pg&~=@iotsy]', Keyword),          # Misc
            (r'[()A-Z]', Comment),                # Fingerprints
            (r'\s+', Text),                       # Whitespace doesn't matter
        ],
    }


class CAmkESLexer(RegexLexer):
    """
    Basic lexer for the input language for the
    `CAmkES <https://sel4.systems/CAmkES/>`_ component platform.

    .. versionadded:: 2.1
    """
    name = 'CAmkES'
    aliases = ['camkes', 'idl4']
    filenames = ['*.camkes', '*.idl4']

    tokens = {
        'root': [
            # C pre-processor directive
            (r'^\s*#.*\n', Comment.Preproc),

            # Whitespace, comments
            (r'\s+', Text),
            (r'/\*(.|\n)*?\*/', Comment),
            (r'//.*\n', Comment),

            (r'[\[(){},.;\]]', Punctuation),
            (r'[~!%^&*+=|?:<>/-]', Operator),

            (words(('assembly', 'attribute', 'component', 'composition',
                    'configuration', 'connection', 'connector', 'consumes',
                    'control', 'dataport', 'Dataport', 'Dataports', 'emits',
                    'event', 'Event', 'Events', 'export', 'from', 'group',
                    'hardware', 'has', 'interface', 'Interface', 'maybe',
                    'procedure', 'Procedure', 'Procedures', 'provides',
                    'template', 'thread', 'threads', 'to', 'uses', 'with'),
                   suffix=r'\b'), Keyword),

            (words(('bool', 'boolean', 'Buf', 'char', 'character', 'double',
                    'float', 'in', 'inout', 'int', 'int16_6', 'int32_t',
                    'int64_t', 'int8_t', 'integer', 'mutex', 'out', 'real',
                    'refin', 'semaphore', 'signed', 'string', 'struct',
                    'uint16_t', 'uint32_t', 'uint64_t', 'uint8_t', 'uintptr_t',
                    'unsigned', 'void'),
                   suffix=r'\b'), Keyword.Type),

            # Recognised attributes
            (r'[a-zA-Z_]\w*_(priority|domain|buffer)', Keyword.Reserved),
            (words(('dma_pool', 'from_access', 'to_access'), suffix=r'\b'),
                Keyword.Reserved),

            # CAmkES-level include
            (r'import\s+(<[^>]*>|"[^"]*");', Comment.Preproc),

            # C-level include
            (r'include\s+(<[^>]*>|"[^"]*");', Comment.Preproc),

            # Literals
            (r'0[xX][\da-fA-F]+', Number.Hex),
            (r'-?[\d]+', Number),
            (r'-?[\d]+\.[\d]+', Number.Float),
            (r'"[^"]*"', String),
            (r'[Tt]rue|[Ff]alse', Name.Builtin),

            # Identifiers
            (r'[a-zA-Z_]\w*', Name),
        ],
    }


class CapDLLexer(RegexLexer):
    """
    Basic lexer for
    `CapDL <https://ssrg.nicta.com.au/publications/nictaabstracts/Kuz_KLW_10.abstract.pml>`_.

    The source of the primary tool that reads such specifications is available
    at https://github.com/seL4/capdl/tree/master/capDL-tool. Note that this
    lexer only supports a subset of the grammar. For example, identifiers can
    shadow type names, but these instances are currently incorrectly
    highlighted as types. Supporting this would need a stateful lexer that is
    considered unnecessarily complex for now.

    .. versionadded:: 2.2
    """
    name = 'CapDL'
    aliases = ['capdl']
    filenames = ['*.cdl']

    tokens = {
        'root': [
            # C pre-processor directive
            (r'^\s*#.*\n', Comment.Preproc),

            # Whitespace, comments
            (r'\s+', Text),
            (r'/\*(.|\n)*?\*/', Comment),
            (r'(//|--).*\n', Comment),

            (r'[<>\[(){},:;=\]]', Punctuation),
            (r'\.\.', Punctuation),

            (words(('arch', 'arm11', 'caps', 'child_of', 'ia32', 'irq', 'maps',
                    'objects'), suffix=r'\b'), Keyword),

            (words(('aep', 'asid_pool', 'cnode', 'ep', 'frame', 'io_device',
                    'io_ports', 'io_pt', 'notification', 'pd', 'pt', 'tcb',
                    'ut', 'vcpu'), suffix=r'\b'), Keyword.Type),

            # Properties
            (words(('asid', 'addr', 'badge', 'cached', 'dom', 'domainID', 'elf',
                    'fault_ep', 'G', 'guard', 'guard_size', 'init', 'ip',
                    'prio', 'sp', 'R', 'RG', 'RX', 'RW', 'RWG', 'RWX', 'W',
                    'WG', 'WX', 'level', 'masked', 'master_reply', 'paddr',
                    'ports', 'reply', 'uncached'), suffix=r'\b'),
             Keyword.Reserved),

            # Literals
            (r'0[xX][\da-fA-F]+', Number.Hex),
            (r'\d+(\.\d+)?(k|M)?', Number),
            (words(('bits',), suffix=r'\b'), Number),
            (words(('cspace', 'vspace', 'reply_slot', 'caller_slot',
                    'ipc_buffer_slot'), suffix=r'\b'), Number),

            # Identifiers
            (r'[a-zA-Z_][-@\.\w]*', Name),
        ],
    }


class RedcodeLexer(RegexLexer):
    """
    A simple Redcode lexer based on ICWS'94.
    Contributed by Adam Blinkinsop <blinks@acm.org>.

    .. versionadded:: 0.8
    """
    name = 'Redcode'
    aliases = ['redcode']
    filenames = ['*.cw']

    opcodes = ('DAT', 'MOV', 'ADD', 'SUB', 'MUL', 'DIV', 'MOD',
               'JMP', 'JMZ', 'JMN', 'DJN', 'CMP', 'SLT', 'SPL',
               'ORG', 'EQU', 'END')
    modifiers = ('A', 'B', 'AB', 'BA', 'F', 'X', 'I')

    tokens = {
        'root': [
            # Whitespace:
            (r'\s+', Text),
            (r';.*$', Comment.Single),
            # Lexemes:
            #  Identifiers
            (r'\b(%s)\b' % '|'.join(opcodes), Name.Function),
            (r'\b(%s)\b' % '|'.join(modifiers), Name.Decorator),
            (r'[A-Za-z_]\w+', Name),
            #  Operators
            (r'[-+*/%]', Operator),
            (r'[#$@<>]', Operator),  # mode
            (r'[.,]', Punctuation),  # mode
            #  Numbers
            (r'[-+]?\d+', Number.Integer),
        ],
    }


class AheuiLexer(RegexLexer):
    """
    Aheui_ Lexer.

    Aheui_ is esoteric language based on Korean alphabets.

    .. _Aheui:: http://aheui.github.io/

    """

    name = 'Aheui'
    aliases = ['aheui']
    filenames = ['*.aheui']

    tokens = {
        'root': [
            (u'['
             u'나-낳냐-냫너-넣녀-녛노-놓뇨-눟뉴-닇'
             u'다-닿댜-댷더-덯뎌-뎧도-돟됴-둫듀-딓'
             u'따-땋땨-떃떠-떻뗘-뗳또-똫뚀-뚷뜌-띟'
             u'라-랗랴-럏러-렇려-렿로-롷료-뤃류-릫'
             u'마-맣먀-먛머-멓며-몋모-뫃묘-뭏뮤-믷'
             u'바-밯뱌-뱧버-벟벼-볗보-봏뵤-붛뷰-빃'
             u'빠-빻뺘-뺳뻐-뻫뼈-뼣뽀-뽛뾰-뿧쀼-삏'
             u'사-샇샤-샿서-섷셔-셯소-솧쇼-숳슈-싛'
             u'싸-쌓쌰-썋써-쎃쎠-쎻쏘-쏳쑈-쑿쓔-씧'
             u'자-잫쟈-쟣저-젛져-졓조-좋죠-줗쥬-즿'
             u'차-챃챠-챻처-첳쳐-쳫초-촣쵸-춯츄-칗'
             u'카-캏캬-컇커-컿켜-켷코-콯쿄-쿻큐-킣'
             u'타-탛탸-턓터-텋텨-톃토-톻툐-퉇튜-틯'
             u'파-팧퍄-퍟퍼-펗펴-폏포-퐇표-풓퓨-픻'
             u'하-핳햐-햫허-헣혀-혛호-홓효-훟휴-힇'
             u']', Operator),
            ('.', Comment),
        ],
    }
