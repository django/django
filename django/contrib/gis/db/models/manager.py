from django.db.models.manager import Manager
from django.contrib.gis.db.models.query import GeoQuerySet

class GeoManager(Manager):
    "Overrides Manager to return Geographic QuerySets."

    def get_query_set(self):
        return GeoQuerySet(model=self.model)
