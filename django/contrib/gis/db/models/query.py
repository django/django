import operator
from django.core.exceptions import ImproperlyConfigured
from django.db import connection
from django.db.models.query import EmptyResultSet, Q, QuerySet, handle_legacy_orderlist, quote_only_if_word, orderfield2column, fill_table_cache
from django.db.models.fields import FieldDoesNotExist
from django.utils.datastructures import SortedDict
from django.contrib.gis.db.models.fields import GeometryField
# parse_lookup depends on the spatial database backend.
from django.contrib.gis.db.backend import parse_lookup, ASGML, ASKML, UNION
from django.contrib.gis.geos import GEOSGeometry

class GeoQ(Q):
    "Geographical query encapsulation object."

    def get_sql(self, opts):
        "Overloaded to use our own parse_lookup() function."
        return parse_lookup(self.kwargs.items(), opts)

class GeoQuerySet(QuerySet):
    "Geographical-enabled QuerySet object."
    
    #### Overloaded QuerySet Routines ####
    def __init__(self, model=None):
        super(GeoQuerySet, self).__init__(model=model)

        # We only want to use the GeoQ object for our queries
        self._filters = GeoQ()

        # For replacement fields in the SELECT.
        self._custom_select = {}

    def _filter_or_exclude(self, mapper, *args, **kwargs):
        # mapper is a callable used to transform Q objects,
        # or None for identity transform
        if mapper is None:
            mapper = lambda x: x
        if len(args) > 0 or len(kwargs) > 0:
            assert self._limit is None and self._offset is None, \
                "Cannot filter a query once a slice has been taken."

        clone = self._clone()
        if len(kwargs) > 0:
            # Using the GeoQ object for our filters instead
            clone._filters = clone._filters & mapper(GeoQ(**kwargs))
        if len(args) > 0:
            clone._filters = clone._filters & reduce(operator.and_, map(mapper, args))
        return clone

    def _get_sql_clause(self):
        qn = connection.ops.quote_name
        opts = self.model._meta

        # Construct the fundamental parts of the query: SELECT X FROM Y WHERE Z.
        select = []

        # This is the only component of this routine that is customized for the 
        #  GeoQuerySet. Specifically, this allows operations to be done on fields 
        #  in the SELECT, overriding their values -- this is different from using 
        #  QuerySet.extra(select=foo) because extra() adds an  an _additional_ 
        #  field to be selected.  Used in returning transformed geometries.
        for f in opts.fields:
            if f.column in self._custom_select: select.append(self._custom_select[f.column])
            else: select.append(self._field_column(f))

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
            fill_table_cache(opts, select, tables, where,
                             old_prefix=opts.db_table,
                             cache_tables_seen=[opts.db_table],
                             max_depth=self._max_related_depth)

        # Add any additional SELECTs.
        if self._select:
            select.extend(['(%s) AS %s' % (quote_only_if_word(s[1]), qn(s[0])) for s in self._select.items()])

        # Start composing the body of the SQL statement.
        sql = [" FROM", qn(opts.db_table)]

        # Compose the join dictionary into SQL describing the joins.
        if joins:
            sql.append(" ".join(["%s %s AS %s ON %s" % (join_type, table, alias, condition)
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
                order_by.append(connection.ops.random_function_sql())
            else:
                if f.startswith('-'):
                    col_name = f[1:]
                    order = "DESC"
                else:
                    col_name = f
                    order = "ASC"
                if "." in col_name:
                    table_prefix, col_name = col_name.split('.', 1)
                    table_prefix = qn(table_prefix) + '.'
                else:
                    # Use the database table as a column prefix if it wasn't given,
                    # and if the requested column isn't a custom SELECT.
                    if "." not in col_name and col_name not in (self._select or ()):
                        table_prefix = qn(opts.db_table) + '.'
                    else:
                        table_prefix = ''
                order_by.append('%s%s %s' % (table_prefix, qn(orderfield2column(col_name, opts)), order))
        if order_by:
            sql.append("ORDER BY " + ", ".join(order_by))

        # LIMIT and OFFSET clauses
        if self._limit is not None:
            sql.append("%s " % connection.ops.limit_offset_sql(self._limit, self._offset))
        else:
            assert self._offset is None, "'offset' is not allowed without 'limit'"

        return select, " ".join(sql), params

    def _clone(self, klass=None, **kwargs):
        c = super(GeoQuerySet, self)._clone(klass, **kwargs)
        c._custom_select = self._custom_select
        return c

    #### Methods specific to the GeoQuerySet ####
    def _field_column(self, field):
        "Helper function that returns the database column for the given field."
        qn = connection.ops.quote_name
        return "%s.%s" % (qn(self.model._meta.db_table),
                          qn(field.column))

    def _geo_column(self, field_name):
        """
        Helper function that returns False when the given field name is not an
        instance of a GeographicField, otherwise, the database column for the
        geographic field is returned.
        """
        field = self.model._meta.get_field(field_name)
        if isinstance(field, GeometryField):
            return self._field_column(field)
        else:
            return False

    def gml(self, field_name, precision=8, version=2):
        """
        Returns GML representation of the given field in a `gml` attribute
        on each element of the GeoQuerySet.
        """
        # Is GML output supported?
        if not ASGML:
            raise ImproperlyConfigured('AsGML() stored procedure not available.')

        # Is the given field name a geographic field?
        field_col = self._geo_column(field_name)
        if not field_col:
            raise TypeError('GML output only available on GeometryFields')

        # Adding AsGML function call to SELECT part of the SQL.
        return self.extra(select={'gml':'%s(%s,%s,%s)' % (ASGML, field_col, precision, version)})

    def kml(self, field_name, precision=8):
        """
        Returns KML representation of the given field name in a `kml` 
        attribute on each element of the GeoQuerySet.
        """
        # Is KML output supported?
        if not ASKML:
            raise ImproperlyConfigured('AsKML() stored procedure not available.')

        # Is the given field name a geographic field?
        field_col = self._geo_column(field_name)
        if not field_col:
            raise TypeError('KML output only available on GeometryFields.')
        
        # Adding the AsKML function call to SELECT part of the SQL.
        return self.extra(select={'kml':'%s(%s,%s)' % (ASKML, field_col, precision)})

    def transform(self, field_name, srid=4326):
        """
        Transforms the given geometry field to the given SRID.  If no SRID is
        provided, the transformation will default to using 4326 (WGS84).
        """
        # Is the given field name a geographic field?
        field = self.model._meta.get_field(field_name)
        if not isinstance(field, GeometryField):
            raise TypeError('ST_Transform() only available for GeometryFields')

        # Setting the key for the field's column with the custom SELECT SQL to 
        #  override the geometry column returned from the database.
        self._custom_select[field.column] = \
            '(ST_Transform(%s, %s)) AS %s' % (self._field_column(field), srid, 
                                              connection.ops.quote_name(field.column))
        return self._clone()

    def union(self, field_name):
        """
        Performs an aggregate union on the given geometry field.  Returns
        None if the GeoQuerySet is empty.
        """
        # Making sure backend supports the Union stored procedure
        if not UNION:
            raise ImproperlyConfigured('Union stored procedure not available.')

        # Getting the geographic field column
        field_col = self._geo_column(field_name)
        if not field_col:
            raise TypeError('Aggregate Union only available on GeometryFields.')

        # Getting the SQL for the query.
        try:
            select, sql, params = self._get_sql_clause()
        except EmptyResultSet:
            return None

        # Replacing the select with a call to the ST_Union stored procedure
        #  on the geographic field column.
        union_sql = ('SELECT %s(%s)' % (UNION, field_col)) + sql
        cursor = connection.cursor()
        cursor.execute(union_sql, params)

        # Pulling the HEXEWKB from the returned cursor.
        hex = cursor.fetchone()[0]
        if hex: return GEOSGeometry(hex)
        else: return None
