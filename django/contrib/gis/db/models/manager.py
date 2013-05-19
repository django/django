from django.db.models.manager import Manager
from django.contrib.gis.db.models.query import GeoQuerySet

class GeoManager(Manager):
    "Overrides Manager to return Geographic QuerySets."

    # This manager should be used for queries on related fields
    # so that geometry columns on Oracle and MySQL are selected
    # properly.
    use_for_related_fields = True

    def get_queryset(self):
        return GeoQuerySet(self.model, using=self._db)

    def area(self, *args, **kwargs):
        return self.get_queryset().area(*args, **kwargs)

    def centroid(self, *args, **kwargs):
        return self.get_queryset().centroid(*args, **kwargs)

    def collect(self, *args, **kwargs):
        return self.get_queryset().collect(*args, **kwargs)

    def difference(self, *args, **kwargs):
        return self.get_queryset().difference(*args, **kwargs)

    def distance(self, *args, **kwargs):
        return self.get_queryset().distance(*args, **kwargs)

    def envelope(self, *args, **kwargs):
        return self.get_queryset().envelope(*args, **kwargs)

    def extent(self, *args, **kwargs):
        return self.get_queryset().extent(*args, **kwargs)

    def extent3d(self, *args, **kwargs):
        return self.get_queryset().extent3d(*args, **kwargs)

    def force_rhr(self, *args, **kwargs):
        return self.get_queryset().force_rhr(*args, **kwargs)

    def geohash(self, *args, **kwargs):
        return self.get_queryset().geohash(*args, **kwargs)

    def geojson(self, *args, **kwargs):
        return self.get_queryset().geojson(*args, **kwargs)

    def gml(self, *args, **kwargs):
        return self.get_queryset().gml(*args, **kwargs)

    def intersection(self, *args, **kwargs):
        return self.get_queryset().intersection(*args, **kwargs)

    def kml(self, *args, **kwargs):
        return self.get_queryset().kml(*args, **kwargs)

    def length(self, *args, **kwargs):
        return self.get_queryset().length(*args, **kwargs)

    def make_line(self, *args, **kwargs):
        return self.get_queryset().make_line(*args, **kwargs)

    def mem_size(self, *args, **kwargs):
        return self.get_queryset().mem_size(*args, **kwargs)

    def num_geom(self, *args, **kwargs):
        return self.get_queryset().num_geom(*args, **kwargs)

    def num_points(self, *args, **kwargs):
        return self.get_queryset().num_points(*args, **kwargs)

    def perimeter(self, *args, **kwargs):
        return self.get_queryset().perimeter(*args, **kwargs)

    def point_on_surface(self, *args, **kwargs):
        return self.get_queryset().point_on_surface(*args, **kwargs)

    def reverse_geom(self, *args, **kwargs):
        return self.get_queryset().reverse_geom(*args, **kwargs)

    def scale(self, *args, **kwargs):
        return self.get_queryset().scale(*args, **kwargs)

    def snap_to_grid(self, *args, **kwargs):
        return self.get_queryset().snap_to_grid(*args, **kwargs)

    def svg(self, *args, **kwargs):
        return self.get_queryset().svg(*args, **kwargs)

    def sym_difference(self, *args, **kwargs):
        return self.get_queryset().sym_difference(*args, **kwargs)

    def transform(self, *args, **kwargs):
        return self.get_queryset().transform(*args, **kwargs)

    def translate(self, *args, **kwargs):
        return self.get_queryset().translate(*args, **kwargs)

    def union(self, *args, **kwargs):
        return self.get_queryset().union(*args, **kwargs)

    def unionagg(self, *args, **kwargs):
        return self.get_queryset().unionagg(*args, **kwargs)
