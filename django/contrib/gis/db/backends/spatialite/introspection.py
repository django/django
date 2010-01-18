from django.contrib.gis.gdal import OGRGeomType
from django.db.backends.sqlite3.introspection import DatabaseIntrospection, FlexibleFieldLookupDict

class GeoFlexibleFieldLookupDict(FlexibleFieldLookupDict):
    """
    Sublcass that includes updates the `base_data_types_reverse` dict
    for geometry field types.
    """
    base_data_types_reverse = FlexibleFieldLookupDict.base_data_types_reverse.copy()
    base_data_types_reverse.update(
        {'point' : 'GeometryField',
         'linestring' : 'GeometryField',
         'polygon' : 'GeometryField',
         'multipoint' : 'GeometryField',
         'multilinestring' : 'GeometryField',
         'multipolygon' : 'GeometryField',
         'geometrycollection' : 'GeometryField',
         })

class SpatiaLiteIntrospection(DatabaseIntrospection):
    data_types_reverse = GeoFlexibleFieldLookupDict()

    def get_geometry_type(self, table_name, geo_col):
        cursor = self.connection.cursor()
        try:
            # Querying the `geometry_columns` table to get additional metadata.
            cursor.execute('SELECT "coord_dimension", "srid", "type" '
                           'FROM "geometry_columns" '
                           'WHERE "f_table_name"=%s AND "f_geometry_column"=%s',
                           (table_name, geo_col))
            row = cursor.fetchone()
            if not row:
                raise Exception('Could not find a geometry column for "%s"."%s"' %
                                (table_name, geo_col))

            # OGRGeomType does not require GDAL and makes it easy to convert
            # from OGC geom type name to Django field.
            field_type = OGRGeomType(row[2]).django

            # Getting any GeometryField keyword arguments that are not the default.
            dim = row[0]
            srid = row[1]
            field_params = {}
            if srid != 4326:
                field_params['srid'] = srid
            if isinstance(dim, basestring) and 'Z' in dim:
                field_params['dim'] = 3
        finally:
            cursor.close()

        return field_type, field_params
