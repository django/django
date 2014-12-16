from django.db.backends.sqlite3.creation import DatabaseCreation


class SpatiaLiteCreation(DatabaseCreation):

    def sql_indexes_for_field(self, model, f, style):
        "Return any spatial index creation SQL for the field."
        from django.contrib.gis.db.models.fields import GeometryField

        output = super(SpatiaLiteCreation, self).sql_indexes_for_field(model, f, style)

        if isinstance(f, GeometryField):
            gqn = self.connection.ops.geo_quote_name
            db_table = model._meta.db_table

            output.append(style.SQL_KEYWORD('SELECT ') +
                          style.SQL_TABLE('AddGeometryColumn') + '(' +
                          style.SQL_TABLE(gqn(db_table)) + ', ' +
                          style.SQL_FIELD(gqn(f.column)) + ', ' +
                          style.SQL_FIELD(str(f.srid)) + ', ' +
                          style.SQL_COLTYPE(gqn(f.geom_type)) + ', ' +
                          style.SQL_KEYWORD(str(f.dim)) + ', ' +
                          style.SQL_KEYWORD(str(int(not f.null))) +
                          ');')

            if f.spatial_index:
                output.append(style.SQL_KEYWORD('SELECT ') +
                              style.SQL_TABLE('CreateSpatialIndex') + '(' +
                              style.SQL_TABLE(gqn(db_table)) + ', ' +
                              style.SQL_FIELD(gqn(f.column)) + ');')

        return output
