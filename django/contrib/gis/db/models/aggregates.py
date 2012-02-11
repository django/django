from django.db.models import Aggregate
from django.contrib.gis.db.models.sql import GeomField

class GeoAggregate(Aggregate):
    def __init__(self, lookup, tolerance=0.05, **extra):
        super(GeoAggregate, self).__init__(lookup, **extra)

        # Required by some Oracle aggregates.
        self.extra['tolerance'] = tolerance

class Collect(GeoAggregate):
    name = 'Collect'

class Extent(GeoAggregate):
    name = 'Extent'

class Extent3D(GeoAggregate):
    name = 'Extent3D'

class MakeLine(GeoAggregate):
    name = 'MakeLine'

class Union(GeoAggregate):
    name = 'Union'
