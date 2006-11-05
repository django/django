from django.db import backend, connection
from django.db.models.query import handle_legacy_orderlist
from django.utils.datastructures import SortedDict
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

            full_query = None
            select, sql, params, full_query = self._get_sql_clause()
            if not full_query:
                full_query = "SELECT %s%s\n%s" % \
                             ((self._distinct and "DISTINCT " or ""),
                              ', '.join(select), sql)
                
            cursor = connection.cursor()
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

        def _get_sql_clause(self):
            opts = self.model._meta
    
            # Construct the fundamental parts of the query: SELECT X FROM Y WHERE Z.
            select = ["%s.%s" % (backend.quote_name(opts.db_table), backend.quote_name(f.column)) for f in opts.fields]
            tables = [quote_only_if_word(t) for t in self._tables]
            joins = SortedDict()
            where = self._where[:]
            params = self._params[:]
    
            # Convert self._filters into SQL.
            joins2, where2, params2 = self._filters.get_sql(opts)
            joins.update(joins2)
            where.extend(where2)
            params.extend(params2)
    
            # Add additional tables and WHERE clauses based on select_related.
            if self._select_related:
                fill_table_cache(opts, select, tables, where, opts.db_table, [opts.db_table])
    
            # Add any additional SELECTs.
            if self._select:
                select.extend(['(%s) AS %s' % (quote_only_if_word(s[1]), backend.quote_name(s[0])) for s in self._select.items()])
    
            # Start composing the body of the SQL statement.
            sql = [" FROM", backend.quote_name(opts.db_table)]
    
            # Compose the join dictionary into SQL describing the joins.
            if joins:
                sql.append(" ".join(["%s %s %s ON %s" % (join_type, table, alias, condition)
                                for (alias, (table, join_type, condition)) in joins.items()]))
    
            # Compose the tables clause into SQL.
            if tables:
                sql.append(", " + ", ".join(tables))
    
            # Compose the where clause into SQL.
            if where:
                sql.append(where and "WHERE " + " AND ".join(where))
    
            # ORDER BY clause
            order_by = []
            if self._order_by is not None:
                ordering_to_use = self._order_by
            else:
                ordering_to_use = opts.ordering
            for f in handle_legacy_orderlist(ordering_to_use):
                if f == '?': # Special case.
                    order_by.append(backend.get_random_function_sql())
                else:
                    if f.startswith('-'):
                        col_name = f[1:]
                        order = "DESC"
                    else:
                        col_name = f
                        order = "ASC"
                    if "." in col_name:
                        table_prefix, col_name = col_name.split('.', 1)
                        table_prefix = backend.quote_name(table_prefix) + '.'
                    else:
                        # Use the database table as a column prefix if it wasn't given,
                        # and if the requested column isn't a custom SELECT.
                        if "." not in col_name and col_name not in (self._select or ()):
                            table_prefix = backend.quote_name(opts.db_table) + '.'
                        else:
                            table_prefix = ''
                    order_by.append('%s%s %s' % (table_prefix, backend.quote_name(orderfield2column(col_name, opts)), order))
            if order_by:
                sql.append("ORDER BY " + ", ".join(order_by))
    
            # LIMIT and OFFSET clauses
            # To support limits and offsets, Oracle requires some funky rewriting of an otherwise normal looking query. 
            select_clause = ",".join(select) 
            distinct = (self._distinct and "DISTINCT " or "") 

            if order_by:  
                order_by_clause = " OVER (ORDER BY %s )" % (", ".join(order_by)) 
            else:
                #Oracle's row_number() function always requires an order-by clause. 
                #So we need to define a default order-by, since none was provided. 
                order_by_clause = " OVER (ORDER BY %s.%s)" % \
                    (backend.quote_name(opts.db_table),  
                    backend.quote_name(opts.fields[0].db_column or opts.fields[0].column)) 
            # limit_and_offset_clause 
            offset = self._offset and int(self._offset) or 0 
            limit = self._limit and int(self._limit) or None 
            limit_and_offset_clause = '' 
            if limit: 
                limit_and_offset_clause = "WHERE rn > %s AND rn <= %s" % (offset, limit+offset) 
            elif offset:
                limit_and_offset_clause = "WHERE rn > %s" % (offset) 

            if len(limit_and_offset_clause) > 0: 
                full_query = """SELECT * FROM  
                    (SELECT %s    
                    %s, 
                    ROW_NUMBER() %s AS rn 
                    %s 
                    ) 
                    %s 
                    """ % (distinct, select_clause, order_by_clause, " ".join(sql), limit_and_offset_clause)
            else:
                full_query = None 
             
            return select, " ".join(sql), params, full_query
    
        
    return OracleQuerySet
