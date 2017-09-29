from django.db.backends.sqlite3.schema import DatabaseSchemaEditor
from django.db.utils import DatabaseError


class SpatialiteSchemaEditor(DatabaseSchemaEditor):
    sql_add_geometry_column = (
        "SELECT AddGeometryColumn(%(table)s, %(column)s, %(srid)s, "
        "%(geom_type)s, %(dim)s, %(null)s)"
    )
    sql_add_spatial_index = "SELECT CreateSpatialIndex(%(table)s, %(column)s)"
    sql_drop_spatial_index = "DROP TABLE idx_%(table)s_%(column)s"
    sql_recover_geometry_metadata = (
        "SELECT RecoverGeometryColumn(%(table)s, %(column)s, %(srid)s, "
        "%(geom_type)s, %(dim)s)"
    )
    sql_remove_geometry_metadata = "SELECT DiscardGeometryColumn(%(table)s, %(column)s)"
    sql_discard_geometry_columns = "DELETE FROM %(geom_table)s WHERE f_table_name = %(table)s"
    sql_update_geometry_columns = (
        "UPDATE %(geom_table)s SET f_table_name = %(new_table)s "
        "WHERE f_table_name = %(old_table)s"
    )

    geometry_tables = [
        "geometry_columns",
        "geometry_columns_auth",
        "geometry_columns_time",
        "geometry_columns_statistics",
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.geometry_sql = []

    def geo_quote_name(self, name):
        return self.connection.ops.geo_quote_name(name)

    def column_sql(self, model, field, include_default=False):
        from django.contrib.gis.db.models.fields import GeometryField
        if not isinstance(field, GeometryField):
            return super().column_sql(model, field, include_default)

        # Geometry columns are created by the `AddGeometryColumn` function
        self.geometry_sql.append(
            self.sql_add_geometry_column % {
                "table": self.geo_quote_name(model._meta.db_table),
                "column": self.geo_quote_name(field.column),
                "srid": field.srid,
                "geom_type": self.geo_quote_name(field.geom_type),
                "dim": field.dim,
                "null": int(not field.null),
            }
        )

        if field.spatial_index:
            self.geometry_sql.append(
                self.sql_add_spatial_index % {
                    "table": self.quote_name(model._meta.db_table),
                    "column": self.quote_name(field.column),
                }
            )
        return None, None

    def remove_geometry_metadata(self, model, field):
        self.execute(
            self.sql_remove_geometry_metadata % {
                "table": self.quote_name(model._meta.db_table),
                "column": self.quote_name(field.column),
            }
        )
        self.execute(
            self.sql_drop_spatial_index % {
                "table": model._meta.db_table,
                "column": field.column,
            }
        )

    def create_model(self, model):
        super().create_model(model)
        # Create geometry columns
        for sql in self.geometry_sql:
            self.execute(sql)
        self.geometry_sql = []

    def delete_model(self, model, **kwargs):
        from django.contrib.gis.db.models.fields import GeometryField
        # Drop spatial metadata (dropping the table does not automatically remove them)
        for field in model._meta.local_fields:
            if isinstance(field, GeometryField):
                self.remove_geometry_metadata(model, field)
        # Make sure all geom stuff is gone
        for geom_table in self.geometry_tables:
            try:
                self.execute(
                    self.sql_discard_geometry_columns % {
                        "geom_table": geom_table,
                        "table": self.quote_name(model._meta.db_table),
                    }
                )
            except DatabaseError:
                pass
        super().delete_model(model, **kwargs)

    def add_field(self, model, field):
        from django.contrib.gis.db.models.fields import GeometryField
        if isinstance(field, GeometryField):
            # Populate self.geometry_sql
            self.column_sql(model, field)
            for sql in self.geometry_sql:
                self.execute(sql)
            self.geometry_sql = []
        else:
            super().add_field(model, field)

    def remove_field(self, model, field):
        from django.contrib.gis.db.models.fields import GeometryField
        # NOTE: If the field is a geometry field, the table is just recreated,
        # the parent's remove_field can't be used cause it will skip the
        # recreation if the field does not have a database type. Geometry fields
        # do not have a db type cause they are added and removed via stored
        # procedures.
        if isinstance(field, GeometryField):
            self._remake_table(model, delete_field=field)
        else:
            super().remove_field(model, field)

    def alter_db_table(self, model, old_db_table, new_db_table):
        from django.contrib.gis.db.models.fields import GeometryField
        # Remove geometry-ness from temp table
        for field in model._meta.local_fields:
            if isinstance(field, GeometryField):
                self.execute(
                    self.sql_remove_geometry_metadata % {
                        "table": self.quote_name(old_db_table),
                        "column": self.quote_name(field.column),
                    }
                )
        # Alter table
        super().alter_db_table(model, old_db_table, new_db_table)
        # Repoint any straggler names
        for geom_table in self.geometry_tables:
            try:
                self.execute(
                    self.sql_update_geometry_columns % {
                        "geom_table": geom_table,
                        "old_table": self.quote_name(old_db_table),
                        "new_table": self.quote_name(new_db_table),
                    }
                )
            except DatabaseError:
                pass
        # Re-add geometry-ness and rename spatial index tables
        for field in model._meta.local_fields:
            if isinstance(field, GeometryField):
                self.execute(self.sql_recover_geometry_metadata % {
                    "table": self.geo_quote_name(new_db_table),
                    "column": self.geo_quote_name(field.column),
                    "srid": field.srid,
                    "geom_type": self.geo_quote_name(field.geom_type),
                    "dim": field.dim,
                })
            if getattr(field, 'spatial_index', False):
                self.execute(self.sql_rename_table % {
                    "old_table": self.quote_name("idx_%s_%s" % (old_db_table, field.column)),
                    "new_table": self.quote_name("idx_%s_%s" % (new_db_table, field.column)),
                })
