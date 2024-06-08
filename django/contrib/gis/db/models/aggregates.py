from django.contrib.gis.db.models.fields import (
    ExtentField,
    GeometryCollectionField,
    GeometryField,
    LineStringField,
)
from django.db.models import Aggregate, Func, Value
from django.utils.functional import cached_property

__all__ = ["Collect", "Extent", "Extent3D", "MakeLine", "Union"]


class GeoAggregate(Aggregate):
    function = None
    is_extent = False

    @cached_property
    def output_field(self):
        return self.output_field_class(self.source_expressions[0].output_field.srid)

    def as_sql(self, compiler, connection, function=None, **extra_context):
        # this will be called again in parent, but it's needed now - before
        # we get the spatial_aggregate_name
        connection.ops.check_expression_support(self)
        return super().as_sql(
            compiler,
            connection,
            function=function or connection.ops.spatial_aggregate_name(self.name),
            **extra_context,
        )

    def as_oracle(self, compiler, connection, **extra_context):
        if not self.is_extent:
            tolerance = self.extra.get("tolerance") or getattr(self, "tolerance", 0.05)
            clone = self.copy()
            source_expressions = self.get_source_expressions()
            source_expressions.pop()  # Don't wrap filters with SDOAGGRTYPE().
            spatial_type_expr = Func(
                *source_expressions,
                Value(tolerance),
                function="SDOAGGRTYPE",
                output_field=self.output_field,
            )
            source_expressions = [spatial_type_expr, self.filter]
            clone.set_source_expressions(source_expressions)
            return clone.as_sql(compiler, connection, **extra_context)
        return self.as_sql(compiler, connection, **extra_context)

    def resolve_expression(
        self, query=None, allow_joins=True, reuse=None, summarize=False, for_save=False
    ):
        c = super().resolve_expression(query, allow_joins, reuse, summarize, for_save)
        for field in c.get_source_fields():
            if not hasattr(field, "geom_type"):
                raise ValueError(
                    "Geospatial aggregates only allowed on geometry fields."
                )
        return c


class Collect(GeoAggregate):
    name = "Collect"
    output_field_class = GeometryCollectionField


class Extent(GeoAggregate):
    name = "Extent"
    is_extent = "2D"

    def __init__(self, expression, **extra):
        super().__init__(expression, output_field=ExtentField(), **extra)

    def convert_value(self, value, expression, connection):
        return connection.ops.convert_extent(value)


class Extent3D(GeoAggregate):
    name = "Extent3D"
    is_extent = "3D"

    def __init__(self, expression, **extra):
        super().__init__(expression, output_field=ExtentField(), **extra)

    def convert_value(self, value, expression, connection):
        return connection.ops.convert_extent3d(value)


class MakeLine(GeoAggregate):
    name = "MakeLine"
    output_field_class = LineStringField


class Union(GeoAggregate):
    name = "Union"
    output_field_class = GeometryField
