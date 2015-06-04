from django.contrib.gis.db.models.fields import ExtentField
from django.db.models.aggregates import Aggregate

__all__ = ['Collect', 'Extent', 'Extent3D', 'MakeLine', 'Union']


class GeoAggregate(Aggregate):
    function = None
    is_extent = False

    def as_sql(self, compiler, connection):
        # this will be called again in parent, but it's needed now - before
        # we get the spatial_aggregate_name
        connection.ops.check_expression_support(self)
        self.function = connection.ops.spatial_aggregate_name(self.name)
        return super(GeoAggregate, self).as_sql(compiler, connection)

    def as_oracle(self, compiler, connection):
        if not hasattr(self, 'tolerance'):
            self.tolerance = 0.05
        self.extra['tolerance'] = self.tolerance
        if not self.is_extent:
            self.template = '%(function)s(SDOAGGRTYPE(%(expressions)s,%(tolerance)s))'
        return self.as_sql(compiler, connection)

    def resolve_expression(self, query=None, allow_joins=True, reuse=None, summarize=False, for_save=False):
        c = super(GeoAggregate, self).resolve_expression(query, allow_joins, reuse, summarize, for_save)
        for expr in c.get_source_expressions():
            if not hasattr(expr.field, 'geom_type'):
                raise ValueError('Geospatial aggregates only allowed on geometry fields.')
        return c

    def convert_value(self, value, expression, connection, context):
        return connection.ops.convert_geom(value, self.output_field)


class Collect(GeoAggregate):
    name = 'Collect'


class Extent(GeoAggregate):
    name = 'Extent'
    is_extent = '2D'

    def __init__(self, expression, **extra):
        super(Extent, self).__init__(expression, output_field=ExtentField(), **extra)

    def convert_value(self, value, expression, connection, context):
        return connection.ops.convert_extent(value, context.get('transformed_srid'))


class Extent3D(GeoAggregate):
    name = 'Extent3D'
    is_extent = '3D'

    def __init__(self, expression, **extra):
        super(Extent3D, self).__init__(expression, output_field=ExtentField(), **extra)

    def convert_value(self, value, expression, connection, context):
        return connection.ops.convert_extent3d(value, context.get('transformed_srid'))


class MakeLine(GeoAggregate):
    name = 'MakeLine'


class Union(GeoAggregate):
    name = 'Union'
