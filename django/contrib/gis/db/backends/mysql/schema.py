import logging

from django.contrib.gis.db.models import GeometryField
from django.db import OperationalError
from django.db.backends.mysql.schema import DatabaseSchemaEditor

logger = logging.getLogger("django.contrib.gis")


class MySQLGISSchemaEditor(DatabaseSchemaEditor):
    """
    MySQL GIS schema editor with proper SRID + spatial index handling.
    """

    # ✅ CRITICAL FIX: enforce InnoDB (required for SRID support)
    sql_create_table = "CREATE TABLE %(table)s (%(definition)s) ENGINE=InnoDB"

    sql_add_spatial_index = "CREATE SPATIAL INDEX %(index)s " "ON %(table)s(%(column)s)"

    # -------------------------------
    # Helpers
    # -------------------------------
    def _is_spatial_indexable(self, field):
        return (
            isinstance(field, GeometryField) and field.spatial_index and not field.null
        )

    # -------------------------------
    # Model creation
    # -------------------------------
    def create_model(self, model):
        has_geometry = any(isinstance(f, GeometryField) for f in model._meta.fields)

        if has_geometry:
            logger.debug(
                "Creating model %s with GeometryField support",
                model._meta.db_table,
            )

        return super().create_model(model)

    # -------------------------------
    # Field removal
    # -------------------------------
    def remove_field(self, model, field):
        if self._is_spatial_indexable(field):
            sql = self._delete_spatial_index_sql(model, field)
            try:
                self.execute(sql)
            except OperationalError:
                logger.error(
                    "Couldn't remove spatial index: %s "
                    "(may be expected if unsupported).",
                    sql,
                )

        super().remove_field(model, field)

    # -------------------------------
    # Field alteration
    # -------------------------------
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

        old_spatial = self._is_spatial_indexable(old_field)
        new_spatial = self._is_spatial_indexable(new_field)

        if (
            self.connection.mysql_version >= (8, 0)
            and not self.connection.mysql_is_mariadb
            and self._storage_engine_supports_srid()
        ):
            self._handle_srid_change(model, old_field, new_field)

        if not old_spatial and new_spatial:
            sql = self._create_spatial_index_sql(model, new_field)
            if sql:
                self.execute(sql)

        elif old_spatial and not new_spatial:
            self.execute(self._delete_spatial_index_sql(model, old_field))

    # -------------------------------
    # SRID handling
    # -------------------------------
    def _handle_srid_change(self, model, old_field, new_field):
        if (
            isinstance(old_field, GeometryField)
            and isinstance(new_field, GeometryField)
            and old_field.srid != new_field.srid
            and new_field.srid is not None
        ):
            sql = self._alter_srid_sql(model, new_field)
            try:
                self.execute(sql)
            except OperationalError as e:
                logger.warning(
                    "Could not add SRID constraint to %s: %s",
                    new_field.name,
                    e,
                )

    def _alter_srid_sql(self, model, field):
        table = model._meta.db_table
        column = field.column
        geom_type = field.geom_type

        column_type = f"{geom_type} SRID {field.srid}" if field.srid else geom_type

        return self.sql_alter_column % {
            "table": self.quote_name(table),
            "changes": self.sql_alter_column_type
            % {
                "column": self.quote_name(column),
                "type": column_type,
            },
        }

    # -------------------------------
    # Spatial index handling
    # -------------------------------
    def _create_spatial_index_name(self, model, field):
        if self.connection.mysql_version >= (8, 0):
            return f"{model._meta.db_table}_{field.column}_spatial"
        return f"{model._meta.db_table}_{field.column}_id"

    def _create_spatial_index_sql(self, model, field):
        index_name = self._create_spatial_index_name(model, field)

        if self._index_exists(model._meta.db_table, index_name):
            return None

        qn = self.connection.ops.quote_name
        return self.sql_add_spatial_index % {
            "index": qn(index_name),
            "table": qn(model._meta.db_table),
            "column": qn(field.column),
        }

    def _delete_spatial_index_sql(self, model, field):
        index_name = self._create_spatial_index_name(model, field)
        return self._delete_index_sql(model, index_name)

    # -------------------------------
    # Field addition
    # -------------------------------
    def add_field(self, model, field):
        if (
            isinstance(field, GeometryField)
            and self.connection.mysql_version >= (8, 0)
            and not self.connection.mysql_is_mariadb
            and field.srid
            and self._storage_engine_supports_srid()
        ):
            self._current_field_srid = field.srid

        super().add_field(model, field)

        if hasattr(self, "_current_field_srid"):
            delattr(self, "_current_field_srid")

        if self._is_spatial_indexable(field):
            with self.connection.cursor() as cursor:
                supports = self.connection.introspection.supports_spatial_index(
                    cursor,
                    model._meta.db_table,
                )
            if supports:
                sql = self._create_spatial_index_sql(model, field)
                if sql:
                    self.execute(sql)

    # -------------------------------
    # Column SQL customization
    # -------------------------------
    def _column_sql(self, model, field, include_default=False):
        sql = super()._column_sql(model, field, include_default)

        if isinstance(field, GeometryField):
            import re

            def _clean_invalid_srid(match):
                """Remove SRID if it is <= 0."""
                value = int(match.group().split()[-1])
                return "" if value <= 0 else match.group()

            # ✅ Remove invalid SRID (<= 0)
            sql = re.sub(
                r"\s+SRID\s+-?\d+",
                _clean_invalid_srid,
                sql,
                flags=re.IGNORECASE,
            )

            # ✅ Add valid SRID if needed (MySQL 8+ only)
            if (
                self.connection.mysql_version >= (8, 0)
                and not self.connection.mysql_is_mariadb
                and self._storage_engine_supports_srid()
            ):
                srid = getattr(self, "_current_field_srid", field.srid)

                if srid and srid > 0 and "SRID" not in sql.upper():
                    geom_type = field.geom_type
                    sql = sql.replace(
                        geom_type,
                        f"{geom_type} SRID {srid}",
                    )

        return sql

    # -------------------------------
    # Utilities
    # -------------------------------
    def _storage_engine_supports_srid(self):
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("SELECT @@default_storage_engine")
                engine = cursor.fetchone()[0]
                return engine == "InnoDB"
        except Exception:
            return False

    def _index_exists(self, table_name, index_name):
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
