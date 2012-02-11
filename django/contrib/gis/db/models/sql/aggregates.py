from django.db.models.sql.aggregates import *
from django.contrib.gis.db.models.fields import GeometryField

class GeoAggregate(Aggregate):
    # Conversion class, if necessary.
    conversion_class = None

    # Flags for indicating the type of the aggregate.
    is_extent = False

    def __init__(self, expression, query, promote_joins=False, is_summary=False, **extra):
        super(GeoAggregate, self).__init__(expression, query, promote_joins, is_summary, **extra)

        # Can't use geographic aggregates on non-geometry fields.
        if not isinstance(self.field, GeometryField):
            raise ValueError('Geospatial aggregates only allowed on geometry fields.')

class Collect(GeoAggregate):
    pass

class Extent(GeoAggregate):
    is_extent = '2D'

class Extent3D(GeoAggregate):
    is_extent = '3D'

class MakeLine(GeoAggregate):
    pass

class Union(GeoAggregate):
    pass
