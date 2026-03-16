import logging

from django.contrib.gis.db.models import GeometryField
from django.db import OperationalError
from django.db.backends.mysql.schema import DatabaseSchemaEditor

logger = logging.getLogger("django.contrib.gis")


class MySQLGISSchemaEditor(DatabaseSchemaEditor):
    sql_add_spatial_index = "CREATE SPATIAL INDEX %(index)s ON %(table)s(%(column)s)"

    def quote_value(self, value):
        if isinstance(value, self.connection.ops.Adapter):
            return super().quote_value(str(value))
        return super().quote_value(value)

    def _field_indexes_sql(self, model, field):
        """Return SQL for creating indexes on a field."""
        if isinstance(field, GeometryField) and field.spatial_index and not field.null:
            with self.connection.cursor() as cursor:
                supports_spatial_index = (
                    self.connection.introspection.supports_spatial_index(
                        cursor, model._meta.db_table
                    )
                )
            sql = self._create_spatial_index_sql(model, field)
            if supports_spatial_index:
                return [sql]
            else:
                logger.error(
                    f"Cannot create SPATIAL INDEX {sql}. Only MyISAM, Aria, and InnoDB "
                    f"support them.",
                )
                return []
        return super()._field_indexes_sql(model, field)

    def remove_field(self, model, field):
        """Remove a field and its spatial index if it exists."""
        if isinstance(field, GeometryField) and field.spatial_index and not field.null:
            sql = self._delete_spatial_index_sql(model, field)
            try:
                self.execute(sql)
            except OperationalError:
                logger.error(
                    "Couldn't remove spatial index: %s (may be expected "
                    "if your storage engine doesn't support them).",
                    sql,
                )

        super().remove_field(model, field)

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
        """Handle alterations to fields, including spatial index changes."""
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

        # Handle spatial index changes
        old_field_spatial_index = (
            isinstance(old_field, GeometryField)
            and old_field.spatial_index
            and not old_field.null
        )
        new_field_spatial_index = (
            isinstance(new_field, GeometryField)
            and new_field.spatial_index
            and not new_field.null
        )

        # For MySQL 8.0+, we also need to handle SRID changes
        if (
            self.connection.mysql_version >= (8, 0)
            and not self.connection.mysql_is_mariadb
        ):
            self._handle_srid_change(model, old_field, new_field)

        # Handle spatial index creation/removal
        if not old_field_spatial_index and new_field_spatial_index:
            self.execute(self._create_spatial_index_sql(model, new_field))
        elif old_field_spatial_index and not new_field_spatial_index:
            self.execute(self._delete_spatial_index_sql(model, old_field))

    def _handle_srid_change(self, model, old_field, new_field):
        """
        Handle SRID changes for geometry fields in MySQL 8.0+.
        MySQL 8.0 allows SRID constraints on geometry columns.
        """
        if (
            isinstance(old_field, GeometryField)
            and isinstance(new_field, GeometryField)
            and old_field.srid != new_field.srid
        ):

            # For MySQL 8.0+, modify column to enforce SRID constraint
            if new_field.srid is not None:
                # Alter column to add SRID constraint
                sql = self._alter_srid_sql(model, new_field)
                try:
                    self.execute(sql)
                except OperationalError as e:
                    logger.warning(
                        f"Could not add SRID constraint to {new_field.name}: {e}"
                    )

    def _alter_srid_sql(self, model, field):
        """
        Generate SQL to add SRID constraint to a column.

        Works with MySQL 8.0+ only.
        """
        table = model._meta.db_table
        column = field.column
        geom_type = field.geom_type

        # MySQL 8.0 supports SRID constraint in column definition
        if field.srid:
            column_type = f"{geom_type} SRID {field.srid}"
        else:
            column_type = geom_type

        return self.sql_alter_column % {
            "table": self.quote_name(table),
            "changes": self.sql_alter_column_type
            % {
                "column": self.quote_name(column),
                "type": column_type,
            },
        }

    def _create_spatial_index_name(self, model, field):
        """Generate a name for a spatial index."""
        # For MySQL 8.0, we can use a more descriptive name
        if self.connection.mysql_version >= (8, 0):
            return f"{model._meta.db_table}_{field.column}_spatial"
        # Backward compatibility with older MySQL versions
        return f"{model._meta.db_table}_{field.column}_id"

    def _create_spatial_index_sql(self, model, field):
        """Generate SQL to create a spatial index, avoiding duplicates."""
        index_name = self._create_spatial_index_name(model, field)

        # Check if index already exists
        if self._index_exists(model._meta.db_table, index_name):
            return None  # Skip if index exists

        qn = self.connection.ops.quote_name
        return self.sql_add_spatial_index % {
            "index": qn(index_name),
            "table": qn(model._meta.db_table),
            "column": qn(field.column),
        }

    def _delete_spatial_index_sql(self, model, field):
        """Generate SQL to delete a spatial index."""
        index_name = self._create_spatial_index_name(model, field)
        return self._delete_index_sql(model, index_name)

    def add_field(self, model, field):
        """
        Add a field to the database. Enhanced for MySQL 8.0 SRID support.
        """
        # For MySQL 8.0 geometry fields with SRID, we need to ensure
        # the column is created with the SRID constraint
        if (
            isinstance(field, GeometryField)
            and self.connection.mysql_version >= (8, 0)
            and not self.connection.mysql_is_mariadb
            and field.srid
        ):

            # Temporarily store the SRID to use in column definition
            self._current_field_srid = field.srid

        super().add_field(model, field)

        # Clear temporary storage
        if hasattr(self, "_current_field_srid"):
            delattr(self, "_current_field_srid")

        # Create spatial index if needed
        if isinstance(field, GeometryField) and field.spatial_index and not field.null:
            with self.connection.cursor() as cursor:
                supports_spatial_index = (
                    self.connection.introspection.supports_spatial_index(
                        cursor, model._meta.db_table
                    )
                )
            if supports_spatial_index:
                sql = self._create_spatial_index_sql(model, field)
                if sql:  # Only execute if SQL is returned
                    self.execute(sql)

    def _column_sql(self, model, field, include_default=False):
        """
        Override to add SRID constraint for MySQL 8.0 geometry fields,
        but only if the storage engine supports it.
        """
        sql = super()._column_sql(model, field, include_default)

        # For MySQL 8.0 geometry fields with SRID, modify the column definition
        if (
            isinstance(field, GeometryField)
            and self.connection.mysql_version >= (8, 0)
            and not self.connection.mysql_is_mariadb
        ):

            # Check if storage engine supports SRID constraints
            supports_srid = self._storage_engine_supports_srid(model)

            srid = getattr(self, "_current_field_srid", field.srid)
            if srid and supports_srid:
                # Add SRID constraint to the column type
                if "SRID" not in sql.upper():
                    geom_type = field.geom_type
                    sql = sql.replace(geom_type, f"{geom_type} SRID {srid}")

        return sql

    def _storage_engine_supports_srid(self, model):
        """
        Check if the table's storage engine supports SRID constraints.
        InnoDB supports them, MyISAM does not.
        """
        with self.connection.cursor() as cursor:
            cursor.execute(
                "SELECT engine FROM information_schema.tables "
                "WHERE table_name = %s AND table_schema = DATABASE()",
                [model._meta.db_table],
            )
            result = cursor.fetchone()
            if result:
                engine = result[0]
                return engine == "InnoDB"
        return False

    def _index_exists(self, table_name, index_name):
        """Check if an index exists on a table."""
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM information_schema.statistics
                WHERE table_schema = DATABASE()
                    AND table_name = %s
                    AND index_name = %s
            """,
                [table_name, index_name],
            )
            return cursor.fetchone()[0] > 0
