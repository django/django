from django.db.models.constants import LOOKUP_SEP
from django.db.models.fields import FieldDoesNotExist
from django.db.models.lookups import Lookup
from django.db.models.sql.expressions import SQLEvaluator


class GISLookup(Lookup):
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
        from django.contrib.gis.db.models.fields import GeometryField
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

    def as_sql(self, qn, connection):
        # We use the same approach as was used by GeoWhereNode. It would
        # be a good idea to upgrade GIS to use similar code that is used
        # for other lookups.
        if isinstance(self.rhs, SQLEvaluator):
            # Make sure the F Expression destination field exists, and
            # set an `srid` attribute with the same as that of the
            # destination.
            geo_fld = self._check_geo_field(self.rhs.opts, self.rhs.expression.name)
            if not geo_fld:
                raise ValueError('No geographic field found in expression.')
            self.rhs.srid = geo_fld.srid
        db_type = self.lhs.output_field.db_type(connection=connection)
        params = self.lhs.output_field.get_db_prep_lookup(
            self.lookup_name, self.rhs, connection=connection)
        lhs_sql, lhs_params = self.process_lhs(qn, connection)
        # lhs_params not currently supported.
        assert not lhs_params
        data = (lhs_sql, db_type)
        spatial_sql, spatial_params = connection.ops.spatial_lookup_sql(
            data, self.lookup_name, self.rhs, self.lhs.output_field, qn)
        return spatial_sql, spatial_params + params
