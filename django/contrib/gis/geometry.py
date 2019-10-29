import re

from django.utils.regex_helper import _lazy_re_compile

# Regular expression for recognizing HEXEWKB and WKT.  A prophylactic measure
# to prevent potentially malicious input from reaching the underlying C
# library.  Not a substitute for good Web security programming practices.
hex_regex = _lazy_re_compile(r'^[0-9A-F]+$', re.I)
wkt_regex = _lazy_re_compile(
    r'^(SRID=(?P<srid>\-?\d+);)?'
    r'(?P<wkt>'
    r'(?P<type>POINT|LINESTRING|LINEARRING|POLYGON|MULTIPOINT|'
    r'MULTILINESTRING|MULTIPOLYGON|GEOMETRYCOLLECTION)'
    r'[ACEGIMLONPSRUTYZ\d,\.\-\+\(\) ]+)$',
    re.I
)
json_regex = _lazy_re_compile(r'^(\s+)?\{.*}(\s+)?$', re.DOTALL)
