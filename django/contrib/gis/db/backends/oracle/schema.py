from django.contrib.gis.db.models import GeometryField
from django.db.backends.oracle.schema import DatabaseSchemaEditor
from django.db.backends.utils import strip_quotes, truncate_name


class OracleGISSchemaEditor(DatabaseSchemaEditor):
    sql_add_geometry_metadata = """
        INSERT INTO USER_SDO_GEOM_METADATA
            ("TABLE_NAME", "COLUMN_NAME", "DIMINFO", "SRID")
        VALUES (
            %(table)s,
            %(column)s,
            MDSYS.SDO_DIM_ARRAY(
                MDSYS.SDO_DIM_ELEMENT('LONG', %(dim0)s, %(dim2)s, %(tolerance)s),
                MDSYS.SDO_DIM_ELEMENT('LAT', %(dim1)s, %(dim3)s, %(tolerance)s)
            ),
            %(srid)s
        )"""
    sql_add_spatial_index = (
        "CREATE INDEX %(index)s ON %(table)s(%(column)s) "
        "INDEXTYPE IS MDSYS.SPATIAL_INDEX"
    )
    sql_clear_geometry_table_metadata = (
        "DELETE FROM USER_SDO_GEOM_METADATA WHERE TABLE_NAME = %(table)s"
    )
    sql_clear_geometry_field_metadata = (
        "DELETE FROM USER_SDO_GEOM_METADATA WHERE TABLE_NAME = %(table)s "
        "AND COLUMN_NAME = %(column)s"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.geometry_sql = []

    def geo_quote_name(self, name):
        return self.connection.ops.geo_quote_name(name)

    def quote_value(self, value):
        if isinstance(value, self.connection.ops.Adapter):
            return super().quote_value(str(value))
        return super().quote_value(value)

    def _field_indexes_sql(self, model, field):
        if isinstance(field, GeometryField) and field.spatial_index:
            return [self._create_spatial_index_sql(model, field)]
        return super()._field_indexes_sql(model, field)

    def column_sql(self, model, field, include_default=False):
        column_sql = super().column_sql(model, field, include_default)
        if isinstance(field, GeometryField):
            self.geometry_sql.append(
                self.sql_add_geometry_metadata
                % {
                    "table": self.geo_quote_name(model._meta.db_table),
                    "column": self.geo_quote_name(field.column),
                    "dim0": field._extent[0],
                    "dim1": field._extent[1],
                    "dim2": field._extent[2],
                    "dim3": field._extent[3],
                    "tolerance": field._tolerance,
                    "srid": field.srid,
                }
            )
        return column_sql

    def create_model(self, model):
        super().create_model(model)
        self.run_geometry_sql()

    def delete_model(self, model):
        super().delete_model(model)
        self.execute(
            self.sql_clear_geometry_table_metadata
            % {
                "table": self.geo_quote_name(model._meta.db_table),
            }
        )

    def add_field(self, model, field):
        super().add_field(model, field)
        self.run_geometry_sql()

    def remove_field(self, model, field):
        if isinstance(field, GeometryField):
            self.execute(
                self.sql_clear_geometry_field_metadata
                % {
                    "table": self.geo_quote_name(model._meta.db_table),
                    "column": self.geo_quote_name(field.column),
                }
            )
            if field.spatial_index:
                self.execute(self._delete_spatial_index_sql(model, field))
        super().remove_field(model, field)

    def run_geometry_sql(self):
        for sql in self.geometry_sql:
            self.execute(sql)
        self.geometry_sql = []

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
        # Oracle doesn't allow object names > 30 characters. Use this scheme
        # instead of self._create_index_name() for backwards compatibility.
        return truncate_name(
            "%s_%s_id" % (strip_quotes(model._meta.db_table), field.column), 30
        )

    def _create_spatial_index_sql(self, model, field):
        index_name = self._create_spatial_index_name(model, field)
        return self.sql_add_spatial_index % {
            "index": self.quote_name(index_name),
            "table": self.quote_name(model._meta.db_table),
            "column": self.quote_name(field.column),
        }

    def _delete_spatial_index_sql(self, model, field):
        index_name = self._create_spatial_index_name(model, field)
        return self._delete_index_sql(model, index_name)
