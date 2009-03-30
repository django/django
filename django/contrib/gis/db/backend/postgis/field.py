from django.db import connection
from django.db.models.fields import Field # Django base Field class
from django.contrib.gis.db.backend.util import gqn
from django.contrib.gis.db.backend.postgis.query import TRANSFORM

# Quotename & geographic quotename, respectively
qn = connection.ops.quote_name

class PostGISField(Field):
    """
    The backend-specific geographic field for PostGIS.
    """

    def _add_geom(self, style, db_table):
        """
        Constructs the addition of the geometry to the table using the
        AddGeometryColumn(...) PostGIS (and OGC standard) stored procedure.

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

        if not self.null:
            # Add a NOT NULL constraint to the field
            sql += ('\n' +
                    style.SQL_KEYWORD('ALTER TABLE ') +
                    style.SQL_TABLE(qn(db_table)) +
                    style.SQL_KEYWORD(' ALTER ') +
                    style.SQL_FIELD(qn(self.column)) +
                    style.SQL_KEYWORD(' SET NOT NULL') + ';')
        return sql

    def _geom_index(self, style, db_table,
                    index_type='GIST', index_opts='GIST_GEOMETRY_OPS'):
        "Creates a GiST index for this geometry field."
        sql = (style.SQL_KEYWORD('CREATE INDEX ') +
              style.SQL_TABLE(qn('%s_%s_id' % (db_table, self.column))) +
              style.SQL_KEYWORD(' ON ') +
              style.SQL_TABLE(qn(db_table)) +
              style.SQL_KEYWORD(' USING ') +
              style.SQL_COLTYPE(index_type) + ' ( ' +
              style.SQL_FIELD(qn(self.column)) + ' ' +
              style.SQL_KEYWORD(index_opts) + ' );')
        return sql

    def post_create_sql(self, style, db_table):
        """
        Returns SQL that will be executed after the model has been
        created. Geometry columns must be added after creation with the
        PostGIS AddGeometryColumn() function.
        """

        # Getting the AddGeometryColumn() SQL necessary to create a PostGIS
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
        PostGIS geometry columns are added by stored procedures, should be
        None.
        """
        return None

    def get_placeholder(self, value):
        """
        Provides a proper substitution value for Geometries that are not in the
        SRID of the field.  Specifically, this routine will substitute in the
        ST_Transform() function call.
        """
        if value is None or value.srid == self.srid:
            return '%s'
        else:
            # Adding Transform() to the SQL placeholder.
            return '%s(%%s, %s)' % (TRANSFORM, self.srid)
