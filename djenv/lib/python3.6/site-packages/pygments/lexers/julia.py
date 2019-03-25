# -*- coding: utf-8 -*-
"""
    pygments.lexers.julia
    ~~~~~~~~~~~~~~~~~~~~~

    Lexers for the Julia language.

    :copyright: Copyright 2006-2017 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from pygments.lexer import Lexer, RegexLexer, bygroups, do_insertions, \
    words, include
from pygments.token import Text, Comment, Operator, Keyword, Name, String, \
    Number, Punctuation, Generic
from pygments.util import shebang_matches, unirange

__all__ = ['JuliaLexer', 'JuliaConsoleLexer']

allowed_variable = (
    u'(?:[a-zA-Z_\u00A1-\uffff]|%s)(?:[a-zA-Z_0-9\u00A1-\uffff]|%s)*!*' %
    ((unirange(0x10000, 0x10ffff),) * 2))


class JuliaLexer(RegexLexer):
    """
    For `Julia <http://julialang.org/>`_ source code.

    .. versionadded:: 1.6
    """

    name = 'Julia'
    aliases = ['julia', 'jl']
    filenames = ['*.jl']
    mimetypes = ['text/x-julia', 'application/x-julia']

    flags = re.MULTILINE | re.UNICODE

    tokens = {
        'root': [
            (r'\n', Text),
            (r'[^\S\n]+', Text),
            (r'#=', Comment.Multiline, "blockcomment"),
            (r'#.*$', Comment),
            (r'[\[\]{}(),;]', Punctuation),

            # keywords
            (r'in\b', Keyword.Pseudo),
            (r'(true|false)\b', Keyword.Constant),
            (r'(local|global|const)\b', Keyword.Declaration),
            (words([
                'function', 'type', 'typealias', 'abstract', 'immutable',
                'baremodule', 'begin', 'bitstype', 'break', 'catch', 'ccall',
                'continue', 'do', 'else', 'elseif', 'end', 'export', 'finally',
                'for', 'if', 'import', 'importall', 'let', 'macro', 'module',
                'quote', 'return', 'try', 'using', 'while'],
                suffix=r'\b'), Keyword),

            # NOTE
            # Patterns below work only for definition sites and thus hardly reliable.
            #
            # functions
            # (r'(function)(\s+)(' + allowed_variable + ')',
            #  bygroups(Keyword, Text, Name.Function)),
            #
            # types
            # (r'(type|typealias|abstract|immutable)(\s+)(' + allowed_variable + ')',
            #  bygroups(Keyword, Text, Name.Class)),

            # type names
            (words([
                'ANY', 'ASCIIString', 'AbstractArray', 'AbstractChannel',
                'AbstractFloat', 'AbstractMatrix', 'AbstractRNG',
                'AbstractSparseArray', 'AbstractSparseMatrix',
                'AbstractSparseVector', 'AbstractString', 'AbstractVecOrMat',
                'AbstractVector', 'Any', 'ArgumentError', 'Array',
                'AssertionError', 'Associative', 'Base64DecodePipe',
                'Base64EncodePipe', 'Bidiagonal', 'BigFloat', 'BigInt',
                'BitArray', 'BitMatrix', 'BitVector', 'Bool', 'BoundsError',
                'Box', 'BufferStream', 'CapturedException', 'CartesianIndex',
                'CartesianRange', 'Cchar', 'Cdouble', 'Cfloat', 'Channel',
                'Char', 'Cint', 'Cintmax_t', 'Clong', 'Clonglong',
                'ClusterManager', 'Cmd', 'Coff_t', 'Colon', 'Complex',
                'Complex128', 'Complex32', 'Complex64', 'CompositeException',
                'Condition', 'Cptrdiff_t', 'Cshort', 'Csize_t', 'Cssize_t',
                'Cstring', 'Cuchar', 'Cuint', 'Cuintmax_t', 'Culong',
                'Culonglong', 'Cushort', 'Cwchar_t', 'Cwstring', 'DataType',
                'Date', 'DateTime', 'DenseArray', 'DenseMatrix',
                'DenseVecOrMat', 'DenseVector', 'Diagonal', 'Dict',
                'DimensionMismatch', 'Dims', 'DirectIndexString', 'Display',
                'DivideError', 'DomainError', 'EOFError', 'EachLine', 'Enum',
                'Enumerate', 'ErrorException', 'Exception', 'Expr',
                'Factorization', 'FileMonitor', 'FileOffset', 'Filter',
                'Float16', 'Float32', 'Float64', 'FloatRange', 'Function',
                'GenSym', 'GlobalRef', 'GotoNode', 'HTML', 'Hermitian', 'IO',
                'IOBuffer', 'IOStream', 'IPv4', 'IPv6', 'InexactError',
                'InitError', 'Int', 'Int128', 'Int16', 'Int32', 'Int64', 'Int8',
                'IntSet', 'Integer', 'InterruptException', 'IntrinsicFunction',
                'InvalidStateException', 'Irrational', 'KeyError', 'LabelNode',
                'LambdaStaticData', 'LinSpace', 'LineNumberNode', 'LoadError',
                'LocalProcess', 'LowerTriangular', 'MIME', 'Matrix',
                'MersenneTwister', 'Method', 'MethodError', 'MethodTable',
                'Module', 'NTuple', 'NewvarNode', 'NullException', 'Nullable',
                'Number', 'ObjectIdDict', 'OrdinalRange', 'OutOfMemoryError',
                'OverflowError', 'Pair', 'ParseError', 'PartialQuickSort',
                'Pipe', 'PollingFileWatcher', 'ProcessExitedException',
                'ProcessGroup', 'Ptr', 'QuoteNode', 'RandomDevice', 'Range',
                'Rational', 'RawFD', 'ReadOnlyMemoryError', 'Real',
                'ReentrantLock', 'Ref', 'Regex', 'RegexMatch',
                'RemoteException', 'RemoteRef', 'RepString', 'RevString',
                'RopeString', 'RoundingMode', 'SegmentationFault',
                'SerializationState', 'Set', 'SharedArray', 'SharedMatrix',
                'SharedVector', 'Signed', 'SimpleVector', 'SparseMatrixCSC',
                'StackOverflowError', 'StatStruct', 'StepRange', 'StridedArray',
                'StridedMatrix', 'StridedVecOrMat', 'StridedVector', 'SubArray',
                'SubString', 'SymTridiagonal', 'Symbol', 'SymbolNode',
                'Symmetric', 'SystemError', 'TCPSocket', 'Task', 'Text',
                'TextDisplay', 'Timer', 'TopNode', 'Tridiagonal', 'Tuple',
                'Type', 'TypeConstructor', 'TypeError', 'TypeName', 'TypeVar',
                'UDPSocket', 'UInt', 'UInt128', 'UInt16', 'UInt32', 'UInt64',
                'UInt8', 'UTF16String', 'UTF32String', 'UTF8String',
                'UndefRefError', 'UndefVarError', 'UnicodeError', 'UniformScaling',
                'Union', 'UnitRange', 'Unsigned', 'UpperTriangular', 'Val',
                'Vararg', 'VecOrMat', 'Vector', 'VersionNumber', 'Void', 'WString',
                'WeakKeyDict', 'WeakRef', 'WorkerConfig', 'Zip'], suffix=r'\b'),
                Keyword.Type),

            # builtins
            (words([
                u'ARGS', u'CPU_CORES', u'C_NULL', u'DevNull', u'ENDIAN_BOM',
                u'ENV', u'I', u'Inf', u'Inf16', u'Inf32', u'Inf64',
                u'InsertionSort', u'JULIA_HOME', u'LOAD_PATH', u'MergeSort',
                u'NaN', u'NaN16', u'NaN32', u'NaN64', u'OS_NAME',
                u'QuickSort', u'RoundDown', u'RoundFromZero', u'RoundNearest',
                u'RoundNearestTiesAway', u'RoundNearestTiesUp',
                u'RoundToZero', u'RoundUp', u'STDERR', u'STDIN', u'STDOUT',
                u'VERSION', u'WORD_SIZE', u'catalan', u'e', u'eu',
                u'eulergamma', u'golden', u'im', u'nothing', u'pi', u'γ',
                u'π', u'φ'],
                suffix=r'\b'), Name.Builtin),

            # operators
            # see: https://github.com/JuliaLang/julia/blob/master/src/julia-parser.scm
            (words([
                # prec-assignment
                u'=', u':=', u'+=', u'-=', u'*=', u'/=', u'//=', u'.//=', u'.*=', u'./=',
                u'\\=', u'.\\=', u'^=', u'.^=', u'÷=', u'.÷=', u'%=', u'.%=', u'|=', u'&=',
                u'$=', u'=>', u'<<=', u'>>=', u'>>>=', u'~', u'.+=', u'.-=',
                # prec-conditional
                u'?',
                # prec-arrow
                u'--', u'-->',
                # prec-lazy-or
                u'||',
                # prec-lazy-and
                u'&&',
                # prec-comparison
                u'>', u'<', u'>=', u'≥', u'<=', u'≤', u'==', u'===', u'≡', u'!=', u'≠',
                u'!==', u'≢', u'.>', u'.<', u'.>=', u'.≥', u'.<=', u'.≤', u'.==', u'.!=',
                u'.≠', u'.=', u'.!', u'<:', u'>:', u'∈', u'∉', u'∋', u'∌', u'⊆',
                u'⊈', u'⊂',
                u'⊄', u'⊊',
                # prec-pipe
                u'|>', u'<|',
                # prec-colon
                u':',
                # prec-plus
                u'+', u'-', u'.+', u'.-', u'|', u'∪', u'$',
                # prec-bitshift
                u'<<', u'>>', u'>>>', u'.<<', u'.>>', u'.>>>',
                # prec-times
                u'*', u'/', u'./', u'÷', u'.÷', u'%', u'⋅', u'.%', u'.*', u'\\', u'.\\', u'&', u'∩',
                # prec-rational
                u'//', u'.//',
                # prec-power
                u'^', u'.^',
                # prec-decl
                u'::',
                # prec-dot
                u'.',
                # unary op
                u'+', u'-', u'!', u'√', u'∛', u'∜'
            ]), Operator),

            # chars
            (r"'(\\.|\\[0-7]{1,3}|\\x[a-fA-F0-9]{1,3}|\\u[a-fA-F0-9]{1,4}|"
             r"\\U[a-fA-F0-9]{1,6}|[^\\\'\n])'", String.Char),

            # try to match trailing transpose
            (r'(?<=[.\w)\]])\'+', Operator),

            # strings
            (r'"""', String, 'tqstring'),
            (r'"', String, 'string'),

            # regular expressions
            (r'r"""', String.Regex, 'tqregex'),
            (r'r"', String.Regex, 'regex'),

            # backticks
            (r'`', String.Backtick, 'command'),

            # names
            (allowed_variable, Name),
            (r'@' + allowed_variable, Name.Decorator),

            # numbers
            (r'(\d+(_\d+)+\.\d*|\d*\.\d+(_\d+)+)([eEf][+-]?[0-9]+)?', Number.Float),
            (r'(\d+\.\d*|\d*\.\d+)([eEf][+-]?[0-9]+)?', Number.Float),
            (r'\d+(_\d+)+[eEf][+-]?[0-9]+', Number.Float),
            (r'\d+[eEf][+-]?[0-9]+', Number.Float),
            (r'0b[01]+(_[01]+)+', Number.Bin),
            (r'0b[01]+', Number.Bin),
            (r'0o[0-7]+(_[0-7]+)+', Number.Oct),
            (r'0o[0-7]+', Number.Oct),
            (r'0x[a-fA-F0-9]+(_[a-fA-F0-9]+)+', Number.Hex),
            (r'0x[a-fA-F0-9]+', Number.Hex),
            (r'\d+(_\d+)+', Number.Integer),
            (r'\d+', Number.Integer)
        ],

        "blockcomment": [
            (r'[^=#]', Comment.Multiline),
            (r'#=', Comment.Multiline, '#push'),
            (r'=#', Comment.Multiline, '#pop'),
            (r'[=#]', Comment.Multiline),
        ],

        'string': [
            (r'"', String, '#pop'),
            # FIXME: This escape pattern is not perfect.
            (r'\\([\\"\'$nrbtfav]|(x|u|U)[a-fA-F0-9]+|\d+)', String.Escape),
            # Interpolation is defined as "$" followed by the shortest full
            # expression, which is something we can't parse.
            # Include the most common cases here: $word, and $(paren'd expr).
            (r'\$' + allowed_variable, String.Interpol),
            # (r'\$[a-zA-Z_]+', String.Interpol),
            (r'(\$)(\()', bygroups(String.Interpol, Punctuation), 'in-intp'),
            # @printf and @sprintf formats
            (r'%[-#0 +]*([0-9]+|[*])?(\.([0-9]+|[*]))?[hlL]?[E-GXc-giorsux%]',
             String.Interpol),
            (r'.|\s', String),
        ],

        'tqstring': [
            (r'"""', String, '#pop'),
            (r'\\([\\"\'$nrbtfav]|(x|u|U)[a-fA-F0-9]+|\d+)', String.Escape),
            (r'\$' + allowed_variable, String.Interpol),
            (r'(\$)(\()', bygroups(String.Interpol, Punctuation), 'in-intp'),
            (r'.|\s', String),
        ],

        'regex': [
            (r'"', String.Regex, '#pop'),
            (r'\\"', String.Regex),
            (r'.|\s', String.Regex),
        ],

        'tqregex': [
            (r'"""', String.Regex, '#pop'),
            (r'.|\s', String.Regex),
        ],

        'command': [
            (r'`', String.Backtick, '#pop'),
            (r'\$' + allowed_variable, String.Interpol),
            (r'(\$)(\()', bygroups(String.Interpol, Punctuation), 'in-intp'),
            (r'.|\s', String.Backtick)
        ],

        'in-intp': [
            (r'\(', Punctuation, '#push'),
            (r'\)', Punctuation, '#pop'),
            include('root'),
        ]
    }

    def analyse_text(text):
        return shebang_matches(text, r'julia')


class JuliaConsoleLexer(Lexer):
    """
    For Julia console sessions. Modeled after MatlabSessionLexer.

    .. versionadded:: 1.6
    """
    name = 'Julia console'
    aliases = ['jlcon']

    def get_tokens_unprocessed(self, text):
        jllexer = JuliaLexer(**self.options)
        start = 0
        curcode = ''
        insertions = []
        output = False
        error = False

        for line in text.splitlines(True):
            if line.startswith('julia>'):
                insertions.append((len(curcode), [(0, Generic.Prompt, line[:6])]))
                curcode += line[6:]
                output = False
                error = False
            elif line.startswith('help?>') or line.startswith('shell>'):
                yield start, Generic.Prompt, line[:6]
                yield start + 6, Text, line[6:]
                output = False
                error = False
            elif line.startswith('      ') and not output:
                insertions.append((len(curcode), [(0, Text, line[:6])]))
                curcode += line[6:]
            else:
                if curcode:
                    for item in do_insertions(
                            insertions, jllexer.get_tokens_unprocessed(curcode)):
                        yield item
                    curcode = ''
                    insertions = []
                if line.startswith('ERROR: ') or error:
                    yield start, Generic.Error, line
                    error = True
                else:
                    yield start, Generic.Output, line
                output = True
            start += len(line)

        if curcode:
            for item in do_insertions(
                    insertions, jllexer.get_tokens_unprocessed(curcode)):
                yield item
