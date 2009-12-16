from django.conf import settings
from django.db.backends.postgresql.creation import DatabaseCreation

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
                # Geography columns
                if f.geography:
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
        qn = self.connection.ops.quote_name
        return ' TEMPLATE %s' % qn(getattr(settings, 'POSTGIS_TEMPLATE', 'template_postgis'))
