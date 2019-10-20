from django.core.management.commands.inspectdb import (
    Command as InspectDBCommand,
)


class Command(InspectDBCommand):
    db_module = 'django.contrib.gis.db'

    def get_field_type(self, connection, table_name, row):
        field_type, field_params, field_notes = super().get_field_type(connection, table_name, row)
        if field_type == 'GeometryField':
            # Getting a more specific field type and any additional parameters
            # from the `get_geometry_type` routine for the spatial backend.
            field_type, geo_params = connection.introspection.get_geometry_type(table_name, row)
            field_params.update(geo_params)
        return field_type, field_params, field_notes

    def _get_field_constrains_params(self, connection, constraints, table_name, column_name,
                                     is_relation, is_primary_key, row):
        extra_params, field_notes = super()._get_field_constrains_params(
            connection, constraints, table_name, column_name,
            is_relation, is_primary_key, row)
        field_type, _, _ = super().get_field_type(connection, table_name, row)
        if field_type == 'GeometryField' and extra_params.get('db_index'):
            del extra_params['db_index']
        return extra_params, field_notes
