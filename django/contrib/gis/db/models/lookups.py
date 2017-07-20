import re

from django.contrib.gis.db.models.fields import BaseSpatialField
from django.db.models.expressions import Col, Expression
from django.db.models.lookups import Lookup, Transform
from django.db.models.sql.query import Query


class RasterBandTransform(Transform):
    def as_sql(self, compiler, connection):
        return compiler.compile(self.lhs)


class GISLookup(Lookup):
    sql_template = None
    transform_func = None
    distance = False
    band_rhs = None
    band_lhs = None

    def __init__(self, lhs, rhs):
        rhs, *self.rhs_params = rhs if isinstance(rhs, (list, tuple)) else [rhs]
        super().__init__(lhs, rhs)
        self.template_params = {}
        self.process_rhs_params()

    def process_rhs_params(self):
        if self.rhs_params:
            # Check if a band index was passed in the query argument.
            if len(self.rhs_params) == (2 if self.lookup_name == 'relate' else 1):
                self.process_band_indices()
            elif len(self.rhs_params) > 1:
                raise ValueError('Tuple too long for lookup %s.' % self.lookup_name)
        elif isinstance(self.lhs, RasterBandTransform):
            self.process_band_indices(only_lhs=True)

    def process_band_indices(self, only_lhs=False):
        """
        Extract the lhs band index from the band transform class and the rhs
        band index from the input tuple.
        """
        # PostGIS band indices are 1-based, so the band index needs to be
        # increased to be consistent with the GDALRaster band indices.
        if only_lhs:
            self.band_rhs = 1
            self.band_lhs = self.lhs.band_index + 1
            return

        if isinstance(self.lhs, RasterBandTransform):
            self.band_lhs = self.lhs.band_index + 1
        else:
            self.band_lhs = 1

        self.band_rhs, *self.rhs_params = self.rhs_params

    def get_db_prep_lookup(self, value, connection):
        # get_db_prep_lookup is called by process_rhs from super class
        return ('%s', [connection.ops.Adapter(value)] + (self.rhs_params or []))

    def process_rhs(self, compiler, connection):
        if isinstance(self.rhs, Query):
            # If rhs is some Query, don't touch it.
            return super().process_rhs(compiler, connection)

        geom = self.rhs
        if isinstance(self.rhs, Col):
            # Make sure the F Expression destination field exists, and
            # set an `srid` attribute with the same as that of the
            # destination.
            geo_fld = self.rhs.output_field
            if not hasattr(geo_fld, 'srid'):
                raise ValueError('No geographic field found in expression.')
            self.rhs.srid = geo_fld.srid
            sql, _ = compiler.compile(geom)
            return connection.ops.get_geom_placeholder(self.lhs.output_field, geom, compiler) % sql, []
        elif isinstance(self.rhs, Expression):
            raise ValueError('Complex expressions not supported for spatial fields.')

        rhs, rhs_params = super().process_rhs(compiler, connection)
        rhs = connection.ops.get_geom_placeholder(self.lhs.output_field, geom, compiler)
        return rhs, rhs_params

    def get_rhs_op(self, connection, rhs):
        # Unlike BuiltinLookup, the GIS get_rhs_op() implementation should return
        # an object (SpatialOperator) with an as_sql() method to allow for more
        # complex computations (where the lhs part can be mixed in).
        return connection.ops.gis_operators[self.lookup_name]

    def as_sql(self, compiler, connection):
        lhs_sql, sql_params = self.process_lhs(compiler, connection)
        rhs_sql, rhs_params = self.process_rhs(compiler, connection)
        sql_params.extend(rhs_params)

        template_params = {'lhs': lhs_sql, 'rhs': rhs_sql, 'value': '%s'}
        template_params.update(self.template_params)
        rhs_op = self.get_rhs_op(connection, rhs_sql)
        return rhs_op.as_sql(connection, self, template_params, sql_params)


# ------------------
# Geometry operators
# ------------------

@BaseSpatialField.register_lookup
class OverlapsLeftLookup(GISLookup):
    """
    The overlaps_left operator returns true if A's bounding box overlaps or is to the
    left of B's bounding box.
    """
    lookup_name = 'overlaps_left'


@BaseSpatialField.register_lookup
class OverlapsRightLookup(GISLookup):
    """
    The 'overlaps_right' operator returns true if A's bounding box overlaps or is to the
    right of B's bounding box.
    """
    lookup_name = 'overlaps_right'


@BaseSpatialField.register_lookup
class OverlapsBelowLookup(GISLookup):
    """
    The 'overlaps_below' operator returns true if A's bounding box overlaps or is below
    B's bounding box.
    """
    lookup_name = 'overlaps_below'


@BaseSpatialField.register_lookup
class OverlapsAboveLookup(GISLookup):
    """
    The 'overlaps_above' operator returns true if A's bounding box overlaps or is above
    B's bounding box.
    """
    lookup_name = 'overlaps_above'


@BaseSpatialField.register_lookup
class LeftLookup(GISLookup):
    """
    The 'left' operator returns true if A's bounding box is strictly to the left
    of B's bounding box.
    """
    lookup_name = 'left'


@BaseSpatialField.register_lookup
class RightLookup(GISLookup):
    """
    The 'right' operator returns true if A's bounding box is strictly to the right
    of B's bounding box.
    """
    lookup_name = 'right'


@BaseSpatialField.register_lookup
class StrictlyBelowLookup(GISLookup):
    """
    The 'strictly_below' operator returns true if A's bounding box is strictly below B's
    bounding box.
    """
    lookup_name = 'strictly_below'


@BaseSpatialField.register_lookup
class StrictlyAboveLookup(GISLookup):
    """
    The 'strictly_above' operator returns true if A's bounding box is strictly above B's
    bounding box.
    """
    lookup_name = 'strictly_above'


@BaseSpatialField.register_lookup
class SameAsLookup(GISLookup):
    """
    The "~=" operator is the "same as" operator. It tests actual geometric
    equality of two features. So if A and B are the same feature,
    vertex-by-vertex, the operator returns true.
    """
    lookup_name = 'same_as'


BaseSpatialField.register_lookup(SameAsLookup, 'exact')


@BaseSpatialField.register_lookup
class BBContainsLookup(GISLookup):
    """
    The 'bbcontains' operator returns true if A's bounding box completely contains
    by B's bounding box.
    """
    lookup_name = 'bbcontains'


@BaseSpatialField.register_lookup
class BBOverlapsLookup(GISLookup):
    """
    The 'bboverlaps' operator returns true if A's bounding box overlaps B's bounding box.
    """
    lookup_name = 'bboverlaps'


@BaseSpatialField.register_lookup
class ContainedLookup(GISLookup):
    """
    The 'contained' operator returns true if A's bounding box is completely contained
    by B's bounding box.
    """
    lookup_name = 'contained'


# ------------------
# Geometry functions
# ------------------

@BaseSpatialField.register_lookup
class ContainsLookup(GISLookup):
    lookup_name = 'contains'


@BaseSpatialField.register_lookup
class ContainsProperlyLookup(GISLookup):
    lookup_name = 'contains_properly'


@BaseSpatialField.register_lookup
class CoveredByLookup(GISLookup):
    lookup_name = 'coveredby'


@BaseSpatialField.register_lookup
class CoversLookup(GISLookup):
    lookup_name = 'covers'


@BaseSpatialField.register_lookup
class CrossesLookup(GISLookup):
    lookup_name = 'crosses'


@BaseSpatialField.register_lookup
class DisjointLookup(GISLookup):
    lookup_name = 'disjoint'


@BaseSpatialField.register_lookup
class EqualsLookup(GISLookup):
    lookup_name = 'equals'


@BaseSpatialField.register_lookup
class IntersectsLookup(GISLookup):
    lookup_name = 'intersects'


@BaseSpatialField.register_lookup
class OverlapsLookup(GISLookup):
    lookup_name = 'overlaps'


@BaseSpatialField.register_lookup
class RelateLookup(GISLookup):
    lookup_name = 'relate'
    sql_template = '%(func)s(%(lhs)s, %(rhs)s, %%s)'
    pattern_regex = re.compile(r'^[012TF\*]{9}$')

    def get_db_prep_lookup(self, value, connection):
        if len(self.rhs_params) != 1:
            raise ValueError('relate must be passed a two-tuple')
        # Check the pattern argument
        backend_op = connection.ops.gis_operators[self.lookup_name]
        if hasattr(backend_op, 'check_relate_argument'):
            backend_op.check_relate_argument(self.rhs_params[0])
        else:
            pattern = self.rhs_params[0]
            if not isinstance(pattern, str) or not self.pattern_regex.match(pattern):
                raise ValueError('Invalid intersection matrix pattern "%s".' % pattern)
        return super().get_db_prep_lookup(value, connection)


@BaseSpatialField.register_lookup
class TouchesLookup(GISLookup):
    lookup_name = 'touches'


@BaseSpatialField.register_lookup
class WithinLookup(GISLookup):
    lookup_name = 'within'


class DistanceLookupBase(GISLookup):
    distance = True
    sql_template = '%(func)s(%(lhs)s, %(rhs)s) %(op)s %(value)s'

    def process_rhs_params(self):
        if not 1 <= len(self.rhs_params) <= 3:
            raise ValueError("2, 3, or 4-element tuple required for '%s' lookup." % self.lookup_name)
        elif len(self.rhs_params) == 3 and self.rhs_params[2] != 'spheroid':
            raise ValueError("For 4-element tuples the last argument must be the 'spheroid' directive.")

        # Check if the second parameter is a band index.
        if len(self.rhs_params) > 1 and self.rhs_params[1] != 'spheroid':
            self.process_band_indices()

    def process_rhs(self, compiler, connection):
        params = [connection.ops.Adapter(self.rhs)]
        # Getting the distance parameter in the units of the field.
        dist_param = self.rhs_params[0]
        if hasattr(dist_param, 'resolve_expression'):
            dist_param = dist_param.resolve_expression(compiler.query)
            sql, expr_params = compiler.compile(dist_param)
            self.template_params['value'] = sql
            params.extend(expr_params)
        else:
            params += connection.ops.get_distance(
                self.lhs.output_field, self.rhs_params,
                self.lookup_name,
            )
        rhs = connection.ops.get_geom_placeholder(self.lhs.output_field, params[0], compiler)
        return (rhs, params)


@BaseSpatialField.register_lookup
class DWithinLookup(DistanceLookupBase):
    lookup_name = 'dwithin'
    sql_template = '%(func)s(%(lhs)s, %(rhs)s, %%s)'


@BaseSpatialField.register_lookup
class DistanceGTLookup(DistanceLookupBase):
    lookup_name = 'distance_gt'


@BaseSpatialField.register_lookup
class DistanceGTELookup(DistanceLookupBase):
    lookup_name = 'distance_gte'


@BaseSpatialField.register_lookup
class DistanceLTLookup(DistanceLookupBase):
    lookup_name = 'distance_lt'


@BaseSpatialField.register_lookup
class DistanceLTELookup(DistanceLookupBase):
    lookup_name = 'distance_lte'
