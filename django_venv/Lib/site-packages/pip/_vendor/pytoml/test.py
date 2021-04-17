import datetime
from .utils import format_rfc3339

try:
    _string_types = (str, unicode)
    _int_types = (int, long)
except NameError:
    _string_types = str
    _int_types = int

def translate_to_test(v):
    if isinstance(v, dict):
        return { k: translate_to_test(v) for k, v in v.items() }
    if isinstance(v, list):
        a = [translate_to_test(x) for x in v]
        if v and isinstance(v[0], dict):
            return a
        else:
            return {'type': 'array', 'value': a}
    if isinstance(v, datetime.datetime):
        return {'type': 'datetime', 'value': format_rfc3339(v)}
    if isinstance(v, bool):
        return {'type': 'bool', 'value': 'true' if v else 'false'}
    if isinstance(v, _int_types):
        return {'type': 'integer', 'value': str(v)}
    if isinstance(v, float):
        return {'type': 'float', 'value': '{:.17}'.format(v)}
    if isinstance(v, _string_types):
        return {'type': 'string', 'value': v}
    raise RuntimeError('unexpected value: {!r}'.format(v))
