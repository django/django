import warnings

from django.contrib.gis.db.models.query import GeoQuerySet
from django.db.models.manager import Manager
from django.utils.deprecation import RemovedInDjango20Warning


class GeoManager(Manager.from_queryset(GeoQuerySet)):
    "Overrides Manager to return Geographic QuerySets."

    # This manager should be used for queries on related fields
    # so that geometry columns on Oracle and MySQL are selected
    # properly.
    use_for_related_fields = True

    # No need to bother users with the use_for_related_fields
    # deprecation for this manager which is itself deprecated.
    silence_use_for_related_fields_deprecation = True

    def __init__(self, *args, **kwargs):
        warnings.warn(
            "The GeoManager class is deprecated. Simply use a normal manager "
            "once you have replaced all calls to GeoQuerySet methods by annotations.",
            RemovedInDjango20Warning, stacklevel=2
        )
        super(GeoManager, self).__init__(*args, **kwargs)
