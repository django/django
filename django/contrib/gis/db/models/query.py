import operator
from django.core.exceptions import ImproperlyConfigured
from django.db import backend
from django.db.models.query import Q, QuerySet, handle_legacy_orderlist, quote_only_if_word
from django.db.models.fields import FieldDoesNotExist
from django.utils.datastructures import SortedDict
from django.contrib.gis.db.models.fields import GeometryField
from django.contrib.gis.db.backend import parse_lookup # parse_lookup depends on the spatial database backend.

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
            select.extend(['(%s) AS %s' % (quote_only_if_word(s[1]), backend.quote_name(s[0])) for s in self._select.items()])

        # Start composing the body of the SQL statement.
        sql = [" FROM", backend.quote_name(opts.db_table)]

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
        if self._limit is not None:
            sql.append("%s " % backend.get_limit_offset_sql(self._limit, self._offset))
        else:
            assert self._offset is None, "'offset' is not allowed without 'limit'"

        return select, " ".join(sql), params

    def _clone(self, klass=None, **kwargs):
        c = super(GeoQuerySet, self)._clone(klass, **kwargs)
        c._custom_select = self._custom_select
        return c

    #### Methods specific to the GeoQuerySet ####
    def _field_column(self, field):
        return "%s.%s" % (backend.quote_name(self.model._meta.db_table),
                          backend.quote_name(field.column))
    
    def kml(self, field_name, precision=8):
        """Returns KML representation of the given field name in a `kml` 
        attribute on each element of the QuerySet."""
        # Is KML output supported?
        try:
            from django.contrib.gis.db.backend.postgis import ASKML
        except ImportError:
            raise ImproperlyConfigured, 'AsKML() only available in PostGIS versions 1.2.1 and greater.'

        # Is the given field name a geographic field?
        field = self.model._meta.get_field(field_name)
        if not isinstance(field, GeometryField):
            raise TypeError, 'KML output only available on GeometryField fields.'
        field_col = self._field_column(field)
        
        # Adding the AsKML function call to the SELECT part of the SQL.
        return self.extra(select={'kml':'%s(%s,%s)' % (ASKML, field_col, precision)})

    def transform(self, field_name, srid=4326):
        """Transforms the given geometry field to the given SRID.  If no SRID is
        provided, the transformation will default to using 4326 (WGS84)."""
        field = self.model._meta.get_field(field_name)
        if not isinstance(field, GeometryField):
            raise TypeError, 'ST_Transform() only available for GeometryField fields.'

        # Setting the key for the field's column with the custom SELECT SQL to 
        #  override the geometry column returned from the database.
        self._custom_select[field.column] = \
            '(ST_Transform(%s, %s)) AS %s' % (self._field_column(field), srid, 
                                              backend.quote_name(field.column))
        return self._clone()

    
