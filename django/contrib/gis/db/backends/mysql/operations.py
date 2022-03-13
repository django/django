from django.contrib.gis.db import models
from django.contrib.gis.db.backends.base.adapter import WKTAdapter
from django.contrib.gis.db.backends.base.operations import BaseSpatialOperations
from django.contrib.gis.db.backends.utils import SpatialOperator
from django.contrib.gis.geos.geometry import GEOSGeometryBase
from django.contrib.gis.geos.prototypes.io import wkb_r
from django.contrib.gis.measure import Distance
from django.db.backends.mysql.operations import DatabaseOperations
from django.utils.functional import cached_property


class MySQLOperations(BaseSpatialOperations, DatabaseOperations):
    name = "mysql"
    geom_func_prefix = "ST_"

    Adapter = WKTAdapter

    @cached_property
    def mariadb(self):
        return self.connection.mysql_is_mariadb

    @cached_property
    def mysql(self):
        return not self.connection.mysql_is_mariadb

    @cached_property
    def select(self):
        return self.geom_func_prefix + "AsBinary(%s)"

    @cached_property
    def from_text(self):
        return self.geom_func_prefix + "GeomFromText"

    @cached_property
    def gis_operators(self):
        operators = {
            "bbcontains": SpatialOperator(
                func="MBRContains"
            ),  # For consistency w/PostGIS API
            "bboverlaps": SpatialOperator(func="MBROverlaps"),  # ...
            "contained": SpatialOperator(func="MBRWithin"),  # ...
            "contains": SpatialOperator(func="ST_Contains"),
            "crosses": SpatialOperator(func="ST_Crosses"),
            "disjoint": SpatialOperator(func="ST_Disjoint"),
            "equals": SpatialOperator(func="ST_Equals"),
            "exact": SpatialOperator(func="ST_Equals"),
            "intersects": SpatialOperator(func="ST_Intersects"),
            "overlaps": SpatialOperator(func="ST_Overlaps"),
            "same_as": SpatialOperator(func="ST_Equals"),
            "touches": SpatialOperator(func="ST_Touches"),
            "within": SpatialOperator(func="ST_Within"),
        }
        if self.connection.mysql_is_mariadb:
            operators["relate"] = SpatialOperator(func="ST_Relate")
        return operators

    disallowed_aggregates = (
        models.Collect,
        models.Extent,
        models.Extent3D,
        models.MakeLine,
        models.Union,
    )

    @cached_property
    def unsupported_functions(self):
        unsupported = {
            "AsGML",
            "AsKML",
            "AsSVG",
            "Azimuth",
            "BoundingCircle",
            "ForcePolygonCW",
            "GeometryDistance",
            "LineLocatePoint",
            "MakeValid",
            "MemSize",
            "Perimeter",
            "PointOnSurface",
            "Reverse",
            "Scale",
            "SnapToGrid",
            "Transform",
            "Translate",
        }
        if self.connection.mysql_is_mariadb:
            unsupported.remove("PointOnSurface")
            unsupported.update({"GeoHash", "IsValid"})
        elif self.connection.mysql_version < (5, 7, 5):
            unsupported.update({"AsGeoJSON", "GeoHash", "IsValid"})
        return unsupported

    def geo_db_type(self, f):
        return f.geom_type

    def get_distance(self, f, value, lookup_type):
        value = value[0]
        if isinstance(value, Distance):
            if f.geodetic(self.connection):
                raise ValueError(
                    "Only numeric values of degree units are allowed on "
                    "geodetic distance queries."
                )
            dist_param = getattr(
                value, Distance.unit_attname(f.units_name(self.connection))
            )
        else:
            dist_param = value
        return [dist_param]

    def get_geometry_converter(self, expression):
        read = wkb_r().read
        srid = expression.output_field.srid
        if srid == -1:
            srid = None
        geom_class = expression.output_field.geom_class

        def converter(value, expression, connection):
            if value is not None:
                geom = GEOSGeometryBase(read(memoryview(value)), geom_class)
                if srid:
                    geom.srid = srid
                return geom

        return converter
