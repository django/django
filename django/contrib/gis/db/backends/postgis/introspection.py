from django.contrib.gis.gdal import OGRGeomType
from django.db.backends.postgresql.introspection import DatabaseIntrospection


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

    # Overridden from parent to include raster indices in retrieval.
    # Raster indices have pg_index.indkey value 0 because they are an
    # expression over the raster column through the ST_ConvexHull function.
    # So the default query has to be adapted to include raster indices.
    _get_indexes_query = """
        SELECT DISTINCT attr.attname, idx.indkey, idx.indisunique, idx.indisprimary
        FROM pg_catalog.pg_class c, pg_catalog.pg_class c2, pg_catalog.pg_index idx,
            pg_catalog.pg_attribute attr, pg_catalog.pg_type t
        WHERE
            c.oid = idx.indrelid
            AND idx.indexrelid = c2.oid
            AND attr.attrelid = c.oid
            AND t.oid = attr.atttypid
            AND (
                attr.attnum = idx.indkey[0] OR
                (t.typname LIKE 'raster' AND idx.indkey = '0')
            )
            AND attr.attnum > 0
            AND c.relname = %s"""

    def get_postgis_types(self):
        """
        Returns a dictionary with keys that are the PostgreSQL object
        identification integers for the PostGIS geometry and/or
        geography types (if supported).
        """
        field_types = [
            ('geometry', 'GeometryField'),
            # The value for the geography type is actually a tuple
            # to pass in the `geography=True` keyword to the field
            # definition.
            ('geography', ('GeometryField', {'geography': True})),
        ]
        postgis_types = {}

        # The OID integers associated with the geometry type may
        # be different across versions; hence, this is why we have
        # to query the PostgreSQL pg_type table corresponding to the
        # PostGIS custom data types.
        oid_sql = 'SELECT "oid" FROM "pg_type" WHERE "typname" = %s'
        cursor = self.connection.cursor()
        try:
            for field_type in field_types:
                cursor.execute(oid_sql, (field_type[0],))
                for result in cursor.fetchall():
                    postgis_types[result[0]] = field_type[1]
        finally:
            cursor.close()

        return postgis_types

    def get_field_type(self, data_type, description):
        if not self.postgis_types_reverse:
            # If the PostGIS types reverse dictionary is not populated, do so
            # now.  In order to prevent unnecessary requests upon connection
            # initialization, the `data_types_reverse` dictionary is not updated
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
                if not row:
                    raise GeoIntrospectionError
            except GeoIntrospectionError:
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
