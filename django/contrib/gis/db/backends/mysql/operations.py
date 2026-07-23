from django.contrib.gis.db import models
from django.contrib.gis.db.backends.base.adapter import WKTAdapter
from django.contrib.gis.db.backends.base.operations import BaseSpatialOperations
from django.contrib.gis.db.backends.utils import SpatialOperator
from django.contrib.gis.geos.geometry import GEOSGeometryBase
from django.contrib.gis.geos.prototypes.io import wkb_r
from django.contrib.gis.measure import Distance
from django.db.backends.mysql.operations import DatabaseOperations
from django.utils.functional import cached_property

from .models import MySQLSpatialRefSys


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
    def collect(self):
        if self.connection.features.supports_collect_aggr:
            return self.geom_func_prefix + "Collect"

    @cached_property
    def gis_operators(self):
        operators = {
            "bbcontains": SpatialOperator(
                func="MBRContains"
            ),  # For consistency w/PostGIS API
            "bboverlaps": SpatialOperator(func="MBROverlaps"),  # ...
            "contained": SpatialOperator(func="MBRWithin"),  # ...
            "contains": SpatialOperator(func="ST_Contains"),
            "coveredby": SpatialOperator(func="MBRCoveredBy"),
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
            if self.connection.mysql_version < (12, 0, 1):
                del operators["coveredby"]
        else:
            operators["covers"] = SpatialOperator(func="MBRCovers")

        # Add MySQL 8.0 specific operators if available
        if (
            self.connection.mysql_version >= (8, 0)
            and not self.connection.mysql_is_mariadb
        ):
            # MySQL 8.0 adds support for additional spatial functions
            operators["distance"] = SpatialOperator(func="ST_Distance")
            operators["distance_sphere"] = SpatialOperator(func="ST_Distance_Sphere")

        return operators

    @cached_property
    def disallowed_aggregates(self):
        disallowed_aggregates = [
            models.Extent,
            models.Extent3D,
            models.MakeLine,
            models.Union,
        ]
        is_mariadb = self.connection.mysql_is_mariadb
        if is_mariadb:
            if self.connection.mysql_version < (12, 0, 1):
                disallowed_aggregates.insert(0, models.Collect)
        else:
            # For MySQL 8.0+, some aggregates become available
            if self.connection.mysql_version >= (8, 0):
                # MySQL 8.0 adds Collect support
                pass  # Remove from disallowed if needed

        return tuple(disallowed_aggregates)

    function_names = {
        "FromWKB": "ST_GeomFromWKB",
        "FromWKT": "ST_GeomFromText",
    }

    @cached_property
    def unsupported_functions(self):
        unsupported = {
            "AsGML",
            "AsKML",
            "AsSVG",
            "Azimuth",
            "BoundingCircle",
            "ClosestPoint",
            "ForcePolygonCW",
            "GeometryDistance",
            "IsEmpty",
            "LineLocatePoint",
            "MakeValid",
            "MemSize",
            "NumDimensions",
            "Perimeter",
            "PointOnSurface",
            "Reverse",
            "Rotate",
            "Scale",
            "SnapToGrid",
            "Transform",
            "Translate",
        }

        if self.connection.mysql_is_mariadb:
            unsupported.remove("PointOnSurface")
            if self.connection.mysql_version < (12, 0, 1):
                unsupported.update({"GeoHash", "IsValid"})
        else:
            # MySQL 8.0 adds support for some functions
            if self.connection.mysql_version >= (8, 0):
                # MySQL 8.0 adds these functions
                functions_added_in_8_0 = {
                    "IsEmpty",  # Added in MySQL 8.0
                    "PointOnSurface",  # Added in MySQL 8.0
                }
                unsupported -= functions_added_in_8_0

                # MySQL 8.0.1 adds more
                if self.connection.mysql_version >= (8, 0, 1):
                    unsupported -= {"GeoHash"}  # Added in MySQL 8.0.1

        return unsupported

    @cached_property
    def spatial_ref_sys(self):
        """
        Return the spatial reference system model class for this backend.
        """
        if (
            self.connection.mysql_version >= (8, 0)
            and not self.connection.mysql_is_mariadb
        ):
            return MySQLSpatialRefSys

        # Create a dummy class that matches the real model's API
        class DummySpatialRefSys:
            """Dummy class for databases without spatial_ref_sys table."""

            class DoesNotExist(Exception):
                """Raised when a spatial ref sys is not found."""

                pass

            class MultipleObjectsReturned(Exception):
                """Raised when multiple spatial ref sys are returned."""

                pass

            class Meta:
                """Dummy Meta class for the dummy model."""

                app_label = "gis"
                managed = False

                @staticmethod
                def get_fields():
                    """Return empty fields list."""
                    return []

            _meta = Meta()

            # Define fields that tests might access
            srid = None
            srtext = ""
            auth_name = ""
            auth_srid = None
            proj4text = ""
            wkt = ""
            organization = ""
            organization_coordsys_id = None
            definition = ""
            description = ""

            def __new__(cls, *args, **kwargs):
                """Allow instantiation of the class."""
                return super().__new__(cls)

            def __init__(self, *args, **kwargs):
                """Initialize dummy spatial ref sys with default values."""
                self.srid = kwargs.get("srid", 4326)
                self.srtext = kwargs.get("srtext", "")
                self.auth_name = kwargs.get("auth_name", "")
                self.auth_srid = kwargs.get("auth_srid", None)
                self.proj4text = kwargs.get(
                    "proj4text", "+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs"
                )
                self.wkt = kwargs.get(
                    "wkt",
                    'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,'
                    '298.257223563]],PRIMEM["Greenwich",0],UNIT["degree",'
                    "0.0174532925199433]]",
                )
                self.organization = kwargs.get("organization", "EPSG")
                self.organization_coordsys_id = self.srid
                self.definition = self.wkt
                self.description = kwargs.get("description", "")

            class objects:
                """Dummy manager for the dummy model."""

                def __init__(self):
                    self.model = DummySpatialRefSys

                def using(self, database):
                    """Support the using() method for multi-db queries."""
                    return self

                def get(self, **kwargs):
                    """Raise DoesNotExist for any get query."""
                    raise DummySpatialRefSys.DoesNotExist(
                        "Spatial reference systems are not available for this "
                        "database. MySQL 8.0+ with InnoDB is required."
                    )

                def filter(self, **kwargs):
                    """Return empty list for any filter query."""
                    return []

                def all(self):
                    """Return empty list for all query."""
                    return []

                def count(self):
                    """Return zero count."""
                    return 0

                def get_queryset(self):
                    """Return empty list for queryset."""
                    return []

            @property
            def srs_id(self):
                """Return SRID value."""
                return self.srid

            def get_units(self, wkt=None):
                """Return units for this SRS."""
                from django.contrib.gis.measure import D

                return D["m"], "meter"

            def get_ellipsoid(self, wkt=None):
                """Return ellipsoid parameters."""
                return (6378137.0, 6356752.3142)  # WGS84 ellipsoid

            def get_srid(self, wkt):
                """Return SRID from WKT."""
                return 4326

            def __str__(self):
                """String representation."""
                return f"DummySpatialRefSys (SRID: {self.srid})"

        return DummySpatialRefSys

    def geo_db_type(self, f):
        # MySQL 8.0 supports SRID constraint in column definition
        if (
            self.connection.mysql_version >= (8, 0)
            and not self.connection.mysql_is_mariadb
        ):
            if f.srid:
                return f"{f.geom_type} SRID {f.srid}"
        return f.geom_type

    def get_distance(self, f, value, lookup_type):
        value = value[0]
        if isinstance(value, Distance):
            if f.geodetic(self.connection):
                # For MySQL 8.0, we can use ST_Distance_Sphere for geodetic
                if (
                    self.connection.mysql_version >= (8, 0)
                    and not self.connection.mysql_is_mariadb
                ):
                    # Convert distance to meters for ST_Distance_Sphere
                    dist_param = value.m
                else:
                    raise ValueError(
                        "Only numeric values of degree units are allowed on "
                        "geodetic distance queries."
                    )
            else:
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
                # MySQL 8.0 returns geometry as WKB
                geom = GEOSGeometryBase(read(memoryview(value)), geom_class)
                if srid:
                    geom.srid = srid
                return geom

        return converter

    def spatial_aggregate_name(self, agg_name):
        return getattr(self, agg_name.lower())

    def get_function(self, func_name):
        """
        Return MySQL 8.0 function name for a GeoDjango function.
        Override to handle MySQL 8.0 specific function names.
        """
        if (
            self.connection.mysql_version >= (8, 0)
            and not self.connection.mysql_is_mariadb
        ):
            # MySQL 8.0 function name overrides
            mysql_8_funcs = {
                "Distance": "ST_Distance",
                "DistanceSphere": "ST_Distance_Sphere",
                "IsValid": "ST_IsValid",
                "MakeValid": "ST_MakeValid",  # Actually ST_Validate in MySQL 8.0?
                "GeoHash": "ST_GeoHash",
            }
            if func_name in mysql_8_funcs:
                return mysql_8_funcs[func_name]

        # Fall back to default
        return super().get_function(func_name)
