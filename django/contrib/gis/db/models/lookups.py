from django.db.models.lookups import Lookup
from django.db.models.expressions import ExpressionNode, F


class GISLookup(Lookup):
    def as_sql(self, qn, connection):
        # We use the same approach as was used by GeoWhereNode. It would
        # be a good idea to upgrade GIS to use similar code that is used
        # for other lookups.
        if isinstance(self.rhs, F):
            # Make sure the F Expression destination field exists, and
            # set an `srid` attribute with the same as that of the
            # destination.
            geo_fld = self.rhs.field
            if not hasattr(geo_fld, 'srid'):
                raise ValueError('No geographic field found in expression.')
            self.rhs.srid = geo_fld.srid
        elif isinstance(self.rhs, ExpressionNode):
            raise ValueError('Complex expressions not supported for GeometryField')
        db_type = self.lhs.output_type.db_type(connection=connection)
        params = self.lhs.output_type.get_db_prep_lookup(
            self.lookup_name, self.rhs, connection=connection)
        lhs_sql, lhs_params = self.process_lhs(qn, connection)
        # lhs_params not currently supported.
        assert not lhs_params
        data = (lhs_sql, db_type)
        spatial_sql, spatial_params = connection.ops.spatial_lookup_sql(
            data, self.lookup_name, self.rhs, self.lhs.output_type, qn)
        return spatial_sql, spatial_params + params
