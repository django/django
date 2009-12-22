from django.db.backends.oracle.creation import DatabaseCreation
from django.db.backends.util import truncate_name

class OracleCreation(DatabaseCreation):

    def sql_indexes_for_field(self, model, f, style):
        "Return any spatial index creation SQL for the field."
        from django.contrib.gis.db.models.fields import GeometryField

        output = super(OracleCreation, self).sql_indexes_for_field(model, f, style)

        if isinstance(f, GeometryField):
            gqn = self.connection.ops.geo_quote_name
            qn = self.connection.ops.quote_name
            db_table = model._meta.db_table

            output.append(style.SQL_KEYWORD('INSERT INTO ') +
                          style.SQL_TABLE('USER_SDO_GEOM_METADATA') +
                          ' (%s, %s, %s, %s)\n  ' % tuple(map(qn, ['TABLE_NAME', 'COLUMN_NAME', 'DIMINFO', 'SRID'])) +
                          style.SQL_KEYWORD(' VALUES ') + '(\n    ' +
                          style.SQL_TABLE(gqn(db_table)) + ',\n    ' +
                          style.SQL_FIELD(gqn(f.column)) + ',\n    ' +
                          style.SQL_KEYWORD("MDSYS.SDO_DIM_ARRAY") + '(\n      ' +
                          style.SQL_KEYWORD("MDSYS.SDO_DIM_ELEMENT") +
                          ("('LONG', %s, %s, %s),\n      " % (f._extent[0], f._extent[2], f._tolerance)) +
                          style.SQL_KEYWORD("MDSYS.SDO_DIM_ELEMENT") +
                          ("('LAT', %s, %s, %s)\n    ),\n" % (f._extent[1], f._extent[3], f._tolerance)) +
                          '    %s\n  );' % f.srid)

            if f.spatial_index:
                # Getting the index name, Oracle doesn't allow object
                # names > 30 characters.
                idx_name = truncate_name('%s_%s_id' % (db_table, f.column), 30)

                output.append(style.SQL_KEYWORD('CREATE INDEX ') +
                              style.SQL_TABLE(qn(idx_name)) +
                              style.SQL_KEYWORD(' ON ') +
                              style.SQL_TABLE(qn(db_table)) + '(' +
                              style.SQL_FIELD(qn(f.column)) + ') ' +
                              style.SQL_KEYWORD('INDEXTYPE IS ') +
                              style.SQL_TABLE('MDSYS.SPATIAL_INDEX') + ';')
        return output
