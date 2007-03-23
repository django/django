from django.db.models.manager import Manager
from django.contrib.gis.db.models.query import GeoQuerySet

class GeoManager(Manager):

    def get_query_set(self):
        return GeoQuerySet(model=self.model)

    def geo_filter(self, *args, **kwargs):
        return self.get_query_set().geo_filter(*args, **kwargs)

    def geo_exclude(self, *args, **kwargs):
        return self.get_query_set().geo_exclude(*args, **kwargs)
