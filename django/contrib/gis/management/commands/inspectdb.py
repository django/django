from django.core.management.commands.inspectdb import \
    Command as InspectDBCommand


class Command(InspectDBCommand):
    db_module = 'django.contrib.gis.db'

    def get_field_type(self, connection, table_name, row):
        field_type, field_params, field_notes = super().get_field_type(connection, table_name, row)
        if field_type == 'GeometryField':
            geo_col = row[0]
            # Getting a more specific field type and any additional parameters
            # from the `get_geometry_type` routine for the spatial backend.
            field_type, geo_params = connection.introspection.get_geometry_type(table_name, geo_col)
            field_params.update(geo_params)
        return field_type, field_params, field_notes
