import logging

from django.contrib.gis.db.models import GeometryField
from django.db import OperationalError
from django.db.backends.mysql.schema import DatabaseSchemaEditor

logger = logging.getLogger("django.contrib.gis")


class MySQLGISSchemaEditor(DatabaseSchemaEditor):
    sql_add_spatial_index = "CREATE SPATIAL INDEX %(index)s ON %(table)s(%(column)s)"

    def skip_default(self, field):
        # Geometry fields are stored as BLOB/TEXT, for which MySQL < 8.0.13
        # doesn't support defaults.
        if (
            isinstance(field, GeometryField)
            and not self._supports_limited_data_type_defaults
        ):
            return True
        return super().skip_default(field)

    def quote_value(self, value):
        if isinstance(value, self.connection.ops.Adapter):
            return super().quote_value(str(value))
        return super().quote_value(value)

    def _field_indexes_sql(self, model, field):
        if isinstance(field, GeometryField) and field.spatial_index and not field.null:
            with self.connection.cursor() as cursor:
                supports_spatial_index = (
                    self.connection.introspection.supports_spatial_index(
                        cursor, model._meta.db_table
                    )
                )
            qn = self.connection.ops.quote_name
            sql = self.sql_add_spatial_index % {
                "index": qn(self._create_spatial_index_name(model, field)),
                "table": qn(model._meta.db_table),
                "column": qn(field.column),
            }
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
        if isinstance(field, GeometryField) and field.spatial_index and not field.null:
            index_name = self._create_spatial_index_name(model, field)
            sql = self._delete_index_sql(model, index_name)
            try:
                self.execute(sql)
            except OperationalError:
                logger.error(
                    "Couldn't remove spatial index: %s (may be expected "
                    "if your storage engine doesn't support them).",
                    sql,
                )

        super().remove_field(model, field)

    def _create_spatial_index_name(self, model, field):
        return "%s_%s_id" % (model._meta.db_table, field.column)
