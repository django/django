from django.db.backends.postgresql_psycopg2.introspection import DatabaseIntrospection
from django.contrib.gis.gdal import OGRGeomType

class GeoIntrospectionError(Exception):
    pass

class PostGISIntrospection(DatabaseIntrospection):
    # Reverse dictionary for PostGIS geometry types not populated until
    # introspection is actually performed.
    postgis_types_reverse = {}

    ignored_tables = DatabaseIntrospection.ignored_tables + [
        'geography_columns',
        'geometry_columns',
        'raster_columns',
        'spatial_ref_sys',
        'raster_overviews',
    ]

    def get_postgis_types(self):
        """
        Returns a dictionary with keys that are the PostgreSQL object
        identification integers for the PostGIS geometry and/or
        geography types (if supported).
        """
        cursor = self.connection.cursor()
        # The OID integers associated with the geometry type may
        # be different across versions; hence, this is why we have
        # to query the PostgreSQL pg_type table corresponding to the
        # PostGIS custom data types.
        oid_sql = 'SELECT "oid" FROM "pg_type" WHERE "typname" = %s'
        try:
            cursor.execute(oid_sql, ('geometry',))
            GEOM_TYPE = cursor.fetchone()[0]
            postgis_types = { GEOM_TYPE : 'GeometryField' }
            if self.connection.ops.geography:
                cursor.execute(oid_sql, ('geography',))
                GEOG_TYPE = cursor.fetchone()[0]
                # The value for the geography type is actually a tuple
                # to pass in the `geography=True` keyword to the field
                # definition.
                postgis_types[GEOG_TYPE] = ('GeometryField', {'geography' : True})
        finally:
            cursor.close()

        return postgis_types

    def get_field_type(self, data_type, description):
        if not self.postgis_types_reverse:
            # If the PostGIS types reverse dictionary is not populated, do so
            # now.  In order to prevent unnecessary requests upon connection
            # intialization, the `data_types_reverse` dictionary is not updated
            # with the PostGIS custom types until introspection is actually
            # performed -- in other words, when this function is called.
            self.postgis_types_reverse = self.get_postgis_types()
            self.data_types_reverse.update(self.postgis_types_reverse)
        return super(PostGISIntrospection, self).get_field_type(data_type, description)

    def get_geometry_type(self, table_name, geo_col):
        """
        The geometry type OID used by PostGIS does not indicate the particular
        type of field that a geometry column is (e.g., whether it's a
        PointField or a PolygonField).  Thus, this routine queries the PostGIS
        metadata tables to determine the geometry type,
        """
        cursor = self.connection.cursor()
        try:
            try:
                # First seeing if this geometry column is in the `geometry_columns`
                cursor.execute('SELECT "coord_dimension", "srid", "type" '
                               'FROM "geometry_columns" '
                               'WHERE "f_table_name"=%s AND "f_geometry_column"=%s',
                               (table_name, geo_col))
                row = cursor.fetchone()
                if not row: raise GeoIntrospectionError
            except GeoIntrospectionError:
                if self.connection.ops.geography:
                    cursor.execute('SELECT "coord_dimension", "srid", "type" '
                                   'FROM "geography_columns" '
                                   'WHERE "f_table_name"=%s AND "f_geography_column"=%s',
                                   (table_name, geo_col))
                    row = cursor.fetchone()

            if not row:
                raise Exception('Could not find a geometry or geography column for "%s"."%s"' %
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
            if dim != 2:
                field_params['dim'] = dim
        finally:
            cursor.close()

        return field_type, field_params
