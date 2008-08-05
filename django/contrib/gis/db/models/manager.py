from django.db.models.manager import Manager
from django.contrib.gis.db.models.query import GeoQuerySet

class GeoManager(Manager):
    "Overrides Manager to return Geographic QuerySets."

    # This manager should be used for queries on related fields
    # so that geometry columns on Oracle and MySQL are selected
    # properly.
    use_for_related_fields = True

    def get_query_set(self):
        return GeoQuerySet(model=self.model)

    def area(self, *args, **kwargs):
        return self.get_query_set().area(*args, **kwargs)

    def centroid(self, *args, **kwargs):
        return self.get_query_set().centroid(*args, **kwargs)

    def difference(self, *args, **kwargs):
        return self.get_query_set().difference(*args, **kwargs)

    def distance(self, *args, **kwargs):
        return self.get_query_set().distance(*args, **kwargs)

    def envelope(self, *args, **kwargs):
        return self.get_query_set().envelope(*args, **kwargs)

    def extent(self, *args, **kwargs):
        return self.get_query_set().extent(*args, **kwargs)

    def gml(self, *args, **kwargs):
        return self.get_query_set().gml(*args, **kwargs)

    def intersection(self, *args, **kwargs):
        return self.get_query_set().intersection(*args, **kwargs)

    def kml(self, *args, **kwargs):
        return self.get_query_set().kml(*args, **kwargs)

    def length(self, *args, **kwargs):
        return self.get_query_set().length(*args, **kwargs)

    def make_line(self, *args, **kwargs):
        return self.get_query_set().make_line(*args, **kwargs)
    
    def mem_size(self, *args, **kwargs):
        return self.get_query_set().mem_size(*args, **kwargs)

    def num_geom(self, *args, **kwargs):
        return self.get_query_set().num_geom(*args, **kwargs)

    def num_points(self, *args, **kwargs):
        return self.get_query_set().num_points(*args, **kwargs)

    def perimeter(self, *args, **kwargs):
        return self.get_query_set().perimeter(*args, **kwargs)

    def point_on_surface(self, *args, **kwargs):
        return self.get_query_set().point_on_surface(*args, **kwargs)

    def scale(self, *args, **kwargs):
        return self.get_query_set().scale(*args, **kwargs)

    def svg(self, *args, **kwargs):
        return self.get_query_set().svg(*args, **kwargs)

    def sym_difference(self, *args, **kwargs):
        return self.get_query_set().sym_difference(*args, **kwargs)

    def transform(self, *args, **kwargs):
        return self.get_query_set().transform(*args, **kwargs)

    def translate(self, *args, **kwargs):
        return self.get_query_set().translate(*args, **kwargs)

    def union(self, *args, **kwargs):
        return self.get_query_set().union(*args, **kwargs)

    def unionagg(self, *args, **kwargs):
        return self.get_query_set().unionagg(*args, **kwargs)
