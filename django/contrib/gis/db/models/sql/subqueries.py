from django.contrib.gis.db.backend import SpatialBackend
from django.db.models.query import insert_query

if SpatialBackend.oracle:
    from django.db import connection
    from django.db.models.sql.subqueries import InsertQuery

    class OracleGeoInsertQuery(InsertQuery):
        def insert_values(self, insert_values, raw_values=False):
            """
            This routine is overloaded from InsertQuery so that no parameter is
            passed into cx_Oracle for NULL geometries.  The reason is that
            cx_Oracle has no way to bind Oracle object values (like
            MDSYS.SDO_GEOMETRY).
            """
            placeholders, values = [], []
            for field, val in insert_values:
                if hasattr(field, 'get_placeholder'):
                    ph = field.get_placeholder(val)
                else:
                    ph = '%s'

                placeholders.append(ph)
                self.columns.append(field.column)

                # If 'NULL' for the placeholder, omit appending None
                # to the values list (which is used for db params).
                if not ph == 'NULL':
                    values.append(val)
            if raw_values:
                self.values.extend(values)
            else:
                self.params += tuple(values)
                self.values.extend(placeholders)

    def insert_query(model, values, return_id=False, raw_values=False):
        query = OracleGeoInsertQuery(model, connection)
        query.insert_values(values, raw_values)
        return query.execute_sql(return_id)
