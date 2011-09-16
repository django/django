import re

# Regular expression for recognizing HEXEWKB and WKT.  A prophylactic measure
# to prevent potentially malicious input from reaching the underlying C
# library.  Not a substitute for good Web security programming practices.
hex_regex = re.compile(r'^[0-9A-F]+$', re.I)
wkt_regex = re.compile(r'^(SRID=(?P<srid>\-?\d+);)?'
                       r'(?P<wkt>'
                       r'(?P<type>POINT|LINESTRING|LINEARRING|POLYGON|MULTIPOINT|MULTILINESTRING|MULTIPOLYGON|GEOMETRYCOLLECTION)'
                       r'[ACEGIMLONPSRUTYZ\d,\.\-\(\) ]+)$',
                       re.I)
json_regex = re.compile(r'^(\s+)?\{[\s\w,\[\]\{\}\-\."\':]+\}(\s+)?$')
