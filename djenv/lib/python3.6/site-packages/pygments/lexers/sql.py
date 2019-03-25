# -*- coding: utf-8 -*-
"""
    pygments.lexers.sql
    ~~~~~~~~~~~~~~~~~~~

    Lexers for various SQL dialects and related interactive sessions.

    Postgres specific lexers:

    `PostgresLexer`
        A SQL lexer for the PostgreSQL dialect. Differences w.r.t. the SQL
        lexer are:

        - keywords and data types list parsed from the PG docs (run the
          `_postgres_builtins` module to update them);
        - Content of $-strings parsed using a specific lexer, e.g. the content
          of a PL/Python function is parsed using the Python lexer;
        - parse PG specific constructs: E-strings, $-strings, U&-strings,
          different operators and punctuation.

    `PlPgsqlLexer`
        A lexer for the PL/pgSQL language. Adds a few specific construct on
        top of the PG SQL lexer (such as <<label>>).

    `PostgresConsoleLexer`
        A lexer to highlight an interactive psql session:

        - identifies the prompt and does its best to detect the end of command
          in multiline statement where not all the lines are prefixed by a
          prompt, telling them apart from the output;
        - highlights errors in the output and notification levels;
        - handles psql backslash commands.

    The ``tests/examplefiles`` contains a few test files with data to be
    parsed by these lexers.

    :copyright: Copyright 2006-2017 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from pygments.lexer import Lexer, RegexLexer, do_insertions, bygroups, words
from pygments.token import Punctuation, Whitespace, Error, \
    Text, Comment, Operator, Keyword, Name, String, Number, Generic
from pygments.lexers import get_lexer_by_name, ClassNotFound
from pygments.util import iteritems

from pygments.lexers._postgres_builtins import KEYWORDS, DATATYPES, \
    PSEUDO_TYPES, PLPGSQL_KEYWORDS
from pygments.lexers import _tsql_builtins


__all__ = ['PostgresLexer', 'PlPgsqlLexer', 'PostgresConsoleLexer',
           'SqlLexer', 'TransactSqlLexer', 'MySqlLexer',
           'SqliteConsoleLexer', 'RqlLexer']

line_re  = re.compile('.*?\n')

language_re = re.compile(r"\s+LANGUAGE\s+'?(\w+)'?", re.IGNORECASE)

do_re = re.compile(r'\bDO\b', re.IGNORECASE) 


def language_callback(lexer, match):
    """Parse the content of a $-string using a lexer

    The lexer is chosen looking for a nearby LANGUAGE or assumed as
    plpgsql if inside a DO statement and no LANGUAGE has been found.
    """
    l = None
    m = language_re.match(lexer.text[match.end():match.end()+100])
    if m is not None:
        l = lexer._get_lexer(m.group(1))
    else:
        m = list(language_re.finditer(
            lexer.text[max(0, match.start()-100):match.start()]))
        if m:
            l = lexer._get_lexer(m[-1].group(1))
        else:
            m = list(do_re.finditer(
                lexer.text[max(0, match.start()-25):match.start()]))
            if m:
                l = lexer._get_lexer('plpgsql')
    
    # 1 = $, 2 = delimiter, 3 = $
    yield (match.start(1), String, match.group(1))
    yield (match.start(2), String.Delimiter, match.group(2))
    yield (match.start(3), String, match.group(3))
    # 4 = string contents
    if l:
        for x in l.get_tokens_unprocessed(match.group(4)):
            yield x
    else:
        yield (match.start(4), String, match.group(4))
    # 5 = $, 6 = delimiter, 7 = $
    yield (match.start(5), String, match.group(5))
    yield (match.start(6), String.Delimiter, match.group(6))
    yield (match.start(7), String, match.group(7))


class PostgresBase(object):
    """Base class for Postgres-related lexers.

    This is implemented as a mixin to avoid the Lexer metaclass kicking in.
    this way the different lexer don't have a common Lexer ancestor. If they
    had, _tokens could be created on this ancestor and not updated for the
    other classes, resulting e.g. in PL/pgSQL parsed as SQL. This shortcoming
    seem to suggest that regexp lexers are not really subclassable.
    """
    def get_tokens_unprocessed(self, text, *args):
        # Have a copy of the entire text to be used by `language_callback`.
        self.text = text
        for x in super(PostgresBase, self).get_tokens_unprocessed(
                text, *args):
            yield x

    def _get_lexer(self, lang):
        if lang.lower() == 'sql':
            return get_lexer_by_name('postgresql', **self.options)

        tries = [lang]
        if lang.startswith('pl'):
            tries.append(lang[2:])
        if lang.endswith('u'):
            tries.append(lang[:-1])
        if lang.startswith('pl') and lang.endswith('u'):
            tries.append(lang[2:-1])

        for l in tries:
            try:
                return get_lexer_by_name(l, **self.options)
            except ClassNotFound:
                pass
        else:
            # TODO: better logging
            # print >>sys.stderr, "language not found:", lang
            return None


class PostgresLexer(PostgresBase, RegexLexer):
    """
    Lexer for the PostgreSQL dialect of SQL.

    .. versionadded:: 1.5
    """

    name = 'PostgreSQL SQL dialect'
    aliases = ['postgresql', 'postgres']
    mimetypes = ['text/x-postgresql']

    flags = re.IGNORECASE
    tokens = {
        'root': [
            (r'\s+', Text),
            (r'--.*\n?', Comment.Single),
            (r'/\*', Comment.Multiline, 'multiline-comments'),
            (r'(' + '|'.join(s.replace(" ", r"\s+")
                             for s in DATATYPES + PSEUDO_TYPES)
             + r')\b', Name.Builtin),
            (words(KEYWORDS, suffix=r'\b'), Keyword),
            (r'[+*/<>=~!@#%^&|`?-]+', Operator),
            (r'::', Operator),  # cast
            (r'\$\d+', Name.Variable),
            (r'([0-9]*\.[0-9]*|[0-9]+)(e[+-]?[0-9]+)?', Number.Float),
            (r'[0-9]+', Number.Integer),
            (r"((?:E|U&)?)(')", bygroups(String.Affix, String.Single), 'string'),
            # quoted identifier
            (r'((?:U&)?)(")', bygroups(String.Affix, String.Name), 'quoted-ident'),
            (r'(?s)(\$)([^$]*)(\$)(.*?)(\$)(\2)(\$)', language_callback),
            (r'[a-z_]\w*', Name),

            # psql variable in SQL
            (r""":(['"]?)[a-z]\w*\b\1""", Name.Variable),

            (r'[;:()\[\]{},.]', Punctuation),
        ],
        'multiline-comments': [
            (r'/\*', Comment.Multiline, 'multiline-comments'),
            (r'\*/', Comment.Multiline, '#pop'),
            (r'[^/*]+', Comment.Multiline),
            (r'[/*]', Comment.Multiline)
        ],
        'string': [
            (r"[^']+", String.Single),
            (r"''", String.Single),
            (r"'", String.Single, '#pop'),
        ],
        'quoted-ident': [
            (r'[^"]+', String.Name),
            (r'""', String.Name),
            (r'"', String.Name, '#pop'),
        ],
    }


class PlPgsqlLexer(PostgresBase, RegexLexer):
    """
    Handle the extra syntax in Pl/pgSQL language.

    .. versionadded:: 1.5
    """
    name = 'PL/pgSQL'
    aliases = ['plpgsql']
    mimetypes = ['text/x-plpgsql']

    flags = re.IGNORECASE
    tokens = dict((k, l[:]) for (k, l) in iteritems(PostgresLexer.tokens))

    # extend the keywords list
    for i, pattern in enumerate(tokens['root']):
        if pattern[1] == Keyword:
            tokens['root'][i] = (
                words(KEYWORDS + PLPGSQL_KEYWORDS, suffix=r'\b'),
                Keyword)
            del i
            break
    else:
        assert 0, "SQL keywords not found"

    # Add specific PL/pgSQL rules (before the SQL ones)
    tokens['root'][:0] = [
        (r'\%[a-z]\w*\b', Name.Builtin),     # actually, a datatype
        (r':=', Operator),
        (r'\<\<[a-z]\w*\>\>', Name.Label),
        (r'\#[a-z]\w*\b', Keyword.Pseudo),   # #variable_conflict
    ]


class PsqlRegexLexer(PostgresBase, RegexLexer):
    """
    Extend the PostgresLexer adding support specific for psql commands.

    This is not a complete psql lexer yet as it lacks prompt support
    and output rendering.
    """

    name = 'PostgreSQL console - regexp based lexer'
    aliases = []    # not public

    flags = re.IGNORECASE
    tokens = dict((k, l[:]) for (k, l) in iteritems(PostgresLexer.tokens))

    tokens['root'].append(
        (r'\\[^\s]+', Keyword.Pseudo, 'psql-command'))
    tokens['psql-command'] = [
        (r'\n', Text, 'root'),
        (r'\s+', Text),
        (r'\\[^\s]+', Keyword.Pseudo),
        (r""":(['"]?)[a-z]\w*\b\1""", Name.Variable),
        (r"'(''|[^'])*'", String.Single),
        (r"`([^`])*`", String.Backtick),
        (r"[^\s]+", String.Symbol),
    ]

re_prompt = re.compile(r'^(\S.*?)??[=\-\(\$\'\"][#>]')
re_psql_command = re.compile(r'\s*\\')
re_end_command = re.compile(r';\s*(--.*?)?$')
re_psql_command = re.compile(r'(\s*)(\\.+?)(\s+)$')
re_error = re.compile(r'(ERROR|FATAL):')
re_message = re.compile(
    r'((?:DEBUG|INFO|NOTICE|WARNING|ERROR|'
    r'FATAL|HINT|DETAIL|CONTEXT|LINE [0-9]+):)(.*?\n)')


class lookahead(object):
    """Wrap an iterator and allow pushing back an item."""
    def __init__(self, x):
        self.iter = iter(x)
        self._nextitem = None

    def __iter__(self):
        return self

    def send(self, i):
        self._nextitem = i
        return i

    def __next__(self):
        if self._nextitem is not None:
            ni = self._nextitem
            self._nextitem = None
            return ni
        return next(self.iter)
    next = __next__


class PostgresConsoleLexer(Lexer):
    """
    Lexer for psql sessions.

    .. versionadded:: 1.5
    """

    name = 'PostgreSQL console (psql)'
    aliases = ['psql', 'postgresql-console', 'postgres-console']
    mimetypes = ['text/x-postgresql-psql']

    def get_tokens_unprocessed(self, data):
        sql = PsqlRegexLexer(**self.options)

        lines = lookahead(line_re.findall(data))

        # prompt-output cycle
        while 1:

            # consume the lines of the command: start with an optional prompt
            # and continue until the end of command is detected
            curcode = ''
            insertions = []
            for line in lines:
                # Identify a shell prompt in case of psql commandline example
                if line.startswith('$') and not curcode:
                    lexer = get_lexer_by_name('console', **self.options)
                    for x in lexer.get_tokens_unprocessed(line):
                        yield x
                    break

                # Identify a psql prompt
                mprompt = re_prompt.match(line)
                if mprompt is not None:
                    insertions.append((len(curcode),
                                       [(0, Generic.Prompt, mprompt.group())]))
                    curcode += line[len(mprompt.group()):]
                else:
                    curcode += line

                # Check if this is the end of the command
                # TODO: better handle multiline comments at the end with
                # a lexer with an external state?
                if re_psql_command.match(curcode) \
                   or re_end_command.search(curcode):
                    break

            # Emit the combined stream of command and prompt(s)
            for item in do_insertions(insertions,
                                      sql.get_tokens_unprocessed(curcode)):
                yield item

            # Emit the output lines
            out_token = Generic.Output
            for line in lines:
                mprompt = re_prompt.match(line)
                if mprompt is not None:
                    # push the line back to have it processed by the prompt
                    lines.send(line)
                    break

                mmsg = re_message.match(line)
                if mmsg is not None:
                    if mmsg.group(1).startswith("ERROR") \
                       or mmsg.group(1).startswith("FATAL"):
                        out_token = Generic.Error
                    yield (mmsg.start(1), Generic.Strong, mmsg.group(1))
                    yield (mmsg.start(2), out_token, mmsg.group(2))
                else:
                    yield (0, out_token, line)
            else:
                return


class SqlLexer(RegexLexer):
    """
    Lexer for Structured Query Language. Currently, this lexer does
    not recognize any special syntax except ANSI SQL.
    """

    name = 'SQL'
    aliases = ['sql']
    filenames = ['*.sql']
    mimetypes = ['text/x-sql']

    flags = re.IGNORECASE
    tokens = {
        'root': [
            (r'\s+', Text),
            (r'--.*\n?', Comment.Single),
            (r'/\*', Comment.Multiline, 'multiline-comments'),
            (words((
                'ABORT', 'ABS', 'ABSOLUTE', 'ACCESS', 'ADA', 'ADD', 'ADMIN', 'AFTER', 'AGGREGATE',
                'ALIAS', 'ALL', 'ALLOCATE', 'ALTER', 'ANALYSE', 'ANALYZE', 'AND', 'ANY', 'ARE', 'AS',
                'ASC', 'ASENSITIVE', 'ASSERTION', 'ASSIGNMENT', 'ASYMMETRIC', 'AT', 'ATOMIC',
                'AUTHORIZATION', 'AVG', 'BACKWARD', 'BEFORE', 'BEGIN', 'BETWEEN', 'BITVAR',
                'BIT_LENGTH', 'BOTH', 'BREADTH', 'BY', 'C', 'CACHE', 'CALL', 'CALLED', 'CARDINALITY',
                'CASCADE', 'CASCADED', 'CASE', 'CAST', 'CATALOG', 'CATALOG_NAME', 'CHAIN',
                'CHARACTERISTICS', 'CHARACTER_LENGTH', 'CHARACTER_SET_CATALOG',
                'CHARACTER_SET_NAME', 'CHARACTER_SET_SCHEMA', 'CHAR_LENGTH', 'CHECK',
                'CHECKED', 'CHECKPOINT', 'CLASS', 'CLASS_ORIGIN', 'CLOB', 'CLOSE', 'CLUSTER',
                'COALSECE', 'COBOL', 'COLLATE', 'COLLATION', 'COLLATION_CATALOG',
                'COLLATION_NAME', 'COLLATION_SCHEMA', 'COLUMN', 'COLUMN_NAME',
                'COMMAND_FUNCTION', 'COMMAND_FUNCTION_CODE', 'COMMENT', 'COMMIT',
                'COMMITTED', 'COMPLETION', 'CONDITION_NUMBER', 'CONNECT', 'CONNECTION',
                'CONNECTION_NAME', 'CONSTRAINT', 'CONSTRAINTS', 'CONSTRAINT_CATALOG',
                'CONSTRAINT_NAME', 'CONSTRAINT_SCHEMA', 'CONSTRUCTOR', 'CONTAINS',
                'CONTINUE', 'CONVERSION', 'CONVERT', 'COPY', 'CORRESPONTING', 'COUNT',
                'CREATE', 'CREATEDB', 'CREATEUSER', 'CROSS', 'CUBE', 'CURRENT', 'CURRENT_DATE',
                'CURRENT_PATH', 'CURRENT_ROLE', 'CURRENT_TIME', 'CURRENT_TIMESTAMP',
                'CURRENT_USER', 'CURSOR', 'CURSOR_NAME', 'CYCLE', 'DATA', 'DATABASE',
                'DATETIME_INTERVAL_CODE', 'DATETIME_INTERVAL_PRECISION', 'DAY',
                'DEALLOCATE', 'DECLARE', 'DEFAULT', 'DEFAULTS', 'DEFERRABLE', 'DEFERRED',
                'DEFINED', 'DEFINER', 'DELETE', 'DELIMITER', 'DELIMITERS', 'DEREF', 'DESC',
                'DESCRIBE', 'DESCRIPTOR', 'DESTROY', 'DESTRUCTOR', 'DETERMINISTIC',
                'DIAGNOSTICS', 'DICTIONARY', 'DISCONNECT', 'DISPATCH', 'DISTINCT', 'DO',
                'DOMAIN', 'DROP', 'DYNAMIC', 'DYNAMIC_FUNCTION', 'DYNAMIC_FUNCTION_CODE', 'EACH',
                'ELSE', 'ELSIF', 'ENCODING', 'ENCRYPTED', 'END', 'END-EXEC', 'EQUALS', 'ESCAPE', 'EVERY',
                'EXCEPTION', 'EXCEPT', 'EXCLUDING', 'EXCLUSIVE', 'EXEC', 'EXECUTE', 'EXISTING',
                'EXISTS', 'EXPLAIN', 'EXTERNAL', 'EXTRACT', 'FALSE', 'FETCH', 'FINAL', 'FIRST', 'FOR',
                'FORCE', 'FOREIGN', 'FORTRAN', 'FORWARD', 'FOUND', 'FREE', 'FREEZE', 'FROM', 'FULL',
                'FUNCTION', 'G', 'GENERAL', 'GENERATED', 'GET', 'GLOBAL', 'GO', 'GOTO', 'GRANT', 'GRANTED',
                'GROUP', 'GROUPING', 'HANDLER', 'HAVING', 'HIERARCHY', 'HOLD', 'HOST', 'IDENTITY', 'IF',
                'IGNORE', 'ILIKE', 'IMMEDIATE', 'IMMUTABLE', 'IMPLEMENTATION', 'IMPLICIT', 'IN',
                'INCLUDING', 'INCREMENT', 'INDEX', 'INDITCATOR', 'INFIX', 'INHERITS', 'INITIALIZE',
                'INITIALLY', 'INNER', 'INOUT', 'INPUT', 'INSENSITIVE', 'INSERT', 'INSTANTIABLE',
                'INSTEAD', 'INTERSECT', 'INTO', 'INVOKER', 'IS', 'ISNULL', 'ISOLATION', 'ITERATE', 'JOIN',
                'KEY', 'KEY_MEMBER', 'KEY_TYPE', 'LANCOMPILER', 'LANGUAGE', 'LARGE', 'LAST',
                'LATERAL', 'LEADING', 'LEFT', 'LENGTH', 'LESS', 'LEVEL', 'LIKE', 'LIMIT', 'LISTEN', 'LOAD',
                'LOCAL', 'LOCALTIME', 'LOCALTIMESTAMP', 'LOCATION', 'LOCATOR', 'LOCK', 'LOWER',
                'MAP', 'MATCH', 'MAX', 'MAXVALUE', 'MESSAGE_LENGTH', 'MESSAGE_OCTET_LENGTH',
                'MESSAGE_TEXT', 'METHOD', 'MIN', 'MINUTE', 'MINVALUE', 'MOD', 'MODE', 'MODIFIES',
                'MODIFY', 'MONTH', 'MORE', 'MOVE', 'MUMPS', 'NAMES', 'NATIONAL', 'NATURAL', 'NCHAR',
                'NCLOB', 'NEW', 'NEXT', 'NO', 'NOCREATEDB', 'NOCREATEUSER', 'NONE', 'NOT', 'NOTHING',
                'NOTIFY', 'NOTNULL', 'NULL', 'NULLABLE', 'NULLIF', 'OBJECT', 'OCTET_LENGTH', 'OF', 'OFF',
                'OFFSET', 'OIDS', 'OLD', 'ON', 'ONLY', 'OPEN', 'OPERATION', 'OPERATOR', 'OPTION', 'OPTIONS',
                'OR', 'ORDER', 'ORDINALITY', 'OUT', 'OUTER', 'OUTPUT', 'OVERLAPS', 'OVERLAY', 'OVERRIDING',
                'OWNER', 'PAD', 'PARAMETER', 'PARAMETERS', 'PARAMETER_MODE', 'PARAMATER_NAME',
                'PARAMATER_ORDINAL_POSITION', 'PARAMETER_SPECIFIC_CATALOG',
                'PARAMETER_SPECIFIC_NAME', 'PARAMATER_SPECIFIC_SCHEMA', 'PARTIAL',
                'PASCAL', 'PENDANT', 'PLACING', 'PLI', 'POSITION', 'POSTFIX', 'PRECISION', 'PREFIX',
                'PREORDER', 'PREPARE', 'PRESERVE', 'PRIMARY', 'PRIOR', 'PRIVILEGES', 'PROCEDURAL',
                'PROCEDURE', 'PUBLIC', 'READ', 'READS', 'RECHECK', 'RECURSIVE', 'REF', 'REFERENCES',
                'REFERENCING', 'REINDEX', 'RELATIVE', 'RENAME', 'REPEATABLE', 'REPLACE', 'RESET',
                'RESTART', 'RESTRICT', 'RESULT', 'RETURN', 'RETURNED_LENGTH',
                'RETURNED_OCTET_LENGTH', 'RETURNED_SQLSTATE', 'RETURNS', 'REVOKE', 'RIGHT',
                'ROLE', 'ROLLBACK', 'ROLLUP', 'ROUTINE', 'ROUTINE_CATALOG', 'ROUTINE_NAME',
                'ROUTINE_SCHEMA', 'ROW', 'ROWS', 'ROW_COUNT', 'RULE', 'SAVE_POINT', 'SCALE', 'SCHEMA',
                'SCHEMA_NAME', 'SCOPE', 'SCROLL', 'SEARCH', 'SECOND', 'SECURITY', 'SELECT', 'SELF',
                'SENSITIVE', 'SERIALIZABLE', 'SERVER_NAME', 'SESSION', 'SESSION_USER', 'SET',
                'SETOF', 'SETS', 'SHARE', 'SHOW', 'SIMILAR', 'SIMPLE', 'SIZE', 'SOME', 'SOURCE', 'SPACE',
                'SPECIFIC', 'SPECIFICTYPE', 'SPECIFIC_NAME', 'SQL', 'SQLCODE', 'SQLERROR',
                'SQLEXCEPTION', 'SQLSTATE', 'SQLWARNINIG', 'STABLE', 'START', 'STATE', 'STATEMENT',
                'STATIC', 'STATISTICS', 'STDIN', 'STDOUT', 'STORAGE', 'STRICT', 'STRUCTURE', 'STYPE',
                'SUBCLASS_ORIGIN', 'SUBLIST', 'SUBSTRING', 'SUM', 'SYMMETRIC', 'SYSID', 'SYSTEM',
                'SYSTEM_USER', 'TABLE', 'TABLE_NAME', ' TEMP', 'TEMPLATE', 'TEMPORARY', 'TERMINATE',
                'THAN', 'THEN', 'TIMESTAMP', 'TIMEZONE_HOUR', 'TIMEZONE_MINUTE', 'TO', 'TOAST',
                'TRAILING', 'TRANSATION', 'TRANSACTIONS_COMMITTED',
                'TRANSACTIONS_ROLLED_BACK', 'TRANSATION_ACTIVE', 'TRANSFORM',
                'TRANSFORMS', 'TRANSLATE', 'TRANSLATION', 'TREAT', 'TRIGGER', 'TRIGGER_CATALOG',
                'TRIGGER_NAME', 'TRIGGER_SCHEMA', 'TRIM', 'TRUE', 'TRUNCATE', 'TRUSTED', 'TYPE',
                'UNCOMMITTED', 'UNDER', 'UNENCRYPTED', 'UNION', 'UNIQUE', 'UNKNOWN', 'UNLISTEN',
                'UNNAMED', 'UNNEST', 'UNTIL', 'UPDATE', 'UPPER', 'USAGE', 'USER',
                'USER_DEFINED_TYPE_CATALOG', 'USER_DEFINED_TYPE_NAME',
                'USER_DEFINED_TYPE_SCHEMA', 'USING', 'VACUUM', 'VALID', 'VALIDATOR', 'VALUES',
                'VARIABLE', 'VERBOSE', 'VERSION', 'VIEW', 'VOLATILE', 'WHEN', 'WHENEVER', 'WHERE',
                'WITH', 'WITHOUT', 'WORK', 'WRITE', 'YEAR', 'ZONE'), suffix=r'\b'),
             Keyword),
            (words((
                'ARRAY', 'BIGINT', 'BINARY', 'BIT', 'BLOB', 'BOOLEAN', 'CHAR', 'CHARACTER', 'DATE',
                'DEC', 'DECIMAL', 'FLOAT', 'INT', 'INTEGER', 'INTERVAL', 'NUMBER', 'NUMERIC', 'REAL',
                'SERIAL', 'SMALLINT', 'VARCHAR', 'VARYING', 'INT8', 'SERIAL8', 'TEXT'), suffix=r'\b'),
             Name.Builtin),
            (r'[+*/<>=~!@#%^&|`?-]', Operator),
            (r'[0-9]+', Number.Integer),
            # TODO: Backslash escapes?
            (r"'(''|[^'])*'", String.Single),
            (r'"(""|[^"])*"', String.Symbol),  # not a real string literal in ANSI SQL
            (r'[a-z_][\w$]*', Name),  # allow $s in strings for Oracle
            (r'[;:()\[\],.]', Punctuation)
        ],
        'multiline-comments': [
            (r'/\*', Comment.Multiline, 'multiline-comments'),
            (r'\*/', Comment.Multiline, '#pop'),
            (r'[^/*]+', Comment.Multiline),
            (r'[/*]', Comment.Multiline)
        ]
    }


class TransactSqlLexer(RegexLexer):
    """
    Transact-SQL (T-SQL) is Microsoft's and Sybase's proprietary extension to
    SQL.

    The list of keywords includes ODBC and keywords reserved for future use..
    """

    name = 'Transact-SQL'
    aliases = ['tsql', 't-sql']
    filenames = ['*.sql']
    mimetypes = ['text/x-tsql']

    # Use re.UNICODE to allow non ASCII letters in names.
    flags = re.IGNORECASE | re.UNICODE
    tokens = {
        'root': [
            (r'\s+', Whitespace),
            (r'(?m)--.*?$\n?', Comment.Single),
            (r'/\*', Comment.Multiline, 'multiline-comments'),
            (words(_tsql_builtins.OPERATORS), Operator),
            (words(_tsql_builtins.OPERATOR_WORDS, suffix=r'\b'), Operator.Word),
            (words(_tsql_builtins.TYPES, suffix=r'\b'), Name.Class),
            (words(_tsql_builtins.FUNCTIONS, suffix=r'\b'), Name.Function),
            (r'(goto)(\s+)(\w+\b)', bygroups(Keyword, Whitespace, Name.Label)),
            (words(_tsql_builtins.KEYWORDS, suffix=r'\b'), Keyword),
            (r'(\[)([^]]+)(\])', bygroups(Operator, Name, Operator)),
            (r'0x[0-9a-f]+', Number.Hex),
            # Float variant 1, for example: 1., 1.e2, 1.2e3
            (r'[0-9]+\.[0-9]*(e[+-]?[0-9]+)?', Number.Float),
            # Float variant 2, for example: .1, .1e2
            (r'\.[0-9]+(e[+-]?[0-9]+)?', Number.Float),
            # Float variant 3, for example: 123e45
            (r'[0-9]+e[+-]?[0-9]+', Number.Float),
            (r'[0-9]+', Number.Integer),
            (r"'(''|[^'])*'", String.Single),
            (r'"(""|[^"])*"', String.Symbol),
            (r'[;(),.]', Punctuation),
            # Below we use \w even for the first "real" character because
            # tokens starting with a digit have already been recognized
            # as Number above.
            (r'@@\w+', Name.Builtin),
            (r'@\w+', Name.Variable),
            (r'(\w+)(:)', bygroups(Name.Label, Punctuation)),
            (r'#?#?\w+', Name),  # names for temp tables and anything else
            (r'\?', Name.Variable.Magic),  # parameter for prepared statements
        ],
        'multiline-comments': [
            (r'/\*', Comment.Multiline, 'multiline-comments'),
            (r'\*/', Comment.Multiline, '#pop'),
            (r'[^/*]+', Comment.Multiline),
            (r'[/*]', Comment.Multiline)
        ]
    }


class MySqlLexer(RegexLexer):
    """
    Special lexer for MySQL.
    """

    name = 'MySQL'
    aliases = ['mysql']
    mimetypes = ['text/x-mysql']

    flags = re.IGNORECASE
    tokens = {
        'root': [
            (r'\s+', Text),
            (r'(#|--\s+).*\n?', Comment.Single),
            (r'/\*', Comment.Multiline, 'multiline-comments'),
            (r'[0-9]+', Number.Integer),
            (r'[0-9]*\.[0-9]+(e[+-][0-9]+)', Number.Float),
            (r"'(\\\\|\\'|''|[^'])*'", String.Single),
            (r'"(\\\\|\\"|""|[^"])*"', String.Double),
            (r"`(\\\\|\\`|``|[^`])*`", String.Symbol),
            (r'[+*/<>=~!@#%^&|`?-]', Operator),
            (r'\b(tinyint|smallint|mediumint|int|integer|bigint|date|'
             r'datetime|time|bit|bool|tinytext|mediumtext|longtext|text|'
             r'tinyblob|mediumblob|longblob|blob|float|double|double\s+'
             r'precision|real|numeric|dec|decimal|timestamp|year|char|'
             r'varchar|varbinary|varcharacter|enum|set)(\b\s*)(\()?',
             bygroups(Keyword.Type, Text, Punctuation)),
            (r'\b(add|all|alter|analyze|and|as|asc|asensitive|before|between|'
             r'bigint|binary|blob|both|by|call|cascade|case|change|char|'
             r'character|check|collate|column|condition|constraint|continue|'
             r'convert|create|cross|current_date|current_time|'
             r'current_timestamp|current_user|cursor|database|databases|'
             r'day_hour|day_microsecond|day_minute|day_second|dec|decimal|'
             r'declare|default|delayed|delete|desc|describe|deterministic|'
             r'distinct|distinctrow|div|double|drop|dual|each|else|elseif|'
             r'enclosed|escaped|exists|exit|explain|fetch|flush|float|float4|'
             r'float8|for|force|foreign|from|fulltext|grant|group|having|'
             r'high_priority|hour_microsecond|hour_minute|hour_second|if|'
             r'ignore|in|index|infile|inner|inout|insensitive|insert|int|'
             r'int1|int2|int3|int4|int8|integer|interval|into|is|iterate|'
             r'join|key|keys|kill|leading|leave|left|like|limit|lines|load|'
             r'localtime|localtimestamp|lock|long|loop|low_priority|match|'
             r'minute_microsecond|minute_second|mod|modifies|natural|'
             r'no_write_to_binlog|not|numeric|on|optimize|option|optionally|'
             r'or|order|out|outer|outfile|precision|primary|procedure|purge|'
             r'raid0|read|reads|real|references|regexp|release|rename|repeat|'
             r'replace|require|restrict|return|revoke|right|rlike|schema|'
             r'schemas|second_microsecond|select|sensitive|separator|set|'
             r'show|smallint|soname|spatial|specific|sql|sql_big_result|'
             r'sql_calc_found_rows|sql_small_result|sqlexception|sqlstate|'
             r'sqlwarning|ssl|starting|straight_join|table|terminated|then|'
             r'to|trailing|trigger|undo|union|unique|unlock|unsigned|update|'
             r'usage|use|using|utc_date|utc_time|utc_timestamp|values|'
             r'varying|when|where|while|with|write|x509|xor|year_month|'
             r'zerofill)\b', Keyword),
            # TODO: this list is not complete
            (r'\b(auto_increment|engine|charset|tables)\b', Keyword.Pseudo),
            (r'(true|false|null)', Name.Constant),
            (r'([a-z_]\w*)(\s*)(\()',
             bygroups(Name.Function, Text, Punctuation)),
            (r'[a-z_]\w*', Name),
            (r'@[a-z0-9]*[._]*[a-z0-9]*', Name.Variable),
            (r'[;:()\[\],.]', Punctuation)
        ],
        'multiline-comments': [
            (r'/\*', Comment.Multiline, 'multiline-comments'),
            (r'\*/', Comment.Multiline, '#pop'),
            (r'[^/*]+', Comment.Multiline),
            (r'[/*]', Comment.Multiline)
        ]
    }


class SqliteConsoleLexer(Lexer):
    """
    Lexer for example sessions using sqlite3.

    .. versionadded:: 0.11
    """

    name = 'sqlite3con'
    aliases = ['sqlite3']
    filenames = ['*.sqlite3-console']
    mimetypes = ['text/x-sqlite3-console']

    def get_tokens_unprocessed(self, data):
        sql = SqlLexer(**self.options)

        curcode = ''
        insertions = []
        for match in line_re.finditer(data):
            line = match.group()
            if line.startswith('sqlite> ') or line.startswith('   ...> '):
                insertions.append((len(curcode),
                                   [(0, Generic.Prompt, line[:8])]))
                curcode += line[8:]
            else:
                if curcode:
                    for item in do_insertions(insertions,
                                              sql.get_tokens_unprocessed(curcode)):
                        yield item
                    curcode = ''
                    insertions = []
                if line.startswith('SQL error: '):
                    yield (match.start(), Generic.Traceback, line)
                else:
                    yield (match.start(), Generic.Output, line)
        if curcode:
            for item in do_insertions(insertions,
                                      sql.get_tokens_unprocessed(curcode)):
                yield item


class RqlLexer(RegexLexer):
    """
    Lexer for Relation Query Language.

    `RQL <http://www.logilab.org/project/rql>`_

    .. versionadded:: 2.0
    """
    name = 'RQL'
    aliases = ['rql']
    filenames = ['*.rql']
    mimetypes = ['text/x-rql']

    flags = re.IGNORECASE
    tokens = {
        'root': [
            (r'\s+', Text),
            (r'(DELETE|SET|INSERT|UNION|DISTINCT|WITH|WHERE|BEING|OR'
             r'|AND|NOT|GROUPBY|HAVING|ORDERBY|ASC|DESC|LIMIT|OFFSET'
             r'|TODAY|NOW|TRUE|FALSE|NULL|EXISTS)\b', Keyword),
            (r'[+*/<>=%-]', Operator),
            (r'(Any|is|instance_of|CWEType|CWRelation)\b', Name.Builtin),
            (r'[0-9]+', Number.Integer),
            (r'[A-Z_]\w*\??', Name),
            (r"'(''|[^'])*'", String.Single),
            (r'"(""|[^"])*"', String.Single),
            (r'[;:()\[\],.]', Punctuation)
        ],
    }
