from django.contrib.gis.db.models.query import GeoQuerySet
from django.db.models.manager import Manager


class GeoManager(Manager.from_queryset(GeoQuerySet)):
    "Overrides Manager to return Geographic QuerySets."

    # This manager should be used for queries on related fields
    # so that geometry columns on Oracle and MySQL are selected
    # properly.
    use_for_related_fields = True
