import string, re, sys, datetime
from .core import TomlError
from .utils import rfc3339_re, parse_rfc3339_re

if sys.version_info[0] == 2:
    _chr = unichr
else:
    _chr = chr

def load(fin, translate=lambda t, x, v: v, object_pairs_hook=dict):
    return loads(fin.read(), translate=translate, object_pairs_hook=object_pairs_hook, filename=getattr(fin, 'name', repr(fin)))

def loads(s, filename='<string>', translate=lambda t, x, v: v, object_pairs_hook=dict):
    if isinstance(s, bytes):
        s = s.decode('utf-8')

    s = s.replace('\r\n', '\n')

    root = object_pairs_hook()
    tables = object_pairs_hook()
    scope = root

    src = _Source(s, filename=filename)
    ast = _p_toml(src, object_pairs_hook=object_pairs_hook)

    def error(msg):
        raise TomlError(msg, pos[0], pos[1], filename)

    def process_value(v, object_pairs_hook):
        kind, text, value, pos = v
        if kind == 'str' and value.startswith('\n'):
            value = value[1:]
        if kind == 'array':
            if value and any(k != value[0][0] for k, t, v, p in value[1:]):
                error('array-type-mismatch')
            value = [process_value(item, object_pairs_hook=object_pairs_hook) for item in value]
        elif kind == 'table':
            value = object_pairs_hook([(k, process_value(value[k], object_pairs_hook=object_pairs_hook)) for k in value])
        return translate(kind, text, value)

    for kind, value, pos in ast:
        if kind == 'kv':
            k, v = value
            if k in scope:
                error('duplicate_keys. Key "{0}" was used more than once.'.format(k))
            scope[k] = process_value(v, object_pairs_hook=object_pairs_hook)
        else:
            is_table_array = (kind == 'table_array')
            cur = tables
            for name in value[:-1]:
                if isinstance(cur.get(name), list):
                    d, cur = cur[name][-1]
                else:
                    d, cur = cur.setdefault(name, (None, object_pairs_hook()))

            scope = object_pairs_hook()
            name = value[-1]
            if name not in cur:
                if is_table_array:
                    cur[name] = [(scope, object_pairs_hook())]
                else:
                    cur[name] = (scope, object_pairs_hook())
            elif isinstance(cur[name], list):
                if not is_table_array:
                    error('table_type_mismatch')
                cur[name].append((scope, object_pairs_hook()))
            else:
                if is_table_array:
                    error('table_type_mismatch')
                old_scope, next_table = cur[name]
                if old_scope is not None:
                    error('duplicate_tables')
                cur[name] = (scope, next_table)

    def merge_tables(scope, tables):
        if scope is None:
            scope = object_pairs_hook()
        for k in tables:
            if k in scope:
                error('key_table_conflict')
            v = tables[k]
            if isinstance(v, list):
                scope[k] = [merge_tables(sc, tbl) for sc, tbl in v]
            else:
                scope[k] = merge_tables(v[0], v[1])
        return scope

    return merge_tables(root, tables)

class _Source:
    def __init__(self, s, filename=None):
        self.s = s
        self._pos = (1, 1)
        self._last = None
        self._filename = filename
        self.backtrack_stack = []

    def last(self):
        return self._last

    def pos(self):
        return self._pos

    def fail(self):
        return self._expect(None)

    def consume_dot(self):
        if self.s:
            self._last = self.s[0]
            self.s = self[1:]
            self._advance(self._last)
            return self._last
        return None

    def expect_dot(self):
        return self._expect(self.consume_dot())

    def consume_eof(self):
        if not self.s:
            self._last = ''
            return True
        return False

    def expect_eof(self):
        return self._expect(self.consume_eof())

    def consume(self, s):
        if self.s.startswith(s):
            self.s = self.s[len(s):]
            self._last = s
            self._advance(s)
            return True
        return False

    def expect(self, s):
        return self._expect(self.consume(s))

    def consume_re(self, re):
        m = re.match(self.s)
        if m:
            self.s = self.s[len(m.group(0)):]
            self._last = m
            self._advance(m.group(0))
            return m
        return None

    def expect_re(self, re):
        return self._expect(self.consume_re(re))

    def __enter__(self):
        self.backtrack_stack.append((self.s, self._pos))

    def __exit__(self, type, value, traceback):
        if type is None:
            self.backtrack_stack.pop()
        else:
            self.s, self._pos = self.backtrack_stack.pop()
        return type == TomlError

    def commit(self):
        self.backtrack_stack[-1] = (self.s, self._pos)

    def _expect(self, r):
        if not r:
            raise TomlError('msg', self._pos[0], self._pos[1], self._filename)
        return r

    def _advance(self, s):
        suffix_pos = s.rfind('\n')
        if suffix_pos == -1:
            self._pos = (self._pos[0], self._pos[1] + len(s))
        else:
            self._pos = (self._pos[0] + s.count('\n'), len(s) - suffix_pos)

_ews_re = re.compile(r'(?:[ \t]|#[^\n]*\n|#[^\n]*\Z|\n)*')
def _p_ews(s):
    s.expect_re(_ews_re)

_ws_re = re.compile(r'[ \t]*')
def _p_ws(s):
    s.expect_re(_ws_re)

_escapes = { 'b': '\b', 'n': '\n', 'r': '\r', 't': '\t', '"': '"',
    '\\': '\\', 'f': '\f' }

_basicstr_re = re.compile(r'[^"\\\000-\037]*')
_short_uni_re = re.compile(r'u([0-9a-fA-F]{4})')
_long_uni_re = re.compile(r'U([0-9a-fA-F]{8})')
_escapes_re = re.compile(r'[btnfr\"\\]')
_newline_esc_re = re.compile('\n[ \t\n]*')
def _p_basicstr_content(s, content=_basicstr_re):
    res = []
    while True:
        res.append(s.expect_re(content).group(0))
        if not s.consume('\\'):
            break
        if s.consume_re(_newline_esc_re):
            pass
        elif s.consume_re(_short_uni_re) or s.consume_re(_long_uni_re):
            v = int(s.last().group(1), 16)
            if 0xd800 <= v < 0xe000:
                s.fail()
            res.append(_chr(v))
        else:
            s.expect_re(_escapes_re)
            res.append(_escapes[s.last().group(0)])
    return ''.join(res)

_key_re = re.compile(r'[0-9a-zA-Z-_]+')
def _p_key(s):
    with s:
        s.expect('"')
        r = _p_basicstr_content(s, _basicstr_re)
        s.expect('"')
        return r
    if s.consume('\''):
        if s.consume('\'\''):
            r = s.expect_re(_litstr_ml_re).group(0)
            s.expect('\'\'\'')
        else:
            r = s.expect_re(_litstr_re).group(0)
            s.expect('\'')
        return r
    return s.expect_re(_key_re).group(0)

_float_re = re.compile(r'[+-]?(?:0|[1-9](?:_?\d)*)(?:\.\d(?:_?\d)*)?(?:[eE][+-]?(?:\d(?:_?\d)*))?')

_basicstr_ml_re = re.compile(r'(?:""?(?!")|[^"\\\000-\011\013-\037])*')
_litstr_re = re.compile(r"[^'\000\010\012-\037]*")
_litstr_ml_re = re.compile(r"(?:(?:|'|'')(?:[^'\000-\010\013-\037]))*")
def _p_value(s, object_pairs_hook):
    pos = s.pos()

    if s.consume('true'):
        return 'bool', s.last(), True, pos
    if s.consume('false'):
        return 'bool', s.last(), False, pos

    if s.consume('"'):
        if s.consume('""'):
            r = _p_basicstr_content(s, _basicstr_ml_re)
            s.expect('"""')
        else:
            r = _p_basicstr_content(s, _basicstr_re)
            s.expect('"')
        return 'str', r, r, pos

    if s.consume('\''):
        if s.consume('\'\''):
            r = s.expect_re(_litstr_ml_re).group(0)
            s.expect('\'\'\'')
        else:
            r = s.expect_re(_litstr_re).group(0)
            s.expect('\'')
        return 'str', r, r, pos

    if s.consume_re(rfc3339_re):
        m = s.last()
        return 'datetime', m.group(0), parse_rfc3339_re(m), pos

    if s.consume_re(_float_re):
        m = s.last().group(0)
        r = m.replace('_','')
        if '.' in m or 'e' in m or 'E' in m:
            return 'float', m, float(r), pos
        else:
            return 'int', m, int(r, 10), pos

    if s.consume('['):
        items = []
        with s:
            while True:
                _p_ews(s)
                items.append(_p_value(s, object_pairs_hook=object_pairs_hook))
                s.commit()
                _p_ews(s)
                s.expect(',')
                s.commit()
        _p_ews(s)
        s.expect(']')
        return 'array', None, items, pos

    if s.consume('{'):
        _p_ws(s)
        items = object_pairs_hook()
        if not s.consume('}'):
            k = _p_key(s)
            _p_ws(s)
            s.expect('=')
            _p_ws(s)
            items[k] = _p_value(s, object_pairs_hook=object_pairs_hook)
            _p_ws(s)
            while s.consume(','):
                _p_ws(s)
                k = _p_key(s)
                _p_ws(s)
                s.expect('=')
                _p_ws(s)
                items[k] = _p_value(s, object_pairs_hook=object_pairs_hook)
                _p_ws(s)
            s.expect('}')
        return 'table', None, items, pos

    s.fail()

def _p_stmt(s, object_pairs_hook):
    pos = s.pos()
    if s.consume(   '['):
        is_array = s.consume('[')
        _p_ws(s)
        keys = [_p_key(s)]
        _p_ws(s)
        while s.consume('.'):
            _p_ws(s)
            keys.append(_p_key(s))
            _p_ws(s)
        s.expect(']')
        if is_array:
            s.expect(']')
        return 'table_array' if is_array else 'table', keys, pos

    key = _p_key(s)
    _p_ws(s)
    s.expect('=')
    _p_ws(s)
    value = _p_value(s, object_pairs_hook=object_pairs_hook)
    return 'kv', (key, value), pos

_stmtsep_re = re.compile(r'(?:[ \t]*(?:#[^\n]*)?\n)+[ \t]*')
def _p_toml(s, object_pairs_hook):
    stmts = []
    _p_ews(s)
    with s:
        stmts.append(_p_stmt(s, object_pairs_hook=object_pairs_hook))
        while True:
            s.commit()
            s.expect_re(_stmtsep_re)
            stmts.append(_p_stmt(s, object_pairs_hook=object_pairs_hook))
    _p_ews(s)
    s.expect_eof()
    return stmts
