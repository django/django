from django.db import connections
from django.db.models.sql.subqueries import InsertQuery

class GeoInsertQuery(InsertQuery):
    def insert_values(self, insert_values, raw_values=False):
        """
        Set up the insert query from the 'insert_values' dictionary. The
        dictionary gives the model field names and their target values.

        If 'raw_values' is True, the values in the 'insert_values' dictionary
        are inserted directly into the query, rather than passed as SQL
        parameters. This provides a way to insert NULL and DEFAULT keywords
        into the query, for example.
        """
        placeholders, values = [], []
        for field, val in insert_values:
            placeholders.append((field, val))
            self.columns.append(field.column)

            if not placeholders[-1] == 'NULL':
                values.append(val)
        if raw_values:
            self.values.extend([(None, v) for v in values])
        else:
            self.params += tuple(values)
            self.values.extend(placeholders)

def insert_query(model, values, return_id=False, raw_values=False, using=None):
    """
    Inserts a new record for the given model. This provides an interface to
    the InsertQuery class and is how Model.save() is implemented. It is not
    part of the public API.
    """
    query = GeoInsertQuery(model)
    query.insert_values(values, raw_values)
    return query.get_compiler(using=using).execute_sql(return_id)
