import re

from django.contrib.gis.db import models


class BaseSpatialFeatures:
    gis_enabled = True

    # Does the database contain a SpatialRefSys model to store SRID information?
    has_spatialrefsys_table = True

    # Does the backend support the django.contrib.gis.utils.add_srs_entry() utility?
    supports_add_srs_entry = True
    # Does the backend introspect GeometryField to its subtypes?
    supports_geometry_field_introspection = True

    # Does the database have a geography type?
    supports_geography = False
    # Does the backend support storing 3D geometries?
    supports_3d_storage = False
    # Reference implementation of 3D functions is:
    # https://postgis.net/docs/PostGIS_Special_Functions_Index.html#PostGIS_3D_Functions
    supports_3d_functions = False
    # Does the database support SRID transform operations?
    supports_transform = True
    # Can geometry fields be null?
    supports_null_geometries = True
    # Are empty geometries supported?
    supports_empty_geometries = False
    # Can the function be applied on geodetic coordinate systems?
    supports_distance_geodetic = True
    supports_length_geodetic = True
    supports_perimeter_geodetic = False
    supports_area_geodetic = True
    # Is the database able to count vertices on polygons (with `num_points`)?
    supports_num_points_poly = True

    # Does the backend support expressions for specifying distance in the
    # dwithin lookup?
    supports_dwithin_distance_expr = True

    # Does the database have raster support?
    supports_raster = False

    # Does the database support a unique index on geometry fields?
    supports_geometry_field_unique_index = True

    # Can SchemaEditor alter geometry fields?
    can_alter_geometry_field = True

    # Do the database functions/aggregates support the tolerance parameter?
    supports_tolerance_parameter = False

    # Set of options that AsGeoJSON() doesn't support.
    unsupported_geojson_options = {}

    # Does Intersection() return None (rather than an empty GeometryCollection)
    # for empty results?
    empty_intersection_returns_none = True

    @property
    def supports_bbcontains_lookup(self):
        return 'bbcontains' in self.connection.ops.gis_operators

    @property
    def supports_contained_lookup(self):
        return 'contained' in self.connection.ops.gis_operators

    @property
    def supports_crosses_lookup(self):
        return 'crosses' in self.connection.ops.gis_operators

    @property
    def supports_distances_lookups(self):
        return self.has_Distance_function

    @property
    def supports_dwithin_lookup(self):
        return 'dwithin' in self.connection.ops.gis_operators

    @property
    def supports_relate_lookup(self):
        return 'relate' in self.connection.ops.gis_operators

    @property
    def supports_isvalid_lookup(self):
        return self.has_IsValid_function

    # Is the aggregate supported by the database?
    @property
    def supports_collect_aggr(self):
        return models.Collect not in self.connection.ops.disallowed_aggregates

    @property
    def supports_extent_aggr(self):
        return models.Extent not in self.connection.ops.disallowed_aggregates

    @property
    def supports_make_line_aggr(self):
        return models.MakeLine not in self.connection.ops.disallowed_aggregates

    @property
    def supports_union_aggr(self):
        return models.Union not in self.connection.ops.disallowed_aggregates

    def __getattr__(self, name):
        m = re.match(r'has_(\w*)_function$', name)
        if m:
            func_name = m[1]
            return func_name not in self.connection.ops.unsupported_functions
        raise AttributeError
