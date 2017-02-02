class BaseSpatialOperations:
    """
    This module holds the base `BaseSpatialBackend` object, which is
    instantiated by each spatial database backend with the features
    it has.
    """
    truncate_params = {}

    # Quick booleans for the type of this spatial backend, and
    # an attribute for the spatial database version tuple (if applicable)
    postgis = False
    spatialite = False
    mysql = False
    oracle = False
    spatial_version = None

    # How the geometry column should be selected.
    select = None

    # Does the spatial database have a geometry or geography type?
    geography = False
    geometry = False

    area = False
    bounding_circle = False
    centroid = False
    difference = False
    distance = False
    distance_sphere = False
    distance_spheroid = False
    envelope = False
    force_rhr = False
    mem_size = False
    num_geom = False
    num_points = False
    perimeter = False
    perimeter3d = False
    point_on_surface = False
    polygonize = False
    reverse = False
    scale = False
    snap_to_grid = False
    sym_difference = False
    transform = False
    translate = False
    union = False

    # Aggregates
    disallowed_aggregates = ()

    geom_func_prefix = ''

    # Mapping between Django function names and backend names, when names do not
    # match; used in spatial_function_name().
    function_names = {}

    # Blacklist/set of known unsupported functions of the backend
    unsupported_functions = {
        'Area', 'AsGeoJSON', 'AsGML', 'AsKML', 'AsSVG',
        'BoundingCircle', 'Centroid', 'Difference', 'Distance', 'Envelope',
        'ForceRHR', 'GeoHash', 'Intersection', 'IsValid', 'Length', 'MakeValid',
        'MemSize', 'NumGeometries', 'NumPoints', 'Perimeter', 'PointOnSurface',
        'Reverse', 'Scale', 'SnapToGrid', 'SymDifference', 'Transform',
        'Translate', 'Union',
    }

    # Serialization
    geohash = False
    geojson = False
    gml = False
    kml = False
    svg = False

    # Constructors
    from_text = False
    from_wkb = False

    # Default conversion functions for aggregates; will be overridden if implemented
    # for the spatial backend.
    def convert_extent(self, box, srid):
        raise NotImplementedError('Aggregate extent not implemented for this spatial backend.')

    def convert_extent3d(self, box, srid):
        raise NotImplementedError('Aggregate 3D extent not implemented for this spatial backend.')

    # For quoting column values, rather than columns.
    def geo_quote_name(self, name):
        return "'%s'" % name

    # GeometryField operations
    def geo_db_type(self, f):
        """
        Returns the database column type for the geometry field on
        the spatial backend.
        """
        raise NotImplementedError('subclasses of BaseSpatialOperations must provide a geo_db_type() method')

    def get_distance(self, f, value, lookup_type):
        """
        Returns the distance parameters for the given geometry field,
        lookup value, and lookup type.
        """
        raise NotImplementedError('Distance operations not available on this spatial backend.')

    def get_geom_placeholder(self, f, value, compiler):
        """
        Returns the placeholder for the given geometry field with the given
        value.  Depending on the spatial backend, the placeholder may contain a
        stored procedure call to the transformation function of the spatial
        backend.
        """
        raise NotImplementedError('subclasses of BaseSpatialOperations must provide a geo_db_placeholder() method')

    def check_expression_support(self, expression):
        if isinstance(expression, self.disallowed_aggregates):
            raise NotImplementedError(
                "%s spatial aggregation is not supported by this database backend." % expression.name
            )
        super().check_expression_support(expression)

    def spatial_aggregate_name(self, agg_name):
        raise NotImplementedError('Aggregate support not implemented for this spatial backend.')

    def spatial_function_name(self, func_name):
        if func_name in self.unsupported_functions:
            raise NotImplementedError("This backend doesn't support the %s function." % func_name)
        return self.function_names.get(func_name, self.geom_func_prefix + func_name)

    # Routines for getting the OGC-compliant models.
    def geometry_columns(self):
        raise NotImplementedError('Subclasses of BaseSpatialOperations must provide a geometry_columns() method.')

    def spatial_ref_sys(self):
        raise NotImplementedError('subclasses of BaseSpatialOperations must a provide spatial_ref_sys() method')
