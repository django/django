from django.contrib.gis.gdal.error import OGRException

#### OGRGeomType ####
class OGRGeomType(object):
    "Encapulates OGR Geometry Types."

    # Dictionary of acceptable OGRwkbGeometryType s and their string names.
    _types = {0 : 'Unknown',
              1 : 'Point',
              2 : 'LineString',
              3 : 'Polygon',
              4 : 'MultiPoint',
              5 : 'MultiLineString',
              6 : 'MultiPolygon',
              7 : 'GeometryCollection',
              100 : 'None',
              101 : 'LinearRing',
              }
    # Reverse type dictionary, keyed by lower-case of the name.
    _str_types = dict([(v.lower(), k) for k, v in _types.items()])

    def __init__(self, type_input):
        "Figures out the correct OGR Type based upon the input."
        if isinstance(type_input, OGRGeomType):
            num = type_input.num
        elif isinstance(type_input, basestring):
            type_input = type_input.lower()
            if type_input == 'geometry': type_input='unknown'
            num = self._str_types.get(type_input, None)
            if num is None:
                raise OGRException('Invalid OGR String Type "%s"' % type_input)
        elif isinstance(type_input, int):
            if not type_input in self._types:
                raise OGRException('Invalid OGR Integer Type: %d' % type_input)
            num = type_input
        else:
            raise TypeError('Invalid OGR input type given.')
        
        # Setting the OGR geometry type number.
        self.num = num

    def __str__(self):
        "Returns the value of the name property."
        return self.name

    def __eq__(self, other):
        """
        Does an equivalence test on the OGR type with the given
        other OGRGeomType, the short-hand string, or the integer.
        """
        if isinstance(other, OGRGeomType):
            return self.num == other.num
        elif isinstance(other, basestring):
            return self.name.lower() == other.lower()
        elif isinstance(other, int):
            return self.num == other
        else:
            return False

    def __ne__(self, other):
        return not (self == other)

    @property
    def name(self):
        "Returns a short-hand string form of the OGR Geometry type."
        return self._types[self.num]

    @property
    def django(self):
        "Returns the Django GeometryField for this OGR Type."
        s = self.name
        if s in ('LinearRing', 'None'):
            return None
        elif s == 'Unknown':
            s = 'Geometry'
        return s + 'Field'
