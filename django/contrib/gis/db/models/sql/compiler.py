import datetime

from django.conf import settings
from django.db.backends.util import truncate_name, typecast_date, typecast_timestamp
from django.db.models.sql import compiler
from django.db.models.sql.constants import MULTI
from django.utils import six
from django.utils.six.moves import zip, zip_longest
from django.utils import timezone

SQLCompiler = compiler.SQLCompiler

class GeoSQLCompiler(compiler.SQLCompiler):

    def get_columns(self, with_aliases=False):
        """
        Return the list of columns to use in the select statement. If no
        columns have been specified, returns all columns relating to fields in
        the model.

        If 'with_aliases' is true, any column names that are duplicated
        (without the table names) are given unique aliases. This is needed in
        some cases to avoid ambiguitity with nested queries.

        This routine is overridden from Query to handle customized selection of
        geometry columns.
        """
        qn = self.quote_name_unless_alias
        qn2 = self.connection.ops.quote_name
        result = ['(%s) AS %s' % (self.get_extra_select_format(alias) % col[0], qn2(alias))
                  for alias, col in six.iteritems(self.query.extra_select)]
        params = []
        aliases = set(self.query.extra_select.keys())
        if with_aliases:
            col_aliases = aliases.copy()
        else:
            col_aliases = set()
        if self.query.select:
            only_load = self.deferred_to_columns()
            # This loop customized for GeoQuery.
            for col, field in self.query.select:
                if isinstance(col, (list, tuple)):
                    alias, column = col
                    table = self.query.alias_map[alias].table_name
                    if table in only_load and column not in only_load[table]:
                        continue
                    r = self.get_field_select(field, alias, column)
                    if with_aliases:
                        if col[1] in col_aliases:
                            c_alias = 'Col%d' % len(col_aliases)
                            result.append('%s AS %s' % (r, c_alias))
                            aliases.add(c_alias)
                            col_aliases.add(c_alias)
                        else:
                            result.append('%s AS %s' % (r, qn2(col[1])))
                            aliases.add(r)
                            col_aliases.add(col[1])
                    else:
                        result.append(r)
                        aliases.add(r)
                        col_aliases.add(col[1])
                else:
                    col_sql, col_params = col.as_sql(qn, self.connection)
                    result.append(col_sql)
                    params.extend(col_params)

                    if hasattr(col, 'alias'):
                        aliases.add(col.alias)
                        col_aliases.add(col.alias)

        elif self.query.default_cols:
            cols, new_aliases = self.get_default_columns(with_aliases,
                    col_aliases)
            result.extend(cols)
            aliases.update(new_aliases)

        max_name_length = self.connection.ops.max_name_length()
        for alias, aggregate in self.query.aggregate_select.items():
            agg_sql, agg_params = aggregate.as_sql(qn, self.connection)
            if alias is None:
                result.append(agg_sql)
            else:
                result.append('%s AS %s' % (agg_sql, qn(truncate_name(alias, max_name_length))))
            params.extend(agg_params)

        # This loop customized for GeoQuery.
        for (table, col), field in self.query.related_select_cols:
            r = self.get_field_select(field, table, col)
            if with_aliases and col in col_aliases:
                c_alias = 'Col%d' % len(col_aliases)
                result.append('%s AS %s' % (r, c_alias))
                aliases.add(c_alias)
                col_aliases.add(c_alias)
            else:
                result.append(r)
                aliases.add(r)
                col_aliases.add(col)

        self._select_aliases = aliases
        return result, params

    def get_default_columns(self, with_aliases=False, col_aliases=None,
            start_alias=None, opts=None, as_pairs=False, from_parent=None):
        """
        Computes the default columns for selecting every field in the base
        model. Will sometimes be called to pull in related models (e.g. via
        select_related), in which case "opts" and "start_alias" will be given
        to provide a starting point for the traversal.

        Returns a list of strings, quoted appropriately for use in SQL
        directly, as well as a set of aliases used in the select statement (if
        'as_pairs' is True, returns a list of (alias, col_name) pairs instead
        of strings as the first component and None as the second component).

        This routine is overridden from Query to handle customized selection of
        geometry columns.
        """
        result = []
        if opts is None:
            opts = self.query.get_meta()
        aliases = set()
        only_load = self.deferred_to_columns()
        seen = self.query.included_inherited_models.copy()
        if start_alias:
            seen[None] = start_alias
        for field, model in opts.get_concrete_fields_with_model():
            if from_parent and model is not None and issubclass(from_parent, model):
                # Avoid loading data for already loaded parents.
                continue
            alias = self.query.join_parent_model(opts, model, start_alias, seen)
            table = self.query.alias_map[alias].table_name
            if table in only_load and field.column not in only_load[table]:
                continue
            if as_pairs:
                result.append((alias, field))
                aliases.add(alias)
                continue
            # This part of the function is customized for GeoQuery. We
            # see if there was any custom selection specified in the
            # dictionary, and set up the selection format appropriately.
            field_sel = self.get_field_select(field, alias)
            if with_aliases and field.column in col_aliases:
                c_alias = 'Col%d' % len(col_aliases)
                result.append('%s AS %s' % (field_sel, c_alias))
                col_aliases.add(c_alias)
                aliases.add(c_alias)
            else:
                r = field_sel
                result.append(r)
                aliases.add(r)
                if with_aliases:
                    col_aliases.add(field.column)
        return result, aliases

    def resolve_columns(self, row, fields=()):
        """
        This routine is necessary so that distances and geometries returned
        from extra selection SQL get resolved appropriately into Python
        objects.
        """
        values = []
        aliases = list(self.query.extra_select)

        # Have to set a starting row number offset that is used for
        # determining the correct starting row index -- needed for
        # doing pagination with Oracle.
        rn_offset = 0
        if self.connection.ops.oracle:
            if self.query.high_mark is not None or self.query.low_mark: rn_offset = 1
        index_start = rn_offset + len(aliases)

        # Converting any extra selection values (e.g., geometries and
        # distance objects added by GeoQuerySet methods).
        values = [self.query.convert_values(v,
                               self.query.extra_select_fields.get(a, None),
                               self.connection)
                  for v, a in zip(row[rn_offset:index_start], aliases)]
        if self.connection.ops.oracle or getattr(self.query, 'geo_values', False):
            # We resolve the rest of the columns if we're on Oracle or if
            # the `geo_values` attribute is defined.
            for value, field in zip_longest(row[index_start:], fields):
                values.append(self.query.convert_values(value, field, self.connection))
        else:
            values.extend(row[index_start:])
        return tuple(values)

    #### Routines unique to GeoQuery ####
    def get_extra_select_format(self, alias):
        sel_fmt = '%s'
        if hasattr(self.query, 'custom_select') and alias in self.query.custom_select:
            sel_fmt = sel_fmt % self.query.custom_select[alias]
        return sel_fmt

    def get_field_select(self, field, alias=None, column=None):
        """
        Returns the SELECT SQL string for the given field.  Figures out
        if any custom selection SQL is needed for the column  The `alias`
        keyword may be used to manually specify the database table where
        the column exists, if not in the model associated with this
        `GeoQuery`.  Similarly, `column` may be used to specify the exact
        column name, rather than using the `column` attribute on `field`.
        """
        sel_fmt = self.get_select_format(field)
        if field in self.query.custom_select:
            field_sel = sel_fmt % self.query.custom_select[field]
        else:
            field_sel = sel_fmt % self._field_column(field, alias, column)
        return field_sel

    def get_select_format(self, fld):
        """
        Returns the selection format string, depending on the requirements
        of the spatial backend.  For example, Oracle and MySQL require custom
        selection formats in order to retrieve geometries in OGC WKT. For all
        other fields a simple '%s' format string is returned.
        """
        if self.connection.ops.select and hasattr(fld, 'geom_type'):
            # This allows operations to be done on fields in the SELECT,
            # overriding their values -- used by the Oracle and MySQL
            # spatial backends to get database values as WKT, and by the
            # `transform` method.
            sel_fmt = self.connection.ops.select

            # Because WKT doesn't contain spatial reference information,
            # the SRID is prefixed to the returned WKT to ensure that the
            # transformed geometries have an SRID different than that of the
            # field -- this is only used by `transform` for Oracle and
            # SpatiaLite backends.
            if self.query.transformed_srid and ( self.connection.ops.oracle or
                                                 self.connection.ops.spatialite ):
                sel_fmt = "'SRID=%d;'||%s" % (self.query.transformed_srid, sel_fmt)
        else:
            sel_fmt = '%s'
        return sel_fmt

    # Private API utilities, subject to change.
    def _field_column(self, field, table_alias=None, column=None):
        """
        Helper function that returns the database column for the given field.
        The table and column are returned (quoted) in the proper format, e.g.,
        `"geoapp_city"."point"`.  If `table_alias` is not specified, the
        database table associated with the model of this `GeoQuery` will be
        used.  If `column` is specified, it will be used instead of the value
        in `field.column`.
        """
        if table_alias is None: table_alias = self.query.get_meta().db_table
        return "%s.%s" % (self.quote_name_unless_alias(table_alias),
                          self.connection.ops.quote_name(column or field.column))

class SQLInsertCompiler(compiler.SQLInsertCompiler, GeoSQLCompiler):
    pass

class SQLDeleteCompiler(compiler.SQLDeleteCompiler, GeoSQLCompiler):
    pass

class SQLUpdateCompiler(compiler.SQLUpdateCompiler, GeoSQLCompiler):
    pass

class SQLAggregateCompiler(compiler.SQLAggregateCompiler, GeoSQLCompiler):
    pass

class SQLDateCompiler(compiler.SQLDateCompiler, GeoSQLCompiler):
    """
    This is overridden for GeoDjango to properly cast date columns, since
    `GeoQuery.resolve_columns` is used for spatial values.
    See #14648, #16757.
    """
    def results_iter(self):
        if self.connection.ops.oracle:
            from django.db.models.fields import DateTimeField
            fields = [DateTimeField()]
        else:
            needs_string_cast = self.connection.features.needs_datetime_string_cast

        offset = len(self.query.extra_select)
        for rows in self.execute_sql(MULTI):
            for row in rows:
                date = row[offset]
                if self.connection.ops.oracle:
                    date = self.resolve_columns(row, fields)[offset]
                elif needs_string_cast:
                    date = typecast_date(str(date))
                if isinstance(date, datetime.datetime):
                    date = date.date()
                yield date

class SQLDateTimeCompiler(compiler.SQLDateTimeCompiler, GeoSQLCompiler):
    """
    This is overridden for GeoDjango to properly cast date columns, since
    `GeoQuery.resolve_columns` is used for spatial values.
    See #14648, #16757.
    """
    def results_iter(self):
        if self.connection.ops.oracle:
            from django.db.models.fields import DateTimeField
            fields = [DateTimeField()]
        else:
            needs_string_cast = self.connection.features.needs_datetime_string_cast

        offset = len(self.query.extra_select)
        for rows in self.execute_sql(MULTI):
            for row in rows:
                datetime = row[offset]
                if self.connection.ops.oracle:
                    datetime = self.resolve_columns(row, fields)[offset]
                elif needs_string_cast:
                    datetime = typecast_timestamp(str(datetime))
                # Datetimes are artifically returned in UTC on databases that
                # don't support time zone. Restore the zone used in the query.
                if settings.USE_TZ:
                    datetime = datetime.replace(tzinfo=None)
                    datetime = timezone.make_aware(datetime, self.query.tzinfo)
                yield datetime
