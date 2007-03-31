from django.db.models.query import Q, QNot, QuerySet
from django.contrib.gis.db.models.postgis import parse_lookup
import operator

class GeoQ(Q):
    "Geographical query encapsulation object."

    def get_sql(self, opts):
        "Overloaded to use our own parse_lookup() function."
        return parse_lookup(self.kwargs.items(), opts)

class GeoQuerySet(QuerySet):
    "Geographical-enabled QuerySet object."

    def __init__(self, model=None):
        super(GeoQuerySet, self).__init__(model=model)

        # We only want to use the GeoQ object for our queries
        self._filters = GeoQ()

    def _filter_or_exclude(self, mapper, *args, **kwargs):
        # mapper is a callable used to transform Q objects,
        # or None for identity transform
        if mapper is None:
            mapper = lambda x: x
        if len(args) > 0 or len(kwargs) > 0:
            assert self._limit is None and self._offset is None, \
                "Cannot filter a query once a slice has been taken."

        clone = self._clone()
        if len(kwargs) > 0:
            clone._filters = clone._filters & mapper(GeoQ(**kwargs)) # Using the GeoQ object for our filters instead
        if len(args) > 0:
            clone._filters = clone._filters & reduce(operator.and_, map(mapper, args))
        return clone
