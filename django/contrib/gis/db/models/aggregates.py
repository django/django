from django.db.models.aggregates import Aggregate
from django.db.models import aggregates
from django.db.models.aggregates import *  # NOQA
from django.contrib.gis.db.models.fields import GeometryField

__all__ = ['Collect', 'Extent', 'Extent3D', 'MakeLine', 'Union'] + aggregates.__all__


class GeoAggregate(Aggregate):
    sql_template = None
    sql_function = None
    is_extent = False
    conversion_class = None  # TODO: is this still used?

    def as_sql(self, compiler, connection):
        if connection.ops.oracle:
            if not hasattr(self, 'tolerance'):
                self.tolerance = 0.05
            self.extra['tolerance'] = self.tolerance

        sql_template, sql_function = connection.ops.spatial_aggregate_sql(self)
        if sql_template is None:
            sql_template = '%(function)s(%(field)s)'
        if self.extra.get('sql_template', None) is None:
            self.extra['sql_template'] = sql_template
        if not 'sql_function' in self.extra:
            self.extra['sql_function'] = sql_function

        return super(GeoAggregate, self).as_sql(compiler, connection)

    def prepare(self, query=None, allow_joins=True, reuse=None):
        super(GeoAggregate, self).prepare(query, allow_joins, reuse)
        if not isinstance(self.expression.output_type, GeometryField):
            raise ValueError('Geospatial aggregates only allowed on geometry fields.')


class Collect(GeoAggregate):
    name = 'Collect'


class Extent(GeoAggregate):
    name = 'Extent'
    is_extent = '2D'


class Extent3D(GeoAggregate):
    name = 'Extent3D'
    is_extent = '3D'


class MakeLine(GeoAggregate):
    name = 'MakeLine'


class Union(GeoAggregate):
    name = 'Union'
