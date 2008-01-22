from django.db.models.manager import Manager
from django.contrib.gis.db.models.query import GeoQuerySet

class GeoManager(Manager):
    "Overrides Manager to return Geographic QuerySets."

    def get_query_set(self):
        return GeoQuerySet(model=self.model)

    def distance(self, *args, **kwargs):
        return self.get_query_set().distance(*args, **kwargs)

    def extent(self, *args, **kwargs):
        return self.get_query_set().extent(*args, **kwargs)

    def gml(self, *args, **kwargs):
        return self.get_query_set().gml(*args, **kwargs)

    def kml(self, *args, **kwargs):
        return self.get_query_set().kml(*args, **kwargs)

    def transform(self, *args, **kwargs):
        return self.get_query_set().transform(*args, **kwargs)

    def union(self, *args, **kwargs):
        return self.get_query_set().union(*args, **kwargs)
