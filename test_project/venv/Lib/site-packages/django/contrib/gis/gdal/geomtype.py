from django.contrib.gis.gdal.error import GDALException


class OGRGeomType:
    "Encapsulate OGR Geometry Types."

    wkb25bit = -2147483648

    # Dictionary of acceptable OGRwkbGeometryType s and their string names.
    _types = {
        0: "Unknown",
        1: "Point",
        2: "LineString",
        3: "Polygon",
        4: "MultiPoint",
        5: "MultiLineString",
        6: "MultiPolygon",
        7: "GeometryCollection",
        8: "CircularString",
        9: "CompoundCurve",
        10: "CurvePolygon",
        11: "MultiCurve",
        12: "MultiSurface",
        15: "PolyhedralSurface",
        16: "TIN",
        17: "Triangle",
        100: "None",
        101: "LinearRing",
        102: "PointZ",
        1008: "CircularStringZ",
        1009: "CompoundCurveZ",
        1010: "CurvePolygonZ",
        1011: "MultiCurveZ",
        1012: "MultiSurfaceZ",
        1013: "CurveZ",
        1014: "SurfaceZ",
        1015: "PolyhedralSurfaceZ",
        1016: "TINZ",
        1017: "TriangleZ",
        2001: "PointM",
        2002: "LineStringM",
        2003: "PolygonM",
        2004: "MultiPointM",
        2005: "MultiLineStringM",
        2006: "MultiPolygonM",
        2007: "GeometryCollectionM",
        2008: "CircularStringM",
        2009: "CompoundCurveM",
        2010: "CurvePolygonM",
        2011: "MultiCurveM",
        2012: "MultiSurfaceM",
        2015: "PolyhedralSurfaceM",
        2016: "TINM",
        2017: "TriangleM",
        3001: "PointZM",
        3002: "LineStringZM",
        3003: "PolygonZM",
        3004: "MultiPointZM",
        3005: "MultiLineStringZM",
        3006: "MultiPolygonZM",
        3007: "GeometryCollectionZM",
        3008: "CircularStringZM",
        3009: "CompoundCurveZM",
        3010: "CurvePolygonZM",
        3011: "MultiCurveZM",
        3012: "MultiSurfaceZM",
        3015: "PolyhedralSurfaceZM",
        3016: "TINZM",
        3017: "TriangleZM",
        1 + wkb25bit: "Point25D",
        2 + wkb25bit: "LineString25D",
        3 + wkb25bit: "Polygon25D",
        4 + wkb25bit: "MultiPoint25D",
        5 + wkb25bit: "MultiLineString25D",
        6 + wkb25bit: "MultiPolygon25D",
        7 + wkb25bit: "GeometryCollection25D",
    }
    # Reverse type dictionary, keyed by lowercase of the name.
    _str_types = {v.lower(): k for k, v in _types.items()}

    def __init__(self, type_input):
        "Figure out the correct OGR Type based upon the input."
        if isinstance(type_input, OGRGeomType):
            num = type_input.num
        elif isinstance(type_input, str):
            type_input = type_input.lower()
            if type_input == "geometry":
                type_input = "unknown"
            num = self._str_types.get(type_input)
            if num is None:
                raise GDALException('Invalid OGR String Type "%s"' % type_input)
        elif isinstance(type_input, int):
            if type_input not in self._types:
                raise GDALException("Invalid OGR Integer Type: %d" % type_input)
            num = type_input
        else:
            raise TypeError("Invalid OGR input type given.")

        # Setting the OGR geometry type number.
        self.num = num

    def __str__(self):
        "Return the value of the name property."
        return self.name

    def __repr__(self):
        return f"<{self.__class__.__qualname__}: {self.name}>"

    def __eq__(self, other):
        """
        Do an equivalence test on the OGR type with the given
        other OGRGeomType, the short-hand string, or the integer.
        """
        if isinstance(other, OGRGeomType):
            return self.num == other.num
        elif isinstance(other, str):
            return self.name.lower() == other.lower()
        elif isinstance(other, int):
            return self.num == other
        else:
            return False

    @property
    def name(self):
        "Return a short-hand string form of the OGR Geometry type."
        return self._types[self.num]

    @property
    def django(self):
        "Return the Django GeometryField for this OGR Type."
        s = self.name.replace("25D", "")
        if s in ("LinearRing", "None"):
            return None
        elif s == "Unknown":
            s = "Geometry"
        elif s == "PointZ":
            s = "Point"
        return s + "Field"

    def to_multi(self):
        """
        Transform Point, LineString, Polygon, and their 25D equivalents
        to their Multi... counterpart.
        """
        if self.name.startswith(("Point", "LineString", "Polygon")):
            self.num += 3
