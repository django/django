from django.db import connections
from django.db.models.query import sql
from django.db.models.sql.constants import QUERY_TERMS

from django.contrib.gis.db.models.fields import GeometryField
from django.contrib.gis.db.models.lookups import GISLookup
from django.contrib.gis.db.models import aggregates as gis_aggregates
from django.contrib.gis.db.models.sql.conversion import GeomField


class GeoQuery(sql.Query):
    """
    A single spatial SQL query.
    """
    # Overriding the valid query terms.
    query_terms = QUERY_TERMS | set(GeometryField.class_lookups.keys())

    compiler = 'GeoSQLCompiler'

    #### Methods overridden from the base Query class ####
    def __init__(self, model):
        super(GeoQuery, self).__init__(model)
        # The following attributes are customized for the GeoQuerySet.
        # The SpatialBackend classes contain backend-specific routines and functions.
        self.custom_select = {}
        self.transformed_srid = None
        self.extra_select_fields = {}

    def clone(self, *args, **kwargs):
        obj = super(GeoQuery, self).clone(*args, **kwargs)
        # Customized selection dictionary and transformed srid flag have
        # to also be added to obj.
        obj.custom_select = self.custom_select.copy()
        obj.transformed_srid = self.transformed_srid
        obj.extra_select_fields = self.extra_select_fields.copy()
        return obj

    def get_aggregation(self, using, force_subq=False):
        # Remove any aggregates marked for reduction from the subquery
        # and move them to the outer AggregateQuery.
        connection = connections[using]
        for alias, annotation in self.annotation_select.items():
            if isinstance(annotation, gis_aggregates.GeoAggregate):
                if not getattr(annotation, 'is_extent', False) or connection.ops.oracle:
                    self.extra_select_fields[alias] = GeomField()
        return super(GeoQuery, self).get_aggregation(using, force_subq)

    # Private API utilities, subject to change.
    def _geo_field(self, field_name=None):
        """
        Returns the first Geometry field encountered; or specified via the
        `field_name` keyword.  The `field_name` may be a string specifying
        the geometry field on this GeoQuery's model, or a lookup string
        to a geometry field via a ForeignKey relation.
        """
        if field_name is None:
            # Incrementing until the first geographic field is found.
            for fld in self.model._meta.fields:
                if isinstance(fld, GeometryField):
                    return fld
            return False
        else:
            # Otherwise, check by the given field name -- which may be
            # a lookup to a _related_ geographic field.
            return GISLookup._check_geo_field(self.model._meta, field_name)
