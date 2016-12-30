import re
from functools import partial

from django.contrib.gis.db.models import aggregates


class BaseSpatialFeatures(object):
    gis_enabled = True

    # Does the database contain a SpatialRefSys model to store SRID information?
    has_spatialrefsys_table = True

    # Does the backend support the django.contrib.gis.utils.add_srs_entry() utility?
    supports_add_srs_entry = True
    # Does the backend introspect GeometryField to its subtypes?
    supports_geometry_field_introspection = True

    # Does the backend support storing 3D geometries?
    supports_3d_storage = False
    # Reference implementation of 3D functions is:
    # http://postgis.net/docs/PostGIS_Special_Functions_Index.html#PostGIS_3D_Functions
    supports_3d_functions = False
    # Does the database support SRID transform operations?
    supports_transform = True
    # Do geometric relationship operations operate on real shapes (or only on bounding boxes)?
    supports_real_shape_operations = True
    # Can geometry fields be null?
    supports_null_geometries = True
    # Are empty geometries supported?
    supports_empty_geometries = False
    # Can the the function be applied on geodetic coordinate systems?
    supports_distance_geodetic = True
    supports_length_geodetic = True
    supports_perimeter_geodetic = False
    supports_area_geodetic = True
    # Is the database able to count vertices on polygons (with `num_points`)?
    supports_num_points_poly = True

    # The following properties indicate if the database backend support
    # certain lookups (dwithin, left and right, relate, ...)
    supports_distances_lookups = True
    supports_left_right_lookups = False

    # Does the database have raster support?
    supports_raster = False

    # Does the database support a unique index on geometry fields?
    supports_geometry_field_unique_index = True

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
    def supports_dwithin_lookup(self):
        return 'dwithin' in self.connection.ops.gis_operators

    @property
    def supports_relate_lookup(self):
        return 'relate' in self.connection.ops.gis_operators

    @property
    def supports_isvalid_lookup(self):
        return 'isvalid' in self.connection.ops.gis_operators

    # For each of those methods, the class will have a property named
    # `has_<name>_method` (defined in __init__) which accesses connection.ops
    # to determine GIS method availability.
    geoqueryset_methods = (
        'area', 'bounding_circle', 'centroid', 'difference', 'distance',
        'distance_spheroid', 'envelope', 'force_rhr', 'geohash', 'gml',
        'intersection', 'kml', 'length', 'mem_size', 'num_geom', 'num_points',
        'perimeter', 'point_on_surface', 'reverse', 'scale', 'snap_to_grid',
        'svg', 'sym_difference', 'transform', 'translate', 'union', 'unionagg',
    )

    # Is the aggregate supported by the database?
    @property
    def supports_collect_aggr(self):
        return aggregates.Collect not in self.connection.ops.disallowed_aggregates

    @property
    def supports_extent_aggr(self):
        return aggregates.Extent not in self.connection.ops.disallowed_aggregates

    @property
    def supports_make_line_aggr(self):
        return aggregates.MakeLine not in self.connection.ops.disallowed_aggregates

    @property
    def supports_union_aggr(self):
        return aggregates.Union not in self.connection.ops.disallowed_aggregates

    def __init__(self, *args):
        super(BaseSpatialFeatures, self).__init__(*args)
        for method in self.geoqueryset_methods:
            # Add dynamically properties for each GQS method, e.g. has_force_rhr_method, etc.
            setattr(self.__class__, 'has_%s_method' % method,
                    property(partial(BaseSpatialFeatures.has_ops_method, method=method)))

    def __getattr__(self, name):
        m = re.match(r'has_(\w*)_function$', name)
        if m:
            func_name = m.group(1)
            return func_name not in self.connection.ops.unsupported_functions
        raise AttributeError

    def has_ops_method(self, method):
        return getattr(self.connection.ops, method, False)
