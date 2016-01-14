from django.db.backends.postgresql.schema import DatabaseSchemaEditor


class PostGISSchemaEditor(DatabaseSchemaEditor):
    geom_index_type = 'GIST'
    geom_index_ops_nd = 'GIST_GEOMETRY_OPS_ND'
    rast_index_wrapper = 'ST_ConvexHull(%s)'

    sql_add_spatial_index = "CREATE INDEX %(index)s ON %(table)s USING %(index_type)s (%(column)s %(ops)s)"
    sql_clear_geometry_columns = "DELETE FROM geometry_columns WHERE f_table_name = %(table)s"

    def __init__(self, *args, **kwargs):
        super(PostGISSchemaEditor, self).__init__(*args, **kwargs)
        self.geometry_sql = []

    def geo_quote_name(self, name):
        return self.connection.ops.geo_quote_name(name)

    def column_sql(self, model, field, include_default=False):
        from django.contrib.gis.db.models.fields import BaseSpatialField
        if not isinstance(field, BaseSpatialField):
            return super(PostGISSchemaEditor, self).column_sql(model, field, include_default)

        column_sql = super(PostGISSchemaEditor, self).column_sql(model, field, include_default)

        if field.spatial_index:
            # Spatial indexes created the same way for both Geometry and
            # Geography columns.
            field_column = self.quote_name(field.column)
            if field.geom_type == 'RASTER':
                # For raster fields, wrap index creation SQL statement with ST_ConvexHull.
                # Indexes on raster columns are based on the convex hull of the raster.
                field_column = self.rast_index_wrapper % field_column
                index_ops = ''
            elif field.geography:
                index_ops = ''
            else:
                # Use either "nd" ops  which are fast on multidimensional cases
                # or just plain gist index for the 2d case.
                if field.dim > 2:
                    index_ops = self.geom_index_ops_nd
                else:
                    index_ops = ''
            self.geometry_sql.append(
                self.sql_add_spatial_index % {
                    "index": self.quote_name('%s_%s_id' % (model._meta.db_table, field.column)),
                    "table": self.quote_name(model._meta.db_table),
                    "column": field_column,
                    "index_type": self.geom_index_type,
                    "ops": index_ops,
                }
            )
        return column_sql

    def create_model(self, model):
        super(PostGISSchemaEditor, self).create_model(model)
        # Create geometry columns
        for sql in self.geometry_sql:
            self.execute(sql)
        self.geometry_sql = []

    def delete_model(self, model):
        super(PostGISSchemaEditor, self).delete_model(model)
        self.execute(self.sql_clear_geometry_columns % {
            "table": self.geo_quote_name(model._meta.db_table),
        })

    def add_field(self, model, field):
        super(PostGISSchemaEditor, self).add_field(model, field)
        # Create geometry columns
        for sql in self.geometry_sql:
            self.execute(sql)
        self.geometry_sql = []
