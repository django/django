import datetime
from django.db.models.fields import Field
from django.db.models.sql.where import WhereNode
from django.contrib.gis.db.backend import get_geo_where_clause, SpatialBackend

class GeoAnnotation(object):
    """
    The annotation used for GeometryFields; basically a placeholder
    for metadata needed by the `get_geo_where_clause` of the spatial
    backend.
    """
    def __init__(self, field, value, where):
        self.geodetic = field.geodetic
        self.geom_type = field._geom
        self.value = value
        self.where = tuple(where)

class GeoWhereNode(WhereNode):
    """
    Used to represent the SQL where-clause for spatial databases --
    these are tied to the GeoQuery class that created it.
    """
    def add(self, data, connector):
        """
        This is overridden from the regular WhereNode to handle the 
        peculiarties of GeometryFields, because they need a special 
        annotation object that contains the spatial metadata from the 
        field so that the correct spatial SQL is generated.
        """
        if not isinstance(data, (list, tuple)):
            super(WhereNode, self).add(data, connector)
            return

        alias, col, field, lookup_type, value = data
        # Do we have a geographic field?
        geo_field = hasattr(field, '_geom')
        if field:
            if geo_field:
                # `GeometryField.get_db_prep_lookup` returns a where clause
                # substitution array in addition to the parameters.
                where, params = field.get_db_prep_lookup(lookup_type, value)
            else:
                params = field.get_db_prep_lookup(lookup_type, value)
            db_type = field.db_type()
        else:
            # This is possible when we add a comparison to NULL sometimes (we
            # don't really need to waste time looking up the associated field
            # object).
            params = Field().get_db_prep_lookup(lookup_type, value)
            db_type = None
  
        if geo_field:
            # The annotation will be a `GeoAnnotation` object that
            # will contain the necessary geometry field metadata for
            # the `get_geo_where_clause` to construct the appropriate
            # spatial SQL when `make_atom` is called.
            annotation = GeoAnnotation(field, value, where)
        elif isinstance(value, datetime.datetime):
            annotation = datetime.datetime
        else:
            annotation = bool(value)

        super(WhereNode, self).add((alias, col, db_type, lookup_type,
                                    annotation, params), connector)

    def make_atom(self, child, qn):
        table_alias, name, db_type, lookup_type, value_annot, params = child
 
        if isinstance(value_annot, GeoAnnotation):
            if lookup_type in SpatialBackend.gis_terms:
                # Getting the geographic where clause; substitution parameters
                # will be populated in the GeoFieldSQL object returned by the
                # GeometryField.
                gwc = get_geo_where_clause(table_alias, name, lookup_type, value_annot)
                return gwc % value_annot.where, params
            else:
                raise TypeError('Invalid lookup type: %r' % lookup_type)
        else:
            # If not a GeometryField, call the `make_atom` from the 
            # base class.
            return super(GeoWhereNode, self).make_atom(child, qn)
