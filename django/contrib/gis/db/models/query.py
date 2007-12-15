import operator
from django.core.exceptions import ImproperlyConfigured
from django.db import connection
from django.db.models.query import EmptyResultSet, Q, QuerySet, handle_legacy_orderlist, quote_only_if_word, orderfield2column, fill_table_cache
from django.db.models.fields import FieldDoesNotExist
from django.utils.datastructures import SortedDict
from django.contrib.gis.db.models.fields import GeometryField
# parse_lookup depends on the spatial database backend.
from django.contrib.gis.db.backend import parse_lookup, \
    ASGML, ASKML, DISTANCE, GEOM_SELECT, SPATIAL_BACKEND, TRANSFORM, UNION, VERSION
from django.contrib.gis.geos import GEOSGeometry

# Shortcut booleans for determining the backend.
oracle = SPATIAL_BACKEND == 'oracle'
postgis = SPATIAL_BACKEND == 'postgis'

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
        self._ewkt = None

        # If GEOM_SELECT is defined in the backend, then it will be used
        # for the selection format of the geometry column.
        if GEOM_SELECT:
            #if oracle and hasattr(self, '_ewkt'):
            # Transformed geometries in Oracle use EWKT so that the SRID
            # on the transformed lazy geometries is set correctly).
            #print '-=' * 20
            #print self._ewkt, GEOM_SELECT
            #self._geo_fmt = "'SRID=%d;'||%s" % (self._ewkt, GEOM_SELECT)
            #self._geo_fmt = GEOM_SELECT
            #else:
            #print '-=' * 20
            self._geo_fmt = GEOM_SELECT
        else:
            self._geo_fmt = '%s'

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

    def _get_sql_clause(self, get_full_query=False):
        qn = connection.ops.quote_name
        opts = self.model._meta

        # Construct the fundamental parts of the query: SELECT X FROM Y WHERE Z.
        select = []

        # This is the only component of this routine that is customized for the 
        # GeoQuerySet. Specifically, this allows operations to be done on fields 
        # in the SELECT, overriding their values -- this is different from using 
        # QuerySet.extra(select=foo) because extra() adds an  an _additional_ 
        # field to be selected.  Used in returning transformed geometries, and
        # handling the selection of native database geometry formats.
        for f in opts.fields:
            # Getting the selection format string.
            if hasattr(f, '_geom'):
                sel_fmt = self._geo_fmt

                # If an SRID needs to specified other than what is in the field
                # (like when `transform` is called), make sure to explicitly set
                # the SRID by returning EWKT.
                if self._ewkt and oracle:
                    sel_fmt = "'SRID=%d;'||%s" % (self._ewkt, sel_fmt)
            else:
                sel_fmt = '%s'
                
            # Getting the field selection substitution string
            if f.column in self._custom_select:
                fld_sel = self._custom_select[f.column]
            else:
                fld_sel = self._field_column(f)

            # Appending the selection 
            select.append(sel_fmt % fld_sel)

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
        if not oracle:
            if self._limit is not None:
                sql.append("%s " % connection.ops.limit_offset_sql(self._limit, self._offset))
            else:
                assert self._offset is None, "'offset' is not allowed without 'limit'"

            return select, " ".join(sql), params
        else:
            # To support limits and offsets, Oracle requires some funky rewriting of an otherwise normal looking query.
            select_clause = ",".join(select)
            distinct = (self._distinct and "DISTINCT " or "")

            if order_by:
                order_by_clause = " OVER (ORDER BY %s )" % (", ".join(order_by))
            else:
                #Oracle's row_number() function always requires an order-by clause.
                #So we need to define a default order-by, since none was provided.
                order_by_clause = " OVER (ORDER BY %s.%s)" % \
                                  (qn(opts.db_table), qn(opts.fields[0].db_column or opts.fields[0].column))
            # limit_and_offset_clause
            if self._limit is None:
                assert self._offset is None, "'offset' is not allowed without 'limit'"

            if self._offset is not None:
                offset = int(self._offset)
            else:
                offset = 0
            if self._limit is not None:
                limit = int(self._limit)
            else:
                limit = None

            limit_and_offset_clause = ''
            if limit is not None:
                limit_and_offset_clause = "WHERE rn > %s AND rn <= %s" % (offset, limit+offset)
            elif offset:
                limit_and_offset_clause = "WHERE rn > %s" % (offset)

            if len(limit_and_offset_clause) > 0:
                fmt = \
    """SELECT * FROM
      (SELECT %s%s,
              ROW_NUMBER()%s AS rn
       %s)
    %s"""
                full_query = fmt % (distinct, select_clause,
                                        order_by_clause, ' '.join(sql).strip(),
                                        limit_and_offset_clause)
            else:
                full_query = None

            if get_full_query:
                return select, " ".join(sql), params, full_query
            else:
                return select, " ".join(sql), params

    def _clone(self, klass=None, **kwargs):
        c = super(GeoQuerySet, self)._clone(klass, **kwargs)
        c._custom_select = self._custom_select
        c._ewkt = self._ewkt
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

    def _get_geofield(self):
        "Returns the name of the first Geometry field encountered."
        for field in self.model._meta.fields:
            if isinstance(field, GeometryField): 
                return field.name
        raise Exception('No GeometryFields in the model.')

    def distance(self, *args, **kwargs):
        """
        Returns the distance from the given geographic field name to the
        given geometry in a `distance` attribute on each element of the
        GeoQuerySet.
        """
        if not DISTANCE:
            raise ImproperlyConfigured('Distance() stored proecedure not available.')

        # Getting the geometry field and GEOSGeometry object to base distance 
        # calculations from.
        nargs = len(args)
        if nargs == 1:
            field_name = self._get_geofield()
            geom = args[0]
        elif nargs == 2:
            field_name, geom = args
        else:
            raise ValueError('Maximum two arguments allowed for `distance` aggregate.')

        # Getting the quoted column.
        field_col = self._geo_column(field_name)
        if not field_col:
            raise TypeError('Distance output only available on GeometryFields.')

        # Getting the geographic field instance.
        geo_field = self.model._meta.get_field(field_name)

        # Using the field's get_db_prep_lookup() to get any needed 
        # transformation SQL -- we pass in a 'dummy' `contains` lookup
        # type.
        geom_sql = geo_field.get_db_prep_lookup('contains', geom)
        if oracle:
            # The `tolerance` keyword may be used for Oracle.
            tolerance = kwargs.get('tolerance', 0.05)

            # More legwork here because the OracleSpatialAdaptor doesn't do
            # quoting of the WKT.
            params = ["'%s'" % geom_sql.params[0]]
            params.extend(geom_sql.params[1:])
            gsql = geom_sql.where[0] % tuple(params)
            dist_select = {'distance' : '%s(%s, %s, %s)' % (DISTANCE, field_col, gsql, tolerance)}
        else:
            dist_select = {'distance' : '%s(%s, %s)' % (DISTANCE, field_col, geom_sql)}
        return self.extra(select=dist_select)

    def gml(self, field_name=None, precision=8, version=2):
        """
        Returns GML representation of the given field in a `gml` attribute
        on each element of the GeoQuerySet.
        """
        # Is GML output supported?
        if not ASGML:
            raise ImproperlyConfigured('AsGML() stored procedure not available.')

        # If no field name explicitly given, get the first GeometryField from
        # the model.
        if not field_name:
            field_name = self._get_geofield()

        field_col = self._geo_column(field_name)
        if not field_col:
            raise TypeError('GML output only available on GeometryFields.')
        
        if oracle:
            gml_select = {'gml':'%s(%s)' % (ASGML, field_col)}
        elif postgis:
            # PostGIS AsGML() aggregate function parameter order depends on the
            # version -- uggh.
            major, minor1, minor2 = VERSION
            if major >= 1 and (minor1 > 3 or (minor1 == 3 and minor2 > 1)):
                gml_select = {'gml':'%s(%s,%s,%s)' % (ASGML, version, field_col, precision)}
            else:
                gml_select = {'gml':'%s(%s,%s,%s)' % (ASGML, field_col, precision, version)}

        # Adding GML function call to SELECT part of the SQL.
        return self.extra(select=gml_select)

    def kml(self, field_name=None, precision=8):
        """
        Returns KML representation of the given field name in a `kml` 
        attribute on each element of the GeoQuerySet.
        """
        # Is KML output supported?
        if not ASKML:
            raise ImproperlyConfigured('AsKML() stored procedure not available.')

        # Getting the geographic field.
        if not field_name:
            field_name = self._get_geofield()

        field_col = self._geo_column(field_name)
        if not field_col:
            raise TypeError('KML output only available on GeometryFields.')
        
        # Adding the AsKML function call to SELECT part of the SQL.
        return self.extra(select={'kml':'%s(%s,%s)' % (ASKML, field_col, precision)})

    def transform(self, field_name=None, srid=4326):
        """
        Transforms the given geometry field to the given SRID.  If no SRID is
        provided, the transformation will default to using 4326 (WGS84).
        """
        # Getting the geographic field.
        if not field_name:
            field_name = self._get_geofield()
        elif isinstance(field_name, int):
            srid = field_name
            field_name = self._get_geofield()

        field = self.model._meta.get_field(field_name)
        if not isinstance(field, GeometryField):
            raise TypeError('%s() only available for GeometryFields' % TRANSFORM)

        # Why cascading substitutions? Because spatial backends like
        # Oracle and MySQL already require a function call to convert to text, thus
        # when there's also a transformation we need to cascade the substitutions.
        # For example, 'SDO_UTIL.TO_WKTGEOMETRY(SDO_CS.TRANSFORM( ... )'
        col = self._custom_select.get(field.column, self._field_column(field))

        # Setting the key for the field's column with the custom SELECT SQL to 
        # override the geometry column returned from the database.
        if oracle:
            custom_sel = '%s(%s, %s)' % (TRANSFORM, col, srid)
            self._ewkt = srid
        else:
            custom_sel = '(%s(%s, %s)) AS %s' % \
                         (TRANSFORM, col, srid, connection.ops.quote_name(field.column))
        self._custom_select[field.column] = custom_sel
        return self._clone()

    def union(self, field_name=None, tolerance=0.0005):
        """
        Performs an aggregate union on the given geometry field.  Returns
        None if the GeoQuerySet is empty.  The `tolerance` keyword is for
        Oracle backends only.
        """
        # Making sure backend supports the Union stored procedure
        if not UNION:
            raise ImproperlyConfigured('Union stored procedure not available.')

        # Getting the geographic field column
        if not field_name:
            field_name = self._get_geofield()

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
        if oracle:
            union_sql = 'SELECT %s' % self._geo_fmt
            union_sql = union_sql % ('%s(SDOAGGRTYPE(%s,%s))' % (UNION, field_col, tolerance))
            union_sql += sql
        else:
            union_sql = ('SELECT %s(%s)' % (UNION, field_col)) + sql

        # Getting a cursor, executing the query.
        cursor = connection.cursor()
        cursor.execute(union_sql, params)

        if oracle:
            # On Oracle have to read out WKT from CLOB first.
            clob = cursor.fetchone()[0]
            if clob: u = clob.read()
            else: u = None
        else:
            u = cursor.fetchone()[0]

        if u: return GEOSGeometry(u)
        else: return None
