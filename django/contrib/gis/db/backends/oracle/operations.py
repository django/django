"""
 This module contains the spatial lookup types, and the `get_geo_where_clause`
 routine for Oracle Spatial.

 Please note that WKT support is broken on the XE version, and thus
 this backend will not work on such platforms.  Specifically, XE lacks
 support for an internal JVM, and Java libraries are required to use
 the WKT constructors.
"""
import re

from django.contrib.gis.db import models
from django.contrib.gis.db.backends.base.operations import BaseSpatialOperations
from django.contrib.gis.db.backends.oracle.adapter import OracleSpatialAdapter
from django.contrib.gis.db.backends.utils import SpatialOperator
from django.contrib.gis.geos.geometry import GEOSGeometry, GEOSGeometryBase
from django.contrib.gis.geos.prototypes.io import wkb_r
from django.contrib.gis.measure import Distance
from django.db.backends.oracle.operations import DatabaseOperations

DEFAULT_TOLERANCE = "0.05"


class SDOOperator(SpatialOperator):
    sql_template = "%(func)s(%(lhs)s, %(rhs)s) = 'TRUE'"


class SDODWithin(SpatialOperator):
    sql_template = "SDO_WITHIN_DISTANCE(%(lhs)s, %(rhs)s, %%s) = 'TRUE'"


class SDODisjoint(SpatialOperator):
    sql_template = (
        "SDO_GEOM.RELATE(%%(lhs)s, 'DISJOINT', %%(rhs)s, %s) = 'DISJOINT'"
        % DEFAULT_TOLERANCE
    )


class SDORelate(SpatialOperator):
    sql_template = "SDO_RELATE(%(lhs)s, %(rhs)s, 'mask=%(mask)s') = 'TRUE'"

    def check_relate_argument(self, arg):
        masks = (
            "TOUCH|OVERLAPBDYDISJOINT|OVERLAPBDYINTERSECT|EQUAL|INSIDE|COVEREDBY|"
            "CONTAINS|COVERS|ANYINTERACT|ON"
        )
        mask_regex = re.compile(r"^(%s)(\+(%s))*$" % (masks, masks), re.I)
        if not isinstance(arg, str) or not mask_regex.match(arg):
            raise ValueError('Invalid SDO_RELATE mask: "%s"' % arg)

    def as_sql(self, connection, lookup, template_params, sql_params):
        template_params["mask"] = sql_params[-1]
        return super().as_sql(connection, lookup, template_params, sql_params[:-1])


class OracleOperations(BaseSpatialOperations, DatabaseOperations):

    name = "oracle"
    oracle = True
    disallowed_aggregates = (models.Collect, models.Extent3D, models.MakeLine)

    Adapter = OracleSpatialAdapter

    extent = "SDO_AGGR_MBR"
    unionagg = "SDO_AGGR_UNION"

    from_text = "SDO_GEOMETRY"

    function_names = {
        "Area": "SDO_GEOM.SDO_AREA",
        "AsGeoJSON": "SDO_UTIL.TO_GEOJSON",
        "AsWKB": "SDO_UTIL.TO_WKBGEOMETRY",
        "AsWKT": "SDO_UTIL.TO_WKTGEOMETRY",
        "BoundingCircle": "SDO_GEOM.SDO_MBC",
        "Centroid": "SDO_GEOM.SDO_CENTROID",
        "Difference": "SDO_GEOM.SDO_DIFFERENCE",
        "Distance": "SDO_GEOM.SDO_DISTANCE",
        "Envelope": "SDO_GEOM_MBR",
        "Intersection": "SDO_GEOM.SDO_INTERSECTION",
        "IsValid": "SDO_GEOM.VALIDATE_GEOMETRY_WITH_CONTEXT",
        "Length": "SDO_GEOM.SDO_LENGTH",
        "NumGeometries": "SDO_UTIL.GETNUMELEM",
        "NumPoints": "SDO_UTIL.GETNUMVERTICES",
        "Perimeter": "SDO_GEOM.SDO_LENGTH",
        "PointOnSurface": "SDO_GEOM.SDO_POINTONSURFACE",
        "Reverse": "SDO_UTIL.REVERSE_LINESTRING",
        "SymDifference": "SDO_GEOM.SDO_XOR",
        "Transform": "SDO_CS.TRANSFORM",
        "Union": "SDO_GEOM.SDO_UNION",
    }

    # We want to get SDO Geometries as WKT because it is much easier to
    # instantiate GEOS proxies from WKT than SDO_GEOMETRY(...) strings.
    # However, this adversely affects performance (i.e., Java is called
    # to convert to WKT on every query).  If someone wishes to write a
    # SDO_GEOMETRY(...) parser in Python, let me know =)
    select = "SDO_UTIL.TO_WKBGEOMETRY(%s)"

    gis_operators = {
        "contains": SDOOperator(func="SDO_CONTAINS"),
        "coveredby": SDOOperator(func="SDO_COVEREDBY"),
        "covers": SDOOperator(func="SDO_COVERS"),
        "disjoint": SDODisjoint(),
        "intersects": SDOOperator(
            func="SDO_OVERLAPBDYINTERSECT"
        ),  # TODO: Is this really the same as ST_Intersects()?
        "equals": SDOOperator(func="SDO_EQUAL"),
        "exact": SDOOperator(func="SDO_EQUAL"),
        "overlaps": SDOOperator(func="SDO_OVERLAPS"),
        "same_as": SDOOperator(func="SDO_EQUAL"),
        # Oracle uses a different syntax, e.g., 'mask=inside+touch'
        "relate": SDORelate(),
        "touches": SDOOperator(func="SDO_TOUCH"),
        "within": SDOOperator(func="SDO_INSIDE"),
        "dwithin": SDODWithin(),
    }

    unsupported_functions = {
        "AsKML",
        "AsSVG",
        "Azimuth",
        "ForcePolygonCW",
        "GeoHash",
        "GeometryDistance",
        "LineLocatePoint",
        "MakeValid",
        "MemSize",
        "Scale",
        "SnapToGrid",
        "Translate",
    }

    def geo_quote_name(self, name):
        return super().geo_quote_name(name).upper()

    def convert_extent(self, clob):
        if clob:
            # Generally, Oracle returns a polygon for the extent -- however,
            # it can return a single point if there's only one Point in the
            # table.
            ext_geom = GEOSGeometry(memoryview(clob.read()))
            gtype = str(ext_geom.geom_type)
            if gtype == "Polygon":
                # Construct the 4-tuple from the coordinates in the polygon.
                shell = ext_geom.shell
                ll, ur = shell[0][:2], shell[2][:2]
            elif gtype == "Point":
                ll = ext_geom.coords[:2]
                ur = ll
            else:
                raise Exception(
                    "Unexpected geometry type returned for extent: %s" % gtype
                )
            xmin, ymin = ll
            xmax, ymax = ur
            return (xmin, ymin, xmax, ymax)
        else:
            return None

    def geo_db_type(self, f):
        """
        Return the geometry database type for Oracle. Unlike other spatial
        backends, no stored procedure is necessary and it's the same for all
        geometry types.
        """
        return "MDSYS.SDO_GEOMETRY"

    def get_distance(self, f, value, lookup_type):
        """
        Return the distance parameters given the value and the lookup type.
        On Oracle, geometry columns with a geodetic coordinate system behave
        implicitly like a geography column, and thus meters will be used as
        the distance parameter on them.
        """
        if not value:
            return []
        value = value[0]
        if isinstance(value, Distance):
            if f.geodetic(self.connection):
                dist_param = value.m
            else:
                dist_param = getattr(
                    value, Distance.unit_attname(f.units_name(self.connection))
                )
        else:
            dist_param = value

        # dwithin lookups on Oracle require a special string parameter
        # that starts with "distance=".
        if lookup_type == "dwithin":
            dist_param = "distance=%s" % dist_param

        return [dist_param]

    def get_geom_placeholder(self, f, value, compiler):
        if value is None:
            return "NULL"
        return super().get_geom_placeholder(f, value, compiler)

    def spatial_aggregate_name(self, agg_name):
        """
        Return the spatial aggregate SQL name.
        """
        agg_name = "unionagg" if agg_name.lower() == "union" else agg_name.lower()
        return getattr(self, agg_name)

    # Routines for getting the OGC-compliant models.
    def geometry_columns(self):
        from django.contrib.gis.db.backends.oracle.models import OracleGeometryColumns

        return OracleGeometryColumns

    def spatial_ref_sys(self):
        from django.contrib.gis.db.backends.oracle.models import OracleSpatialRefSys

        return OracleSpatialRefSys

    def modify_insert_params(self, placeholder, params):
        """Drop out insert parameters for NULL placeholder. Needed for Oracle Spatial
        backend due to #10888.
        """
        if placeholder == "NULL":
            return []
        return super().modify_insert_params(placeholder, params)

    def get_geometry_converter(self, expression):
        read = wkb_r().read
        srid = expression.output_field.srid
        if srid == -1:
            srid = None
        geom_class = expression.output_field.geom_class

        def converter(value, expression, connection):
            if value is not None:
                geom = GEOSGeometryBase(read(memoryview(value.read())), geom_class)
                if srid:
                    geom.srid = srid
                return geom

        return converter

    def get_area_att_for_field(self, field):
        return "sq_m"
