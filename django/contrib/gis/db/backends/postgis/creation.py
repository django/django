from django.conf import settings
from django.db.backends.postgresql_psycopg2.creation import DatabaseCreation
from django.utils.functional import cached_property


class PostGISCreation(DatabaseCreation):
    geom_index_type = 'GIST'
    geom_index_ops = 'GIST_GEOMETRY_OPS'
    geom_index_ops_nd = 'GIST_GEOMETRY_OPS_ND'

    @cached_property
    def template_postgis(self):
        template_postgis = getattr(settings, 'POSTGIS_TEMPLATE', 'template_postgis')
        cursor = self.connection.cursor()
        cursor.execute('SELECT 1 FROM pg_database WHERE datname = %s LIMIT 1;', (template_postgis,))
        if cursor.fetchone():
            return template_postgis
        return None

    def sql_indexes_for_field(self, model, f, style):
        "Return any spatial index creation SQL for the field."
        from django.contrib.gis.db.models.fields import GeometryField

        output = super(PostGISCreation, self).sql_indexes_for_field(model, f, style)

        if isinstance(f, GeometryField):
            gqn = self.connection.ops.geo_quote_name
            qn = self.connection.ops.quote_name
            db_table = model._meta.db_table

            if f.geography or self.connection.ops.geometry:
                # Geography and Geometry (PostGIS 2.0+) columns are
                # created normally.
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
                    index_ops = ''
                elif self.connection.ops.geometry:
                    if f.dim > 2:
                        index_ops = ' ' + style.SQL_KEYWORD(self.geom_index_ops_nd)
                    else:
                        index_ops = ''
                else:
                    index_ops = ' ' + style.SQL_KEYWORD(self.geom_index_ops)
                output.append(style.SQL_KEYWORD('CREATE INDEX ') +
                              style.SQL_TABLE(qn('%s_%s_id' % (db_table, f.column))) +
                              style.SQL_KEYWORD(' ON ') +
                              style.SQL_TABLE(qn(db_table)) +
                              style.SQL_KEYWORD(' USING ') +
                              style.SQL_COLTYPE(self.geom_index_type) + ' ( ' +
                              style.SQL_FIELD(qn(f.column)) + index_ops + ' );')
        return output

    def sql_table_creation_suffix(self):
        if self.template_postgis is not None:
            return ' TEMPLATE %s' % (
                self.connection.ops.quote_name(self.template_postgis),)
        return ''

    def _create_test_db(self, verbosity, autoclobber):
        test_database_name = super(PostGISCreation, self)._create_test_db(verbosity, autoclobber)
        if self.template_postgis is None:
            # Connect to the test database in order to create the postgis extension
            self.connection.close()
            self.connection.settings_dict["NAME"] = test_database_name
            cursor = self.connection.cursor()
            cursor.execute("CREATE EXTENSION postgis")
            cursor.connection.commit()

        return test_database_name
