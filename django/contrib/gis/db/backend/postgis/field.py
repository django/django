from django.db.models.fields import Field # Django base Field class
from django.contrib.gis.geos import GEOSGeometry, GEOSException 
from django.contrib.gis.db.backend.postgis.query import POSTGIS_TERMS, geo_quotename as quotename
from types import StringType

class PostGISField(Field):
    def _add_geom(self, style, db_table):
        """
        Constructs the addition of the geometry to the table using the
        AddGeometryColumn(...) PostGIS (and OGC standard) stored procedure.

        Takes the style object (provides syntax highlighting) and the
         database table as parameters.
        """
        sql = style.SQL_KEYWORD('SELECT ') + \
              style.SQL_TABLE('AddGeometryColumn') + '(' + \
              style.SQL_TABLE(quotename(db_table)) + ', ' + \
              style.SQL_FIELD(quotename(self.column)) + ', ' + \
              style.SQL_FIELD(str(self._srid)) + ', ' + \
              style.SQL_COLTYPE(quotename(self._geom)) + ', ' + \
              style.SQL_KEYWORD(str(self._dim)) + ');'

        if not self.null:
            # Add a NOT NULL constraint to the field
            sql += '\n' + \
                   style.SQL_KEYWORD('ALTER TABLE ') + \
                   style.SQL_TABLE(quotename(db_table, dbl=True)) + \
                   style.SQL_KEYWORD(' ALTER ') + \
                   style.SQL_FIELD(quotename(self.column, dbl=True)) + \
                   style.SQL_KEYWORD(' SET NOT NULL') + ';'
        return sql
    
    def _geom_index(self, style, db_table,
                    index_type='GIST', index_opts='GIST_GEOMETRY_OPS'):
        "Creates a GiST index for this geometry field."
        sql = style.SQL_KEYWORD('CREATE INDEX ') + \
              style.SQL_TABLE(quotename('%s_%s_id' % (db_table, self.column), dbl=True)) + \
              style.SQL_KEYWORD(' ON ') + \
              style.SQL_TABLE(quotename(db_table, dbl=True)) + \
              style.SQL_KEYWORD(' USING ') + \
              style.SQL_COLTYPE(index_type) + ' ( ' + \
              style.SQL_FIELD(quotename(self.column, dbl=True)) + ' ' + \
              style.SQL_KEYWORD(index_opts) + ' );'
        return sql

    def _post_create_sql(self, style, db_table):
        """
        Returns SQL that will be executed after the model has been
        created. Geometry columns must be added after creation with the
        PostGIS AddGeometryColumn() function.
        """

        # Getting the AddGeometryColumn() SQL necessary to create a PostGIS
        # geometry field.
        post_sql = self._add_geom(style, db_table)

        # If the user wants to index this data, then get the indexing SQL as well.
        if self._index:
            return (post_sql, self._geom_index(style, db_table))
        else:
            return (post_sql,)

    def _post_delete_sql(self, style, db_table):
        "Drops the geometry column."
        sql = style.SQL_KEYWORD('SELECT ') + \
            style.SQL_KEYWORD('DropGeometryColumn') + '(' + \
            style.SQL_TABLE(quotename(db_table)) + ', ' + \
            style.SQL_FIELD(quotename(self.column)) +  ');'
        return sql

    def db_type(self):
        """
        PostGIS geometry columns are added by stored procedures, should be
        None.
        """
        return None

    def get_db_prep_lookup(self, lookup_type, value):
        """
        Returns field's value prepared for database lookup, accepts WKT and 
        GEOS Geometries for the value.
        """
        if lookup_type in POSTGIS_TERMS:
            if lookup_type == 'isnull': return [value] # special case for NULL geometries.
            if not bool(value): return [None] # If invalid value passed in.
            if isinstance(value, GEOSGeometry):
                # GEOSGeometry instance passed in.
                if value.srid != self._srid:
                    # Returning a dictionary instructs the parse_lookup() to add 
                    # what's in the 'where' key to the where parameters, since we 
                    # need to transform the geometry in the query.
                    return {'where' : ["ST_Transform(%s,%s)"],
                            'params' : [value, self._srid]
                            }
                else:
                    # Just return the GEOSGeometry, it has its own psycopg2 adaptor.
                    return [value]
            elif isinstance(value, StringType):
                # String instance passed in, assuming WKT.
                # TODO: Any validation needed here to prevent SQL injection?
                return ["SRID=%d;%s" % (self._srid, value)]
            else:
                raise TypeError("Invalid type (%s) used for field lookup value." % str(type(value)))
        else:
            raise TypeError("Field has invalid lookup: %s" % lookup_type)

    def get_db_prep_save(self, value):
        "Prepares the value for saving in the database."
        if not bool(value): return None
        if isinstance(value, GEOSGeometry):
            return value
        else:
            raise TypeError('Geometry Proxy should only return GEOSGeometry objects.')

    def get_internal_type(self):
        """
        Returns NoField because a stored procedure is used by PostGIS to create the
        """
        return 'NoField'

    def get_placeholder(self, value):
        """
        Provides a proper substitution value for Geometries that are not in the
         SRID of the field.  Specifically, this routine will substitute in the
         ST_Transform() function call.
        """
        if isinstance(value, GEOSGeometry) and value.srid != self._srid:
            # Adding Transform() to the SQL placeholder.
            return 'ST_Transform(%%s, %s)' % self._srid
        else:
            return '%s'
