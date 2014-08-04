from django.db.backends.postgresql_psycopg2.schema import DatabaseSchemaEditor


class PostGISSchemaEditor(DatabaseSchemaEditor):
    geom_index_type = 'GIST'
    geom_index_ops = 'GIST_GEOMETRY_OPS'
    geom_index_ops_nd = 'GIST_GEOMETRY_OPS_ND'

    sql_add_geometry_column = "SELECT AddGeometryColumn(%(table)s, %(column)s, %(srid)s, %(geom_type)s, %(dim)s)"
    sql_drop_geometry_column = "SELECT DropGeometryColumn(%(table)s, %(column)s)"
    sql_alter_geometry_column_not_null = "ALTER TABLE %(table)s ALTER COLUMN %(column)s SET NOT NULL"
    sql_add_spatial_index = "CREATE INDEX %(index)s ON %(table)s USING %(index_type)s (%(column)s %(ops)s)"
    sql_clear_geometry_columns = "DELETE FROM geometry_columns WHERE f_table_name = %(table)s"

    def __init__(self, *args, **kwargs):
        super(PostGISSchemaEditor, self).__init__(*args, **kwargs)
        self.geometry_sql = []

    def geo_quote_name(self, name):
        return self.connection.ops.geo_quote_name(name)

    def column_sql(self, model, field, include_default=False):
        from django.contrib.gis.db.models.fields import GeometryField
        if not isinstance(field, GeometryField):
            return super(PostGISSchemaEditor, self).column_sql(model, field, include_default)

        if field.geography or self.connection.ops.geometry:
            # Geography and Geometry (PostGIS 2.0+) columns are
            # created normally.
            column_sql = super(PostGISSchemaEditor, self).column_sql(model, field, include_default)
        else:
            column_sql = None, None
            # Geometry columns are created by the `AddGeometryColumn`
            # stored procedure.
            self.geometry_sql.append(
                self.sql_add_geometry_column % {
                    "table": self.geo_quote_name(model._meta.db_table),
                    "column": self.geo_quote_name(field.column),
                    "srid": field.srid,
                    "geom_type": self.geo_quote_name(field.geom_type),
                    "dim": field.dim,
                }
            )

            if not field.null:
                self.geometry_sql.append(
                    self.sql_alter_geometry_column_not_null % {
                        "table": self.quote_name(model._meta.db_table),
                        "column": self.quote_name(field.column),
                    }
                )

        if field.spatial_index:
            # Spatial indexes created the same way for both Geometry and
            # Geography columns.
            # PostGIS 2.0 does not support GIST_GEOMETRY_OPS. So, on 1.5
            # we use GIST_GEOMETRY_OPS, on 2.0 we use either "nd" ops
            # which are fast on multidimensional cases, or just plain
            # gist index for the 2d case.
            if field.geography:
                index_ops = ''
            elif self.connection.ops.geometry:
                if field.dim > 2:
                    index_ops = self.geom_index_ops_nd
                else:
                    index_ops = ''
            else:
                index_ops = self.geom_index_ops
            self.geometry_sql.append(
                self.sql_add_spatial_index % {
                    "index": self.quote_name('%s_%s_id' % (model._meta.db_table, field.column)),
                    "table": self.quote_name(model._meta.db_table),
                    "column": self.quote_name(field.column),
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

    def remove_field(self, model, field):
        from django.contrib.gis.db.models.fields import GeometryField
        if not isinstance(field, GeometryField) or \
           self.connection.ops.spatial_version > (2, 0) or \
           field.geography:
            super(PostGISSchemaEditor, self).remove_field(model, field)
        else:
            self.execute(
                self.sql_drop_geometry_column % {
                    "table": self.geo_quote_name(model._meta.db_table),
                    "column": self.geo_quote_name(field.column),
                }
            )
