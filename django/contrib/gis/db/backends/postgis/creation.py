from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db.backends.postgresql_psycopg2.creation import DatabaseCreation

class PostGISCreation(DatabaseCreation):
    geom_index_type = 'GIST'
    geom_index_opts = 'GIST_GEOMETRY_OPS'

    def sql_indexes_for_field(self, model, f, style):
        "Return any spatial index creation SQL for the field."
        from django.contrib.gis.db.models.fields import GeometryField

        output = super(PostGISCreation, self).sql_indexes_for_field(model, f, style)

        if isinstance(f, GeometryField):
            gqn = self.connection.ops.geo_quote_name
            qn = self.connection.ops.quote_name
            db_table = model._meta.db_table

            if f.geography:
                # Geogrophy columns are created normally.
                pass
            else:
                # Geometry columns are created by `AddGeometryColumn`
                # stored procedure.
                output.append(style.SQL_KEYWORD('SELECT ') +
                              style.SQL_TABLE('AddGeometryColumn') + '(' +
                              style.SQL_TABLE(gqn(db_table)) + ', ' +
                              style.SQL_FIELD(gqn(f.column)) + ', ' +
                              style.SQL_FIELD(str(f.srid)) + ', ' +
                              style.SQL_COLTYPE(gqn(f.geom_type)) + ', ' +
                              style.SQL_KEYWORD(str(f.dim)) + ');')

                if not f.null:
                    # Add a NOT NULL constraint to the field
                    output.append(style.SQL_KEYWORD('ALTER TABLE ') +
                                  style.SQL_TABLE(qn(db_table)) +
                                  style.SQL_KEYWORD(' ALTER ') +
                                  style.SQL_FIELD(qn(f.column)) +
                                  style.SQL_KEYWORD(' SET NOT NULL') + ';')

            if f.spatial_index:
                # Spatial indexes created the same way for both Geometry and
                # Geography columns.
                # PostGIS 2.0 does not support GIST_GEOMETRY_OPS. So, on 1.5
                # we use GIST_GEOMETRY_OPS, on 2.0 we use either "nd" ops
                # which are fast on multidimensional cases, or just plain
                # gist index for the 2d case.
                if f.geography:
                    index_opts = ''
                elif self.connection.ops.spatial_version >= (2, 0):
                    if f.dim > 2:
                        index_opts = ' ' + style.SQL_KEYWORD('gist_geometry_ops_nd')
                    else:
                        index_opts = ''
                else:
                    index_opts = ' ' + style.SQL_KEYWORD(self.geom_index_opts)
                output.append(style.SQL_KEYWORD('CREATE INDEX ') +
                              style.SQL_TABLE(qn('%s_%s_id' % (db_table, f.column))) +
                              style.SQL_KEYWORD(' ON ') +
                              style.SQL_TABLE(qn(db_table)) +
                              style.SQL_KEYWORD(' USING ') +
                              style.SQL_COLTYPE(self.geom_index_type) + ' ( ' +
                              style.SQL_FIELD(qn(f.column)) + index_opts + ' );')
        return output

    def sql_table_creation_suffix(self):
        cursor = self.connection.cursor()
        cursor.execute('SELECT datname FROM pg_database;')
        db_names = [row[0] for row in cursor.fetchall()]
        postgis_template = getattr(settings, 'POSTGIS_TEMPLATE', 'template_postgis')

        if postgis_template in db_names:
            qn = self.connection.ops.quote_name
            return ' TEMPLATE %s' % qn(postgis_template)
        elif self.connection.ops.spatial_version < (2, 0):
            raise ImproperlyConfigured("Template database '%s' does not exist." % postgis_template)
        else:
            return ''
