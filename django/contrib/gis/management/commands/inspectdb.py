from django.core.management.commands.inspectdb import \
    Command as InspectDBCommand


class Command(InspectDBCommand):
    db_module = 'django.contrib.gis.db'
    gis_tables = {}

    def get_field_type(self, connection, table_name, row):
        field_type, field_params, field_notes = super(Command, self).get_field_type(connection, table_name, row)
        if field_type == 'GeometryField':
            geo_col = row[0]
            # Getting a more specific field type and any additional parameters
            # from the `get_geometry_type` routine for the spatial backend.
            field_type, geo_params = connection.introspection.get_geometry_type(table_name, geo_col)
            field_params.update(geo_params)
            # Adding the table name and column to the `gis_tables` dictionary, this
            # allows us to track which tables need a GeoManager.
            if table_name in self.gis_tables:
                self.gis_tables[table_name].append(geo_col)
            else:
                self.gis_tables[table_name] = [geo_col]
        return field_type, field_params, field_notes

    def get_meta(self, table_name, constraints, column_to_field_name):
        meta_lines = super(Command, self).get_meta(table_name, constraints, column_to_field_name)
        if table_name in self.gis_tables:
            # If the table is a geographic one, then we need make
            # GeoManager the default manager for the model.
            meta_lines.insert(0, '    objects = models.GeoManager()')
        return meta_lines
