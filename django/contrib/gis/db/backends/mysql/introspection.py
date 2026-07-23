from MySQLdb.constants import FIELD_TYPE

from django.contrib.gis.gdal import OGRGeomType
from django.db.backends.mysql.introspection import DatabaseIntrospection


class MySQLIntrospection(DatabaseIntrospection):
    # Updating the data_types_reverse dictionary with the appropriate
    # type for Geometry fields.
    data_types_reverse = DatabaseIntrospection.data_types_reverse.copy()
    data_types_reverse[FIELD_TYPE.GEOMETRY] = "GeometryField"

    def get_geometry_type(self, table_name, description):
        """
        Given a database table description, return the geometry type and
        any additional parameters (e.g., SRID) for the specified column.

        For MySQL 8.0+, uses the ST_GEOMETRY_COLUMNS view to get SRID info.
        For older MySQL versions, falls back to the original method.
        """
        field_params = {}

        # Check if we're on MySQL 8.0+ and can use the ST_GEOMETRY_COLUMNS view
        if self.connection.mysql_version >= (8, 0):
            with self.connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT srs_id, geometry_type_name
                    FROM information_schema.st_geometry_columns
                    WHERE table_schema = DATABASE()
                        AND table_name = %s
                        AND column_name = %s
                """,
                    [table_name, description.name],
                )

                row = cursor.fetchone()

            if row:
                srid, geom_type = row
                field_params = {"srid": srid} if srid else {}

                # Using OGRGeomType to convert from OGC name to Django field
                field_type = OGRGeomType(geom_type).django
                return field_type, field_params

        # Fallback to the original method for MySQL < 8.0 or if the column
        # wasn't found in ST_GEOMETRY_COLUMNS
        with self.connection.cursor() as cursor:
            # In order to get the specific geometry type of the field,
            # we introspect on the table definition using `DESCRIBE`.
            cursor.execute("DESCRIBE %s" % self.connection.ops.quote_name(table_name))
            # Increment over description info until we get to the geometry
            # column.
            for column, typ, null, key, default, extra in cursor.fetchall():
                if column == description.name:
                    # Using OGRGeomType to convert from OGC name to Django
                    # field. MySQL does not support 3D, so the field
                    # params are empty for older versions.
                    field_type = OGRGeomType(typ).django
                    field_params = {}
                    break

        return field_type, field_params

    def get_geometry_columns(self, table_name):
        """
        Return a list of geometry columns for the given table.
        For MySQL 8.0+, gets SRID information from ST_GEOMETRY_COLUMNS.
        For older versions, returns basic info from DESCRIBE.
        """
        geometry_columns = []

        if self.connection.mysql_version >= (8, 0):
            with self.connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT column_name, srs_id, geometry_type_name
                    FROM information_schema.st_geometry_columns
                    WHERE table_schema = DATABASE() AND table_name = %s
                """,
                    [table_name],
                )

                for column_name, srid, geom_type in cursor.fetchall():
                    geometry_columns.append(
                        {
                            "name": column_name,
                            "srid": srid,
                            "type": geom_type,
                        }
                    )
        else:
            # For older MySQL versions, fall back to DESCRIBE
            with self.connection.cursor() as cursor:
                cursor.execute(
                    "DESCRIBE %s" % self.connection.ops.quote_name(table_name)
                )
                for column, typ, null, key, default, extra in cursor.fetchall():
                    # Check if this is a geometry column by looking at the type
                    if any(
                        geom_type in typ.upper()
                        for geom_type in [
                            "GEOMETRY",
                            "POINT",
                            "LINESTRING",
                            "POLYGON",
                            "MULTIPOINT",
                            "MULTILINESTRING",
                            "MULTIPOLYGON",
                            "GEOMETRYCOLLECTION",
                        ]
                    ):
                        geometry_columns.append(
                            {
                                "name": column,
                                "srid": 0,  # MySQL < 8.0 doesn't store SRID per column
                                "type": typ,
                            }
                        )

        return geometry_columns

    def get_spatial_ref_sys_info(self, srid):
        """
        Get information about a spatial reference system by SRID.
        Only works on MySQL 8.0+ with ST_SPATIAL_REFERENCE_SYSTEMS view.
        Returns None for older MySQL versions.
        """
        if self.connection.mysql_version >= (8, 0):
            with self.connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT srs_name, organization, organization_coordsys_id, definition
                    FROM information_schema.st_spatial_reference_systems
                    WHERE srs_id = %s
                """,
                    [srid],
                )
                return cursor.fetchone()
        return None

    def get_spatial_ref_sys_list(self):
        """
        Return a list of all spatial reference systems.
        Only works on MySQL 8.0+ with ST_SPATIAL_REFERENCE_SYSTEMS view.
        Returns empty list for older MySQL versions.
        """
        if self.connection.mysql_version >= (8, 0):
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    SELECT
                        srs_id, srs_name,
                        organization, organization_coordsys_id,
                        definition
                    FROM information_schema.st_spatial_reference_systems
                    ORDER BY srs_id
                """)
                return cursor.fetchall()
        return []

    def supports_spatial_index(self, cursor, table_name):
        # Supported with MyISAM, Aria, or InnoDB.
        storage_engine = self.get_storage_engine(cursor, table_name)
        return storage_engine in ("MyISAM", "Aria", "InnoDB")

    def get_storage_engine(self, cursor, table_name):
        """
        Get the storage engine for the given table.
        """
        cursor.execute(
            "SELECT engine FROM information_schema.tables WHERE table_name = %s",
            [table_name],
        )
        result = cursor.fetchone()
        return result[0] if result else None
