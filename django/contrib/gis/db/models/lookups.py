from django.db.models.lookups import Lookup
from django.db.models.sql.expressions import SQLEvaluator


class GISLookup(Lookup):
    def as_sql(self, qn, connection):
        from django.contrib.gis.db.models.sql import GeoWhereNode
        # We use the same approach as was used by GeoWhereNode. It would
        # be a good idea to upgrade GIS to use similar code that is used
        # for other lookups.
        if isinstance(self.rhs, SQLEvaluator):
            # Make sure the F Expression destination field exists, and
            # set an `srid` attribute with the same as that of the
            # destination.
            geo_fld = GeoWhereNode._check_geo_field(self.rhs.opts, self.rhs.expression.name)
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
