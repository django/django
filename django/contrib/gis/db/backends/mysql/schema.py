import logging

from django.contrib.gis.db.models.fields import GeometryField
from django.db.backends.mysql.schema import DatabaseSchemaEditor
from django.db.utils import OperationalError

logger = logging.getLogger('django.contrib.gis')


class MySQLGISSchemaEditor(DatabaseSchemaEditor):
    sql_add_spatial_index = 'CREATE SPATIAL INDEX %(index)s ON %(table)s(%(column)s)'
    sql_drop_spatial_index = 'DROP INDEX %(index)s ON %(table)s'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.geometry_sql = []

    def skip_default(self, field):
        # Geometry fields are stored as BLOB/TEXT, for which MySQL < 8.0.13 and
        # MariaDB < 10.2.1 don't support defaults.
        if isinstance(field, GeometryField) and not self._supports_limited_data_type_defaults:
            return True
        return super().skip_default(field)

    def column_sql(self, model, field, include_default=False):
        column_sql = super().column_sql(model, field, include_default)
        # MySQL doesn't support spatial indexes on NULL columns
        if isinstance(field, GeometryField) and field.spatial_index and not field.null:
            qn = self.connection.ops.quote_name
            db_table = model._meta.db_table
            self.geometry_sql.append(
                self.sql_add_spatial_index % {
                    'index': qn(self._create_spatial_index_name(model, field)),
                    'table': qn(db_table),
                    'column': qn(field.column),
                }
            )
        return column_sql

    def create_model(self, model):
        super().create_model(model)
        self.create_spatial_indexes()

    def add_field(self, model, field):
        super().add_field(model, field)
        self.create_spatial_indexes()

    def remove_field(self, model, field):
        if isinstance(field, GeometryField) and field.spatial_index:
            qn = self.connection.ops.quote_name
            sql = self.sql_drop_spatial_index % {
                'index': qn(self._create_spatial_index_name(model, field)),
                'table': qn(model._meta.db_table),
            }
            try:
                self.execute(sql)
            except OperationalError:
                logger.error(
                    "Couldn't remove spatial index: %s (may be expected "
                    "if your storage engine doesn't support them).", sql
                )

        super().remove_field(model, field)

    def _create_spatial_index_name(self, model, field):
        return '%s_%s_id' % (model._meta.db_table, field.column)

    def create_spatial_indexes(self):
        for sql in self.geometry_sql:
            try:
                self.execute(sql)
            except OperationalError:
                logger.error(
                    "Cannot create SPATIAL INDEX %s. Only MyISAM and (as of "
                    "MySQL 5.7.5) InnoDB support them.", sql
                )
        self.geometry_sql = []
