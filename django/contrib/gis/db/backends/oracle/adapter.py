from cx_Oracle import CLOB

from django.contrib.gis.db.backends.base.adapter import WKTAdapter
from django.contrib.gis.geos import GeometryCollection, Polygon


class OracleSpatialAdapter(WKTAdapter):
    input_size = CLOB

    def __init__(self, geom):
        """
        Oracle requires that polygon rings are in proper orientation. This
        affects spatial operations and an invalid orientation may cause
        failures. Correct orientations are:
         * Outer ring - counter clockwise
         * Inner ring(s) - clockwise
        """
        if isinstance(geom, Polygon):
            self._fix_polygon(geom)
        elif isinstance(geom, GeometryCollection):
            self._fix_geometry_collection(geom)

        self.wkt = geom.wkt
        self.srid = geom.srid

    def _fix_polygon(self, poly):
        """Fix single polygon orientation as described in __init__()."""
        if poly.empty:
            return poly
        if not poly.exterior_ring.is_counterclockwise:
            poly.exterior_ring = list(reversed(poly.exterior_ring))

        for i in range(1, len(poly)):
            if poly[i].is_counterclockwise:
                poly[i] = list(reversed(poly[i]))

        return poly

    def _fix_geometry_collection(self, coll):
        """
        Fix polygon orientations in geometry collections as described in
        __init__().
        """
        for i, geom in enumerate(coll):
            if isinstance(geom, Polygon):
                coll[i] = self._fix_polygon(geom)
