from django.db.models.sql.where import WhereNode
from django.contrib.gis.db.backend import get_geo_where_clause, SpatialBackend

class GeoWhereNode(WhereNode):
    """
    The GeoWhereNode calls the `get_geo_where_clause` from the appropriate
    spatial backend in order to construct correct spatial SQL.
    """
    def make_atom(self, child, qn):
        table_alias, name, field, lookup_type, value = child
        if hasattr(field, '_geom'):
            if lookup_type in SpatialBackend.gis_terms:
                # Getting the geographic where clause; substitution parameters
                # will be populated in the GeoFieldSQL object returned by the
                # GeometryField.
                gwc = get_geo_where_clause(lookup_type, table_alias, field, value)
                where, params = field.get_db_prep_lookup(lookup_type, value)
                return gwc % tuple(where), params
            else:
                raise TypeError('Invalid lookup type: %r' % lookup_type)
        else:
            # If not a GeometryField, call the `make_atom` from the 
            # base class.
            return super(GeoWhereNode, self).make_atom(child, qn)
