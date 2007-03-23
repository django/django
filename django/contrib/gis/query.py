from django.db.models.query import *
from django.contrib.gis.db.models.postgis import geo_parse_lookup

class GeoQ(Q):
    "Geographical query encapsulation object."

    def get_sql(self, opts):
        "Overloaded to use the geo_parse_lookup() function instead of parse_lookup()"
        return geo_parse_lookup(self.kwargs.items(), opts)

class GeoQuerySet(QuerySet):
    "Geographical-enabled QuerySet object."

    def geo_filter(self, *args, **kwargs):
        "Returns a new GeoQuerySet instance with the args ANDed to the existing set."
        return self._geo_filter_or_exclude(None, *args, **kwargs)

    def geo_exclude(self, *args, **kwargs):
        "Returns a new GeoQuerySet instance with NOT (args) ANDed to the existing set."
        return self._geo_filter_or_exclude(QNot, *args, **kwargs)

    def _geo_filter_or_exclude(self, mapper, *args, **kwargs):
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
