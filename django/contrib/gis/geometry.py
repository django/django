import re

# Regular expression for recognizing HEXEWKB and WKT.  A prophylactic measure
# to prevent potentially malicious input from reaching the underlying C
# library.  Not a substitute for good Web security programming practices.
hex_regex = re.compile(r'^[0-9A-F]+$', re.I)
wkt_regex = re.compile(r'^(SRID=(?P<srid>\-?[0-9]+);)?'
                       r'(?P<wkt>'
                       r'(?P<type>POINT|LINESTRING|LINEARRING|POLYGON|MULTIPOINT|'
                       r'MULTILINESTRING|MULTIPOLYGON|GEOMETRYCOLLECTION)'
                       r'[ACEGIMLONPSRUTYZ[0-9],\.\-\+\(\) ]+)$',
                       re.I)
json_regex = re.compile(r'^(\s+)?\{.*}(\s+)?$', re.DOTALL)
