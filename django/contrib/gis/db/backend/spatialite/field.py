from django.db.models.fields import Field # Django base Field class

# Quotename & geographic quotename, respectively
from django.db import connection
qn = connection.ops.quote_name
from django.contrib.gis.db.backend.util import gqn
from django.contrib.gis.db.backend.spatialite.query import GEOM_FROM_TEXT, TRANSFORM

class SpatiaLiteField(Field):
    """
    The backend-specific geographic field for SpatiaLite.
    """

    def _add_geom(self, style, db_table):
        """
        Constructs the addition of the geometry to the table using the
        AddGeometryColumn(...) OpenGIS stored procedure.

        Takes the style object (provides syntax highlighting) and the
        database table as parameters.
        """
        sql = (style.SQL_KEYWORD('SELECT ') +
               style.SQL_TABLE('AddGeometryColumn') + '(' +
               style.SQL_TABLE(gqn(db_table)) + ', ' +
               style.SQL_FIELD(gqn(self.column)) + ', ' +
               style.SQL_FIELD(str(self.srid)) + ', ' +
               style.SQL_COLTYPE(gqn(self.geom_type)) + ', ' +
               style.SQL_KEYWORD(str(self.dim)) + ');')

        return sql

    def _geom_index(self, style, db_table):
        "Creates a spatial index for this geometry field."
        sql = (style.SQL_KEYWORD('SELECT ') +
              style.SQL_TABLE('CreateSpatialIndex') + '(' +
              style.SQL_TABLE(gqn(db_table)) + ', ' +
              style.SQL_FIELD(gqn(self.column)) + ');')
        return sql

    def post_create_sql(self, style, db_table):
        """
        Returns SQL that will be executed after the model has been
        created. Geometry columns must be added after creation with the
        OpenGIS AddGeometryColumn() function.
        """
        # Getting the AddGeometryColumn() SQL necessary to create a OpenGIS
        # geometry field.
        post_sql = self._add_geom(style, db_table)

        # If the user wants to index this data, then get the indexing SQL as well.
        if self.spatial_index:
            return (post_sql, self._geom_index(style, db_table))
        else:
            return (post_sql,)

    def _post_delete_sql(self, style, db_table):
        "Drops the geometry column."
        sql = (style.SQL_KEYWORD('SELECT ') +
               style.SQL_KEYWORD('DropGeometryColumn') + '(' +
               style.SQL_TABLE(gqn(db_table)) + ', ' +
               style.SQL_FIELD(gqn(self.column)) +  ');')
        return sql

    def db_type(self):
        """
        SpatiaLite geometry columns are added by stored procedures;
        should be None.
        """
        return None

    def get_placeholder(self, value):
        """
        Provides a proper substitution value for Geometries that are not in the
        SRID of the field.  Specifically, this routine will substitute in the
        Transform() and GeomFromText() function call(s).
        """
        if value is None or value.srid == self.srid:
            return '%s(%%s,%s)' % (GEOM_FROM_TEXT, self.srid)
        else:
            # Adding Transform() to the SQL placeholder.
            return '%s(%s(%%s,%s), %s)' % (TRANSFORM, GEOM_FROM_TEXT, value.srid, self.srid)
