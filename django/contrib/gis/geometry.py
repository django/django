import re

from django.utils.regex_helper import _lazy_re_compile

# Regular expression for recognizing HEXEWKB and WKT. A prophylactic measure
# to prevent potentially malicious input from reaching the underlying C
# library. Not a substitute for good web security programming practices.
hex_regex = _lazy_re_compile(r"^[0-9A-F]+$", re.I)
wkt_regex = _lazy_re_compile(
    r"^(SRID=(?P<srid>\-?[0-9]+);)?"
    r"(?P<wkt>"
    r"(?P<type>POINT|LINESTRING|LINEARRING|POLYGON|MULTIPOINT|"
    r"MULTILINESTRING|MULTIPOLYGON|GEOMETRYCOLLECTION|CIRCULARSTRING|COMPOUNDCURVE|"
    r"CURVEPOLYGON|MULTICURVE|MULTISURFACE|CURVE|SURFACE|POLYHEDRALSURFACE|TIN|"
    r"TRIANGLE)"
    r"[ACEGIMLONPSRUTYZ0-9,.+() -]+)$",
    re.I,
)
json_regex = _lazy_re_compile(r"^(\s+)?\{.*}(\s+)?$", re.DOTALL)
