from django.contrib.gis.gdal.error import OGRException

#### OGRGeomType ####
class OGRGeomType(object):
    "Encapulates OGR Geometry Types."

    # Ordered array of acceptable strings and their corresponding OGRwkbGeometryType
    __ogr_str = ['Unknown', 'Point', 'LineString', 'Polygon', 'MultiPoint',
                 'MultiLineString', 'MultiPolygon', 'GeometryCollection',
                 'LinearRing']
    __ogr_int = [0, 1, 2, 3, 4, 5, 6, 7, 101]

    def __init__(self, type_input):
        "Figures out the correct OGR Type based upon the input."
        if isinstance(type_input, OGRGeomType):
            self._index = type_input._index
        elif isinstance(type_input, basestring):
            idx = self._has_str(self.__ogr_str, type_input)
            if idx == None:
                raise OGRException('Invalid OGR String Type "%s"' % type_input)
            self._index = idx
        elif isinstance(type_input, int):
            if not type_input in self.__ogr_int:
                raise OGRException('Invalid OGR Integer Type: %d' % type_input)
            self._index =  self.__ogr_int.index(type_input)
        else:
            raise TypeError('Invalid OGR input type given.')

    def __str__(self):
        "Returns a short-hand string form of the OGR Geometry type."
        return self.__ogr_str[self._index]

    def __eq__(self, other):
        """
        Does an equivalence test on the OGR type with the given
        other OGRGeomType, the short-hand string, or the integer.
        """
        if isinstance(other, OGRGeomType):
            return self._index == other._index
        elif isinstance(other, basestring):
            idx = self._has_str(self.__ogr_str, other)
            if not (idx == None): return self._index == idx
            return False
        elif isinstance(other, int):
            if not other in self.__ogr_int: return False
            return self.__ogr_int.index(other) == self._index
        else:
            raise TypeError('Cannot compare with type: %s' % str(type(other)))

    def __ne__(self, other):
        return not (self == other)

    def _has_str(self, arr, s):
        "Case-insensitive search of the string array for the given pattern."
        s_low = s.lower()
        for i in xrange(len(arr)):
            if s_low == arr[i].lower(): return i
        return None

    @property
    def django(self):
        "Returns the Django GeometryField for this OGR Type."
        s = self.__ogr_str[self._index]
        if s in ('Unknown', 'LinearRing'):
            return None
        else:
            return s + 'Field'

    @property
    def num(self):
        "Returns the OGRwkbGeometryType number for the OGR Type."
        return self.__ogr_int[self._index]
