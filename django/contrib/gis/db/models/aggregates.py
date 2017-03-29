from django.contrib.gis.db.models.fields import ExtentField
from django.db.models.aggregates import Aggregate

__all__ = ['Collect', 'Extent', 'Extent3D', 'MakeLine', 'Union']


class GeoAggregate(Aggregate):
    function = None
    is_extent = False

    def as_sql(self, compiler, connection, function=None, **extra_context):
        # this will be called again in parent, but it's needed now - before
        # we get the spatial_aggregate_name
        connection.ops.check_expression_support(self)
        return super().as_sql(
            compiler,
            connection,
            function=function or connection.ops.spatial_aggregate_name(self.name),
            **extra_context
        )

    def as_oracle(self, compiler, connection):
        tolerance = self.extra.get('tolerance') or getattr(self, 'tolerance', 0.05)
        template = None if self.is_extent else '%(function)s(SDOAGGRTYPE(%(expressions)s,%(tolerance)s))'
        return self.as_sql(compiler, connection, template=template, tolerance=tolerance)

    def resolve_expression(self, query=None, allow_joins=True, reuse=None, summarize=False, for_save=False):
        c = super().resolve_expression(query, allow_joins, reuse, summarize, for_save)
        for expr in c.get_source_expressions():
            if not hasattr(expr.field, 'geom_type'):
                raise ValueError('Geospatial aggregates only allowed on geometry fields.')
        return c


class Collect(GeoAggregate):
    name = 'Collect'


class Extent(GeoAggregate):
    name = 'Extent'
    is_extent = '2D'

    def __init__(self, expression, **extra):
        super().__init__(expression, output_field=ExtentField(), **extra)

    def convert_value(self, value, expression, connection, context):
        return connection.ops.convert_extent(value)


class Extent3D(GeoAggregate):
    name = 'Extent3D'
    is_extent = '3D'

    def __init__(self, expression, **extra):
        super().__init__(expression, output_field=ExtentField(), **extra)

    def convert_value(self, value, expression, connection, context):
        return connection.ops.convert_extent3d(value)


class MakeLine(GeoAggregate):
    name = 'MakeLine'


class Union(GeoAggregate):
    name = 'Union'
