from django.contrib.gis.db.models import GeometryField
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

        return self._create_spatial_index_sql(model, fields[0], **kwargs)

    def _alter_column_type_sql(
        self, table, old_field, new_field, new_type, old_collation, new_collation
    ):
        """
        Special case when dimension changed.
        """
        if not hasattr(old_field, "dim") or not hasattr(new_field, "dim"):
            return super()._alter_column_type_sql(
                table, old_field, new_field, new_type, old_collation, new_collation
            )

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
                    "collation": "",
                },
                [],
            ),
            [],
        )

    def _alter_field(
        self,
        model,
        old_field,
        new_field,
        old_type,
        new_type,
        old_db_params,
        new_db_params,
        strict=False,
    ):
        super()._alter_field(
            model,
            old_field,
            new_field,
            old_type,
            new_type,
            old_db_params,
            new_db_params,
            strict=strict,
        )

        old_field_spatial_index = (
            isinstance(old_field, GeometryField) and old_field.spatial_index
        )
        new_field_spatial_index = (
            isinstance(new_field, GeometryField) and new_field.spatial_index
        )
        if not old_field_spatial_index and new_field_spatial_index:
            self.execute(self._create_spatial_index_sql(model, new_field))
        elif old_field_spatial_index and not new_field_spatial_index:
            self.execute(self._delete_spatial_index_sql(model, old_field))

    def _create_spatial_index_name(self, model, field):
        return self._create_index_name(model._meta.db_table, [field.column], "_id")

    def _create_spatial_index_sql(self, model, field, **kwargs):
        expressions = None
        opclasses = None
        fields = [field]
        if field.geom_type == "RASTER":
            # For raster fields, wrap index creation SQL statement with ST_ConvexHull.
            # Indexes on raster columns are based on the convex hull of the raster.
            expressions = Func(Col(None, field), template=self.rast_index_template)
            fields = None
        elif field.dim > 2 and not field.geography:
            # Use "nd" ops which are fast on multidimensional cases
            opclasses = [self.geom_index_ops_nd]
        if not (name := kwargs.get("name")):
            name = self._create_spatial_index_name(model, field)

        return super()._create_index_sql(
            model,
            fields=fields,
            name=name,
            using=" USING %s" % self.geom_index_type,
            opclasses=opclasses,
            expressions=expressions,
        )

    def _delete_spatial_index_sql(self, model, field):
        index_name = self._create_spatial_index_name(model, field)
        return self._delete_index_sql(model, index_name)
