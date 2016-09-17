from django.db.backends.postgresql.schema import DatabaseSchemaEditor


class PostGISSchemaEditor(DatabaseSchemaEditor):
    geom_index_type = 'GIST'
    geom_index_ops_nd = 'GIST_GEOMETRY_OPS_ND'
    rast_index_wrapper = 'ST_ConvexHull(%s)'

    def geo_quote_name(self, name):
        return self.connection.ops.geo_quote_name(name)

    def _field_should_be_indexed(self, model, field):
        if getattr(field, 'spatial_index', False):
            return True
        return super(PostGISSchemaEditor, self)._field_should_be_indexed(model, field)

    def _create_index_sql(self, model, fields, suffix="", sql=None):
        if len(fields) != 1 or not hasattr(fields[0], 'geodetic'):
            return super(PostGISSchemaEditor, self)._create_index_sql(model, fields, suffix=suffix, sql=sql)

        field = fields[0]
        field_column = self.quote_name(field.column)

        if field.geom_type == 'RASTER':
            # For raster fields, wrap index creation SQL statement with ST_ConvexHull.
            # Indexes on raster columns are based on the convex hull of the raster.
            field_column = self.rast_index_wrapper % field_column
        elif field.dim > 2 and not field.geography:
            # Use "nd" ops which are fast on multidimensional cases
            field_column = "%s %s" % (field_column, self.geom_index_ops_nd)

        return self.sql_create_index % {
            "name": self.quote_name('%s_%s_id' % (model._meta.db_table, field.column)),
            "table": self.quote_name(model._meta.db_table),
            "using": "USING %s" % self.geom_index_type,
            "columns": field_column,
            "extra": '',
        }
