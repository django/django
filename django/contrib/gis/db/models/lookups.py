import re

from django.core.exceptions import FieldDoesNotExist
from django.db.models.constants import LOOKUP_SEP
from django.db.models.expressions import Col, Expression
from django.db.models.lookups import Lookup, Transform
from django.db.models.sql.query import Query

gis_lookups = {}


class RasterBandTransform(Transform):
    def as_sql(self, compiler, connection):
        return compiler.compile(self.lhs)


class GISLookup(Lookup):
    sql_template = None
    transform_func = None
    distance = False
    band_rhs = None
    band_lhs = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.template_params = {}

    @classmethod
    def _check_geo_field(cls, opts, lookup):
        """
        Utility for checking the given lookup with the given model options.
        The lookup is a string either specifying the geographic field, e.g.
        'point, 'the_geom', or a related lookup on a geographic field like
        'address__point'.

        If a BaseSpatialField exists according to the given lookup on the model
        options, it will be returned. Otherwise return None.
        """
        from django.contrib.gis.db.models.fields import BaseSpatialField
        # This takes into account the situation where the lookup is a
        # lookup to a related geographic field, e.g., 'address__point'.
        field_list = lookup.split(LOOKUP_SEP)

        # Reversing so list operates like a queue of related lookups,
        # and popping the top lookup.
        field_list.reverse()
        fld_name = field_list.pop()

        try:
            geo_fld = opts.get_field(fld_name)
            # If the field list is still around, then it means that the
            # lookup was for a geometry field across a relationship --
            # thus we keep on getting the related model options and the
            # model field associated with the next field in the list
            # until there's no more left.
            while len(field_list):
                opts = geo_fld.remote_field.model._meta
                geo_fld = opts.get_field(field_list.pop())
        except (FieldDoesNotExist, AttributeError):
            return False

        # Finally, make sure we got a Geographic field and return.
        if isinstance(geo_fld, BaseSpatialField):
            return geo_fld
        else:
            return False

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

        self.band_rhs = self.rhs[1]
        if len(self.rhs) == 1:
            self.rhs = self.rhs[0]
        else:
            self.rhs = (self.rhs[0], ) + self.rhs[2:]

    def get_db_prep_lookup(self, value, connection):
        # get_db_prep_lookup is called by process_rhs from super class
        if isinstance(value, (tuple, list)):
            # First param is assumed to be the geometric object
            params = [connection.ops.Adapter(value[0])] + list(value)[1:]
        else:
            params = [connection.ops.Adapter(value)]
        return ('%s', params)

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
        elif isinstance(self.rhs, Expression):
            raise ValueError('Complex expressions not supported for spatial fields.')
        elif isinstance(self.rhs, (list, tuple)):
            geom = self.rhs[0]
            # Check if a band index was passed in the query argument.
            if ((len(self.rhs) == 2 and not self.lookup_name == 'relate') or
                    (len(self.rhs) == 3 and self.lookup_name == 'relate')):
                self.process_band_indices()
            elif len(self.rhs) > 2:
                raise ValueError('Tuple too long for lookup %s.' % self.lookup_name)
        elif isinstance(self.lhs, RasterBandTransform):
            self.process_band_indices(only_lhs=True)

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

class OverlapsLeftLookup(GISLookup):
    """
    The overlaps_left operator returns true if A's bounding box overlaps or is to the
    left of B's bounding box.
    """
    lookup_name = 'overlaps_left'


gis_lookups['overlaps_left'] = OverlapsLeftLookup


class OverlapsRightLookup(GISLookup):
    """
    The 'overlaps_right' operator returns true if A's bounding box overlaps or is to the
    right of B's bounding box.
    """
    lookup_name = 'overlaps_right'


gis_lookups['overlaps_right'] = OverlapsRightLookup


class OverlapsBelowLookup(GISLookup):
    """
    The 'overlaps_below' operator returns true if A's bounding box overlaps or is below
    B's bounding box.
    """
    lookup_name = 'overlaps_below'


gis_lookups['overlaps_below'] = OverlapsBelowLookup


class OverlapsAboveLookup(GISLookup):
    """
    The 'overlaps_above' operator returns true if A's bounding box overlaps or is above
    B's bounding box.
    """
    lookup_name = 'overlaps_above'


gis_lookups['overlaps_above'] = OverlapsAboveLookup


class LeftLookup(GISLookup):
    """
    The 'left' operator returns true if A's bounding box is strictly to the left
    of B's bounding box.
    """
    lookup_name = 'left'


gis_lookups['left'] = LeftLookup


class RightLookup(GISLookup):
    """
    The 'right' operator returns true if A's bounding box is strictly to the right
    of B's bounding box.
    """
    lookup_name = 'right'


gis_lookups['right'] = RightLookup


class StrictlyBelowLookup(GISLookup):
    """
    The 'strictly_below' operator returns true if A's bounding box is strictly below B's
    bounding box.
    """
    lookup_name = 'strictly_below'


gis_lookups['strictly_below'] = StrictlyBelowLookup


class StrictlyAboveLookup(GISLookup):
    """
    The 'strictly_above' operator returns true if A's bounding box is strictly above B's
    bounding box.
    """
    lookup_name = 'strictly_above'


gis_lookups['strictly_above'] = StrictlyAboveLookup


class SameAsLookup(GISLookup):
    """
    The "~=" operator is the "same as" operator. It tests actual geometric
    equality of two features. So if A and B are the same feature,
    vertex-by-vertex, the operator returns true.
    """
    lookup_name = 'same_as'


gis_lookups['same_as'] = SameAsLookup


class ExactLookup(SameAsLookup):
    # Alias of same_as
    lookup_name = 'exact'


gis_lookups['exact'] = ExactLookup


class BBContainsLookup(GISLookup):
    """
    The 'bbcontains' operator returns true if A's bounding box completely contains
    by B's bounding box.
    """
    lookup_name = 'bbcontains'


gis_lookups['bbcontains'] = BBContainsLookup


class BBOverlapsLookup(GISLookup):
    """
    The 'bboverlaps' operator returns true if A's bounding box overlaps B's bounding box.
    """
    lookup_name = 'bboverlaps'


gis_lookups['bboverlaps'] = BBOverlapsLookup


class ContainedLookup(GISLookup):
    """
    The 'contained' operator returns true if A's bounding box is completely contained
    by B's bounding box.
    """
    lookup_name = 'contained'


gis_lookups['contained'] = ContainedLookup


# ------------------
# Geometry functions
# ------------------

class ContainsLookup(GISLookup):
    lookup_name = 'contains'


gis_lookups['contains'] = ContainsLookup


class ContainsProperlyLookup(GISLookup):
    lookup_name = 'contains_properly'


gis_lookups['contains_properly'] = ContainsProperlyLookup


class CoveredByLookup(GISLookup):
    lookup_name = 'coveredby'


gis_lookups['coveredby'] = CoveredByLookup


class CoversLookup(GISLookup):
    lookup_name = 'covers'


gis_lookups['covers'] = CoversLookup


class CrossesLookup(GISLookup):
    lookup_name = 'crosses'


gis_lookups['crosses'] = CrossesLookup


class DisjointLookup(GISLookup):
    lookup_name = 'disjoint'


gis_lookups['disjoint'] = DisjointLookup


class EqualsLookup(GISLookup):
    lookup_name = 'equals'


gis_lookups['equals'] = EqualsLookup


class IntersectsLookup(GISLookup):
    lookup_name = 'intersects'


gis_lookups['intersects'] = IntersectsLookup


class IsValidLookup(GISLookup):
    lookup_name = 'isvalid'
    sql_template = '%(func)s(%(lhs)s)'

    def as_sql(self, compiler, connection):
        if self.lhs.field.geom_type == 'RASTER':
            raise ValueError('The isvalid lookup is only available on geometry fields.')
        gis_op = connection.ops.gis_operators[self.lookup_name]
        sql, params = self.process_lhs(compiler, connection)
        sql, params = gis_op.as_sql(connection, self, {'func': gis_op.func, 'lhs': sql}, params)
        if not self.rhs:
            sql = 'NOT ' + sql
        return sql, params


gis_lookups['isvalid'] = IsValidLookup


class OverlapsLookup(GISLookup):
    lookup_name = 'overlaps'


gis_lookups['overlaps'] = OverlapsLookup


class RelateLookup(GISLookup):
    lookup_name = 'relate'
    sql_template = '%(func)s(%(lhs)s, %(rhs)s, %%s)'
    pattern_regex = re.compile(r'^[012TF\*]{9}$')

    def get_db_prep_lookup(self, value, connection):
        if len(value) != 2:
            raise ValueError('relate must be passed a two-tuple')
        # Check the pattern argument
        backend_op = connection.ops.gis_operators[self.lookup_name]
        if hasattr(backend_op, 'check_relate_argument'):
            backend_op.check_relate_argument(value[1])
        else:
            pattern = value[1]
            if not isinstance(pattern, str) or not self.pattern_regex.match(pattern):
                raise ValueError('Invalid intersection matrix pattern "%s".' % pattern)
        return super().get_db_prep_lookup(value, connection)


gis_lookups['relate'] = RelateLookup


class TouchesLookup(GISLookup):
    lookup_name = 'touches'


gis_lookups['touches'] = TouchesLookup


class WithinLookup(GISLookup):
    lookup_name = 'within'


gis_lookups['within'] = WithinLookup


class DistanceLookupBase(GISLookup):
    distance = True
    sql_template = '%(func)s(%(lhs)s, %(rhs)s) %(op)s %(value)s'

    def process_rhs(self, compiler, connection):
        if not isinstance(self.rhs, (tuple, list)) or not 2 <= len(self.rhs) <= 4:
            raise ValueError("2, 3, or 4-element tuple required for '%s' lookup." % self.lookup_name)
        elif len(self.rhs) == 4 and not self.rhs[3] == 'spheroid':
            raise ValueError("For 4-element tuples the last argument must be the 'speroid' directive.")

        # Check if the second parameter is a band index.
        if len(self.rhs) > 2 and not self.rhs[2] == 'spheroid':
            self.process_band_indices()

        params = [connection.ops.Adapter(self.rhs[0])]

        # Getting the distance parameter in the units of the field.
        dist_param = self.rhs[1]
        if hasattr(dist_param, 'resolve_expression'):
            dist_param = dist_param.resolve_expression(compiler.query)
            sql, expr_params = compiler.compile(dist_param)
            self.template_params['value'] = sql
            params.extend(expr_params)
        else:
            params += connection.ops.get_distance(
                self.lhs.output_field, (dist_param,) + self.rhs[2:],
                self.lookup_name, handle_spheroid=False
            )
        rhs = connection.ops.get_geom_placeholder(self.lhs.output_field, params[0], compiler)
        return (rhs, params)


class DWithinLookup(DistanceLookupBase):
    lookup_name = 'dwithin'
    sql_template = '%(func)s(%(lhs)s, %(rhs)s, %%s)'


gis_lookups['dwithin'] = DWithinLookup


class DistanceGTLookup(DistanceLookupBase):
    lookup_name = 'distance_gt'


gis_lookups['distance_gt'] = DistanceGTLookup


class DistanceGTELookup(DistanceLookupBase):
    lookup_name = 'distance_gte'


gis_lookups['distance_gte'] = DistanceGTELookup


class DistanceLTLookup(DistanceLookupBase):
    lookup_name = 'distance_lt'


gis_lookups['distance_lt'] = DistanceLTLookup


class DistanceLTELookup(DistanceLookupBase):
    lookup_name = 'distance_lte'


gis_lookups['distance_lte'] = DistanceLTELookup
