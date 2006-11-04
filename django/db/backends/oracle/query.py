# NOTE: still dependent on other code that Matt Boersma is working on, not yet tested!!! - Jim Baker

from django.db import backend, connection
import cx_Oracle as Database


def get_query_set_class(DefaultQuerySet):
    """
    Create a custom QuerySet class for Oracle.
    """
    
    class OracleQuerySet(DefaultQuerySet):
        def iterator(self):
            "Performs the SELECT database lookup of this QuerySet."

            # self._select is a dictionary, and dictionaries' key order is
            # undefined, so we convert it to a list of tuples.
            extra_select = self._select.items()

            cursor = connection.cursor()

            full_query = None
            select, sql, params, full_query = self._get_sql_clause() 

            if not full_query: 
                cursor.execute("SELECT " + (self._distinct and "DISTINCT " or "") + ",".join(select) + sql, params) 
            else: 
                cursor.execute(full_query, params) 

            fill_cache = self._select_related
            index_end = len(self.model._meta.fields)

            # so here's the logic;
            # 1. retrieve each row in turn
            # 2. convert CLOBs

            def resolve_lobs(row):
                for field in row:
                    if isinstance(field, Database.LOB):
                        yield str(field)
                    else:
                        yield field

            for unresolved_row in cursor:
                row = list(resolve_lobs(unresolved_row))
                if fill_cache:
                    obj, index_end = get_cached_row(self.model, row, 0)
                else:
                    obj = self.model(*row[:index_end])
                for i, k in enumerate(extra_select):
                    setattr(obj, k[0], row[index_end+i])
            yield obj

        
    return OracleQuerySet
