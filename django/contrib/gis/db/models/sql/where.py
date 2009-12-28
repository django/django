from django.db.models.fields import Field, FieldDoesNotExist
from django.db.models.sql.constants import LOOKUP_SEP
from django.db.models.sql.expressions import SQLEvaluator
from django.db.models.sql.where import Constraint, WhereNode
from django.contrib.gis.db.models.fields import GeometryField

class GeoConstraint(Constraint):
    """
    This subclass overrides `process` to better handle geographic SQL
    construction.
    """
    def __init__(self, init_constraint):
        self.alias = init_constraint.alias
        self.col = init_constraint.col
        self.field = init_constraint.field

    def process(self, lookup_type, value, connection):
        if isinstance(value, SQLEvaluator):
            # Make sure the F Expression destination field exists, and
            # set an `srid` attribute with the same as that of the
            # destination.
            geo_fld = GeoWhereNode._check_geo_field(value.opts, value.expression.name)
            if not geo_fld:
                raise ValueError('No geographic field found in expression.')
            value.srid = geo_fld.srid
        db_type = self.field.db_type(connection=connection)
        params = self.field.get_db_prep_lookup(lookup_type, value, connection=connection)
        return (self.alias, self.col, db_type), params

class GeoWhereNode(WhereNode):
    """
    Used to represent the SQL where-clause for spatial databases --
    these are tied to the GeoQuery class that created it.
    """
    def add(self, data, connector):
        if isinstance(data, (list, tuple)):
            obj, lookup_type, value = data
            if ( isinstance(obj, Constraint) and
                 isinstance(obj.field, GeometryField) ):
                data = (GeoConstraint(obj), lookup_type, value)
        super(GeoWhereNode, self).add(data, connector)

    def make_atom(self, child, qn, connection):
        lvalue, lookup_type, value_annot, params_or_value = child
        if isinstance(lvalue, GeoConstraint):
            data, params = lvalue.process(lookup_type, params_or_value, connection)
            spatial_sql = connection.ops.spatial_lookup_sql(data, lookup_type, params_or_value, lvalue.field, qn)
            return spatial_sql, params
        else:
            return super(GeoWhereNode, self).make_atom(child, qn, connection)

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
