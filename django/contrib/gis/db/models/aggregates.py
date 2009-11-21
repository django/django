from django.db.models import Aggregate
from django.contrib.gis.db.backend import SpatialBackend
from django.contrib.gis.db.models.sql import GeomField

class GeoAggregate(Aggregate):

    def add_to_query(self, query, alias, col, source, is_summary):
        if hasattr(source, 'geom_type'):
            # Doing additional setup on the Query object for spatial aggregates.
            aggregate = getattr(query.aggregates_module, self.name)
            
            # Adding a conversion class instance and any selection wrapping
            # SQL (e.g., needed by Oracle).
            if aggregate.conversion_class is GeomField:
                query.extra_select_fields[alias] = GeomField()
                if SpatialBackend.select:
                    query.custom_select[alias] = SpatialBackend.select
     
        super(GeoAggregate, self).add_to_query(query, alias, col, source, is_summary)

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
