from django.db import connection
from django.db.models.fields import Field, FieldDoesNotExist
from django.db.models.sql.constants import LOOKUP_SEP
from django.db.models.sql.expressions import SQLEvaluator
from django.db.models.sql.where import WhereNode
from django.contrib.gis.db.backend import get_geo_where_clause, SpatialBackend
from django.contrib.gis.db.models.fields import GeometryField
qn = connection.ops.quote_name

class GeoAnnotation(object):
    """
    The annotation used for GeometryFields; basically a placeholder
    for metadata needed by the `get_geo_where_clause` of the spatial
    backend.
    """
    def __init__(self, field, value, where):
        self.geodetic = field.geodetic
        self.geom_type = field.geom_type
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
        field to generate the spatial SQL.
        """
        if not isinstance(data, (list, tuple)):
            return super(WhereNode, self).add(data, connector)

        obj, lookup_type, value = data
        col, field = obj.col, obj.field

        if not hasattr(field, "geom_type"):
            # Not a geographic field, so call `WhereNode.add`.
            return super(GeoWhereNode, self).add(data, connector)
        else:
            if isinstance(value, SQLEvaluator):
                # Getting the geographic field to compare with from the expression.
                geo_fld = self._check_geo_field(value.opts, value.expression.name)
                if not geo_fld:
                    raise ValueError('No geographic field found in expression.')

                # Get the SRID of the geometry field that the expression was meant 
                # to operate on -- it's needed to determine whether transformation 
                # SQL is necessary.
                srid = geo_fld.srid

                # Getting the quoted representation of the geometry column that
                # the expression is operating on.
                geo_col = '%s.%s' % tuple(map(qn, value.cols[value.expression]))

                # If it's in a different SRID, we'll need to wrap in 
                # transformation SQL.
                if not srid is None and srid != field.srid and SpatialBackend.transform:
                    placeholder = '%s(%%s, %s)' % (SpatialBackend.transform, field.srid)
                else:
                    placeholder = '%s'

                # Setting these up as if we had called `field.get_db_prep_lookup()`.
                where =  [placeholder % geo_col]
                params = ()
            else:
                # `GeometryField.get_db_prep_lookup` returns a where clause
                # substitution array in addition to the parameters.
                where, params = field.get_db_prep_lookup(lookup_type, value)

            # The annotation will be a `GeoAnnotation` object that
            # will contain the necessary geometry field metadata for
            # the `get_geo_where_clause` to construct the appropriate
            # spatial SQL when `make_atom` is called.
            annotation = GeoAnnotation(field, value, where)
            return super(WhereNode, self).add(((obj.alias, col, field.db_type()), lookup_type, annotation, params), connector)

    def make_atom(self, child, qn):
        obj, lookup_type, value_annot, params = child

        if isinstance(value_annot, GeoAnnotation):
            if lookup_type in SpatialBackend.gis_terms:
                # Getting the geographic where clause; substitution parameters
                # will be populated in the GeoFieldSQL object returned by the
                # GeometryField.
                alias, col, db_type = obj
                gwc = get_geo_where_clause(alias, col, lookup_type, value_annot)
                return gwc % value_annot.where, params
            else:
                raise TypeError('Invalid lookup type: %r' % lookup_type)
        else:
            # If not a GeometryField, call the `make_atom` from the 
            # base class.
            return super(GeoWhereNode, self).make_atom(child, qn)

    @classmethod
    def _check_geo_field(cls, opts, lookup):
        """
        Utility for checking the given lookup with the given model options.  
        The lookup is a string either specifying the geographic field, e.g.
        'point, 'the_geom', or a related lookup on a geographic field like
        'address__point'.

        If a GeometryField exists according to the given lookup on the model
        options, it will be returned.  Otherwise returns None.
        """
        # This takes into account the situation where the lookup is a
        # lookup to a related geographic field, e.g., 'address__point'.
        field_list = lookup.split(LOOKUP_SEP)

        # Reversing so list operates like a queue of related lookups,
        # and popping the top lookup.
        field_list.reverse()
        fld_name = field_list.pop()

        try:
            geo_fld = opts.get_field(fld_name)
            # If the field list is still around, then it means that the
            # lookup was for a geometry field across a relationship --
            # thus we keep on getting the related model options and the
            # model field associated with the next field in the list 
            # until there's no more left.
            while len(field_list):
                opts = geo_fld.rel.to._meta
                geo_fld = opts.get_field(field_list.pop())
        except (FieldDoesNotExist, AttributeError):
            return False

        # Finally, make sure we got a Geographic field and return.
        if isinstance(geo_fld, GeometryField):
            return geo_fld
        else:
            return False
