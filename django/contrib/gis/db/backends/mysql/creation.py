from django.db.backends.mysql.creation import DatabaseCreation


class MySQLCreation(DatabaseCreation):
    def sql_indexes_for_field(self, model, f, style):
        from django.contrib.gis.db.models.fields import GeometryField
        output = super(MySQLCreation, self).sql_indexes_for_field(model, f, style)

        if isinstance(f, GeometryField) and f.spatial_index:
            qn = self.connection.ops.quote_name
            db_table = model._meta.db_table
            idx_name = '%s_%s_id' % (db_table, f.column)
            output.append(style.SQL_KEYWORD('CREATE SPATIAL INDEX ') +
                          style.SQL_TABLE(qn(idx_name)) +
                          style.SQL_KEYWORD(' ON ') +
                          style.SQL_TABLE(qn(db_table)) + '(' +
                          style.SQL_FIELD(qn(f.column)) + ');')
        return output
