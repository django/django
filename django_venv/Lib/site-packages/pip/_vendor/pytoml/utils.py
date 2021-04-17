import datetime
import re

rfc3339_re = re.compile(r'(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(\.\d+)?(?:Z|([+-]\d{2}):(\d{2}))')

def parse_rfc3339(v):
    m = rfc3339_re.match(v)
    if not m or m.group(0) != v:
        return None
    return parse_rfc3339_re(m)

def parse_rfc3339_re(m):
    r = map(int, m.groups()[:6])
    if m.group(7):
        micro = float(m.group(7))
    else:
        micro = 0

    if m.group(8):
        g = int(m.group(8), 10) * 60 + int(m.group(9), 10)
        tz = _TimeZone(datetime.timedelta(0, g * 60))
    else:
        tz = _TimeZone(datetime.timedelta(0, 0))

    y, m, d, H, M, S = r
    return datetime.datetime(y, m, d, H, M, S, int(micro * 1000000), tz)


def format_rfc3339(v):
    offs = v.utcoffset()
    offs = int(offs.total_seconds()) // 60 if offs is not None else 0

    if offs == 0:
        suffix = 'Z'
    else:
        if offs > 0:
            suffix = '+'
        else:
            suffix = '-'
            offs = -offs
        suffix = '{0}{1:02}:{2:02}'.format(suffix, offs // 60, offs % 60)

    if v.microsecond:
        return v.strftime('%Y-%m-%dT%H:%M:%S.%f') + suffix
    else:
        return v.strftime('%Y-%m-%dT%H:%M:%S') + suffix

class _TimeZone(datetime.tzinfo):
    def __init__(self, offset):
        self._offset = offset

    def utcoffset(self, dt):
        return self._offset

    def dst(self, dt):
        return None

    def tzname(self, dt):
        m = self._offset.total_seconds() // 60
        if m < 0:
            res = '-'
            m = -m
        else:
            res = '+'
        h = m // 60
        m = m - h * 60
        return '{}{:.02}{:.02}'.format(res, h, m)
