from django.db.backends.postgresql.schema import DatabaseSchemaEditor
from django.db.models.expressions import Col, Func


class PostGISSchemaEditor(DatabaseSchemaEditor):
    geom_index_type = "GIST"
    geom_index_ops_nd = "GIST_GEOMETRY_OPS_ND"
    rast_index_template = "ST_ConvexHull(%(expressions)s)"

    sql_alter_column_to_3d = (
        "ALTER COLUMN %(column)s TYPE %(type)s USING ST_Force3D(%(column)s)::%(type)s"
    )
    sql_alter_column_to_2d = (
        "ALTER COLUMN %(column)s TYPE %(type)s USING ST_Force2D(%(column)s)::%(type)s"
    )

    def geo_quote_name(self, name):
        return self.connection.ops.geo_quote_name(name)

    def _field_should_be_indexed(self, model, field):
        if getattr(field, "spatial_index", False):
            return True
        return super()._field_should_be_indexed(model, field)

    def _create_index_sql(self, model, *, fields=None, **kwargs):
        if fields is None or len(fields) != 1 or not hasattr(fields[0], "geodetic"):
            return super()._create_index_sql(model, fields=fields, **kwargs)

        field = fields[0]
        expressions = None
        opclasses = None
        if field.geom_type == "RASTER":
            # For raster fields, wrap index creation SQL statement with ST_ConvexHull.
            # Indexes on raster columns are based on the convex hull of the raster.
            expressions = Func(Col(None, field), template=self.rast_index_template)
            fields = None
        elif field.dim > 2 and not field.geography:
            # Use "nd" ops which are fast on multidimensional cases
            opclasses = [self.geom_index_ops_nd]
        name = kwargs.get("name")
        if not name:
            name = self._create_index_name(model._meta.db_table, [field.column], "_id")

        return super()._create_index_sql(
            model,
            fields=fields,
            name=name,
            using=" USING %s" % self.geom_index_type,
            opclasses=opclasses,
            expressions=expressions,
        )

    def _alter_column_type_sql(self, table, old_field, new_field, new_type):
        """
        Special case when dimension changed.
        """
        if not hasattr(old_field, "dim") or not hasattr(new_field, "dim"):
            return super()._alter_column_type_sql(table, old_field, new_field, new_type)

        if old_field.dim == 2 and new_field.dim == 3:
            sql_alter = self.sql_alter_column_to_3d
        elif old_field.dim == 3 and new_field.dim == 2:
            sql_alter = self.sql_alter_column_to_2d
        else:
            sql_alter = self.sql_alter_column_type
        return (
            (
                sql_alter
                % {
                    "column": self.quote_name(new_field.column),
                    "type": new_type,
                },
                [],
            ),
            [],
        )
