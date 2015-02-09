class BaseSpatialOperations(object):
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
    centroid = False
    difference = False
    distance = False
    distance_sphere = False
    distance_spheroid = False
    envelope = False
    force_rhr = False
    mem_size = False
    bounding_circle = False
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

    def convert_geom(self, geom_val, geom_field):
        raise NotImplementedError('Aggregate method not implemented for this spatial backend.')

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
        super(BaseSpatialOperations, self).check_expression_support(expression)

    def spatial_aggregate_name(self, agg_name):
        raise NotImplementedError('Aggregate support not implemented for this spatial backend.')

    # Routines for getting the OGC-compliant models.
    def geometry_columns(self):
        raise NotImplementedError('subclasses of BaseSpatialOperations must a provide geometry_columns() method')

    def spatial_ref_sys(self):
        raise NotImplementedError('subclasses of BaseSpatialOperations must a provide spatial_ref_sys() method')
