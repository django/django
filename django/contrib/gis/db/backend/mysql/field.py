from django.db import connection
from django.db.models.fields import Field # Django base Field class
from django.contrib.gis.db.backend.mysql.query import GEOM_FROM_TEXT

# Quotename & geographic quotename, respectively.
qn = connection.ops.quote_name

class MySQLGeoField(Field):
    """
    The backend-specific geographic field for MySQL.
    """

    def _geom_index(self, style, db_table):
        """
        Creates a spatial index for the geometry column.  If MyISAM tables are
        used an R-Tree index is created, otherwise a B-Tree index is created.
        Thus, for best spatial performance, you should use MyISAM tables
        (which do not support transactions).  For more information, see Ch.
        16.6.1 of the MySQL 5.0 documentation.
        """

        # Getting the index name.
        idx_name = '%s_%s_id' % (db_table, self.column)

        sql = (style.SQL_KEYWORD('CREATE SPATIAL INDEX ') +
               style.SQL_TABLE(qn(idx_name)) +
               style.SQL_KEYWORD(' ON ') +
               style.SQL_TABLE(qn(db_table)) + '(' +
               style.SQL_FIELD(qn(self.column)) + ');')
        return sql

    def post_create_sql(self, style, db_table):
        """
        Returns SQL that will be executed after the model has been
        created.
        """
        # Getting the geometric index for this Geometry column.
        if self.spatial_index:
            return (self._geom_index(style, db_table),)
        else:
            return ()

    def db_type(self):
        "The OpenGIS name is returned for the MySQL database column type."
        return self.geom_type

    def get_placeholder(self, value):
        """
        The placeholder here has to include MySQL's WKT constructor.  Because
        MySQL does not support spatial transformations, there is no need to
        modify the placeholder based on the contents of the given value.
        """
        return '%s(%%s)' % GEOM_FROM_TEXT
