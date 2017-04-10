class BaseSpatialOperations:
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

    # Aggregates
    disallowed_aggregates = ()

    geom_func_prefix = ''

    # Mapping between Django function names and backend names, when names do not
    # match; used in spatial_function_name().
    function_names = {}

    # Blacklist/set of known unsupported functions of the backend
    unsupported_functions = {
        'Area', 'AsGeoJSON', 'AsGML', 'AsKML', 'AsSVG', 'Azimuth',
        'BoundingCircle', 'Centroid', 'Difference', 'Distance', 'Envelope',
        'ForceRHR', 'GeoHash', 'Intersection', 'IsValid', 'Length',
        'LineLocatePoint', 'MakeValid', 'MemSize', 'NumGeometries',
        'NumPoints', 'Perimeter', 'PointOnSurface', 'Reverse', 'Scale',
        'SnapToGrid', 'SymDifference', 'Transform', 'Translate', 'Union',
    }

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
        Return the database column type for the geometry field on
        the spatial backend.
        """
        raise NotImplementedError('subclasses of BaseSpatialOperations must provide a geo_db_type() method')

    def get_distance(self, f, value, lookup_type):
        """
        Return the distance parameters for the given geometry field,
        lookup value, and lookup type.
        """
        raise NotImplementedError('Distance operations not available on this spatial backend.')

    def get_geom_placeholder(self, f, value, compiler):
        """
        Return the placeholder for the given geometry field with the given
        value.  Depending on the spatial backend, the placeholder may contain a
        stored procedure call to the transformation function of the spatial
        backend.
        """
        def transform_value(value, field):
            return (
                not (value is None or value.srid == field.srid) and
                self.connection.features.supports_transform
            )

        if hasattr(value, 'as_sql'):
            return (
                '%s(%%s, %s)' % (self.spatial_function_name('Transform'), f.srid)
                if transform_value(value.output_field, f)
                else '%s'
            )
        if transform_value(value, f):
            # Add Transform() to the SQL placeholder.
            return '%s(%s(%%s,%s), %s)' % (
                self.spatial_function_name('Transform'),
                self.from_text, value.srid, f.srid,
            )
        elif self.connection.features.has_spatialrefsys_table:
            return '%s(%%s,%s)' % (self.from_text, f.srid)
        else:
            # For backwards compatibility on MySQL (#27464).
            return '%s(%%s)' % self.from_text

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
