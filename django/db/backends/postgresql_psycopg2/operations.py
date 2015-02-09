from __future__ import unicode_literals

from psycopg2.extras import Inet

from django.conf import settings
from django.db.backends.base.operations import BaseDatabaseOperations


class DatabaseOperations(BaseDatabaseOperations):
    def unification_cast_sql(self, output_field):
        internal_type = output_field.get_internal_type()
        if internal_type in ("GenericIPAddressField", "IPAddressField", "TimeField", "UUIDField"):
            # PostgreSQL will resolve a union as type 'text' if input types are
            # 'unknown'.
            # http://www.postgresql.org/docs/9.4/static/typeconv-union-case.html
            # These fields cannot be implicitly cast back in the default
            # PostgreSQL configuration so we need to explicitly cast them.
            # We must also remove components of the type within brackets:
            # varchar(255) -> varchar.
            return 'CAST(%%s AS %s)' % output_field.db_type(self.connection).split('(')[0]
        return '%s'

    def date_extract_sql(self, lookup_type, field_name):
        # http://www.postgresql.org/docs/current/static/functions-datetime.html#FUNCTIONS-DATETIME-EXTRACT
        if lookup_type == 'week_day':
            # For consistency across backends, we return Sunday=1, Saturday=7.
            return "EXTRACT('dow' FROM %s) + 1" % field_name
        else:
            return "EXTRACT('%s' FROM %s)" % (lookup_type, field_name)

    def date_trunc_sql(self, lookup_type, field_name):
        # http://www.postgresql.org/docs/current/static/functions-datetime.html#FUNCTIONS-DATETIME-TRUNC
        return "DATE_TRUNC('%s', %s)" % (lookup_type, field_name)

    def datetime_extract_sql(self, lookup_type, field_name, tzname):
        if settings.USE_TZ:
            field_name = "%s AT TIME ZONE %%s" % field_name
            params = [tzname]
        else:
            params = []
        # http://www.postgresql.org/docs/current/static/functions-datetime.html#FUNCTIONS-DATETIME-EXTRACT
        if lookup_type == 'week_day':
            # For consistency across backends, we return Sunday=1, Saturday=7.
            sql = "EXTRACT('dow' FROM %s) + 1" % field_name
        else:
            sql = "EXTRACT('%s' FROM %s)" % (lookup_type, field_name)
        return sql, params

    def datetime_trunc_sql(self, lookup_type, field_name, tzname):
        if settings.USE_TZ:
            field_name = "%s AT TIME ZONE %%s" % field_name
            params = [tzname]
        else:
            params = []
        # http://www.postgresql.org/docs/current/static/functions-datetime.html#FUNCTIONS-DATETIME-TRUNC
        sql = "DATE_TRUNC('%s', %s)" % (lookup_type, field_name)
        return sql, params

    def deferrable_sql(self):
        return " DEFERRABLE INITIALLY DEFERRED"

    def lookup_cast(self, lookup_type, internal_type=None):
        lookup = '%s'

        # Cast text lookups to text to allow things like filter(x__contains=4)
        if lookup_type in ('iexact', 'contains', 'icontains', 'startswith',
                           'istartswith', 'endswith', 'iendswith', 'regex', 'iregex'):
            if internal_type in ('IPAddressField', 'GenericIPAddressField'):
                lookup = "HOST(%s)"
            else:
                lookup = "%s::text"

        # Use UPPER(x) for case-insensitive lookups; it's faster.
        if lookup_type in ('iexact', 'icontains', 'istartswith', 'iendswith'):
            lookup = 'UPPER(%s)' % lookup

        return lookup

    def last_insert_id(self, cursor, table_name, pk_name):
        # Use pg_get_serial_sequence to get the underlying sequence name
        # from the table name and column name (available since PostgreSQL 8)
        cursor.execute("SELECT CURRVAL(pg_get_serial_sequence('%s','%s'))" % (
            self.quote_name(table_name), pk_name))
        return cursor.fetchone()[0]

    def no_limit_value(self):
        return None

    def prepare_sql_script(self, sql, _allow_fallback=False):
        return [sql]

    def quote_name(self, name):
        if name.startswith('"') and name.endswith('"'):
            return name  # Quoting once is enough.
        return '"%s"' % name

    def set_time_zone_sql(self):
        return "SET TIME ZONE %s"

    def sql_flush(self, style, tables, sequences, allow_cascade=False):
        if tables:
            # Perform a single SQL 'TRUNCATE x, y, z...;' statement.  It allows
            # us to truncate tables referenced by a foreign key in any other
            # table.
            tables_sql = ', '.join(
                style.SQL_FIELD(self.quote_name(table)) for table in tables)
            if allow_cascade:
                sql = ['%s %s %s;' % (
                    style.SQL_KEYWORD('TRUNCATE'),
                    tables_sql,
                    style.SQL_KEYWORD('CASCADE'),
                )]
            else:
                sql = ['%s %s;' % (
                    style.SQL_KEYWORD('TRUNCATE'),
                    tables_sql,
                )]
            sql.extend(self.sequence_reset_by_name_sql(style, sequences))
            return sql
        else:
            return []

    def sequence_reset_by_name_sql(self, style, sequences):
        # 'ALTER SEQUENCE sequence_name RESTART WITH 1;'... style SQL statements
        # to reset sequence indices
        sql = []
        for sequence_info in sequences:
            table_name = sequence_info['table']
            column_name = sequence_info['column']
            if not (column_name and len(column_name) > 0):
                # This will be the case if it's an m2m using an autogenerated
                # intermediate table (see BaseDatabaseIntrospection.sequence_list)
                column_name = 'id'
            sql.append("%s setval(pg_get_serial_sequence('%s','%s'), 1, false);" %
                (style.SQL_KEYWORD('SELECT'),
                style.SQL_TABLE(self.quote_name(table_name)),
                style.SQL_FIELD(column_name))
            )
        return sql

    def tablespace_sql(self, tablespace, inline=False):
        if inline:
            return "USING INDEX TABLESPACE %s" % self.quote_name(tablespace)
        else:
            return "TABLESPACE %s" % self.quote_name(tablespace)

    def sequence_reset_sql(self, style, model_list):
        from django.db import models
        output = []
        qn = self.quote_name
        for model in model_list:
            # Use `coalesce` to set the sequence for each model to the max pk value if there are records,
            # or 1 if there are none. Set the `is_called` property (the third argument to `setval`) to true
            # if there are records (as the max pk value is already in use), otherwise set it to false.
            # Use pg_get_serial_sequence to get the underlying sequence name from the table name
            # and column name (available since PostgreSQL 8)

            for f in model._meta.local_fields:
                if isinstance(f, models.AutoField):
                    output.append(
                        "%s setval(pg_get_serial_sequence('%s','%s'), "
                        "coalesce(max(%s), 1), max(%s) %s null) %s %s;" % (
                            style.SQL_KEYWORD('SELECT'),
                            style.SQL_TABLE(qn(model._meta.db_table)),
                            style.SQL_FIELD(f.column),
                            style.SQL_FIELD(qn(f.column)),
                            style.SQL_FIELD(qn(f.column)),
                            style.SQL_KEYWORD('IS NOT'),
                            style.SQL_KEYWORD('FROM'),
                            style.SQL_TABLE(qn(model._meta.db_table)),
                        )
                    )
                    break  # Only one AutoField is allowed per model, so don't bother continuing.
            for f in model._meta.many_to_many:
                if not f.rel.through:
                    output.append(
                        "%s setval(pg_get_serial_sequence('%s','%s'), "
                        "coalesce(max(%s), 1), max(%s) %s null) %s %s;" % (
                            style.SQL_KEYWORD('SELECT'),
                            style.SQL_TABLE(qn(f.m2m_db_table())),
                            style.SQL_FIELD('id'),
                            style.SQL_FIELD(qn('id')),
                            style.SQL_FIELD(qn('id')),
                            style.SQL_KEYWORD('IS NOT'),
                            style.SQL_KEYWORD('FROM'),
                            style.SQL_TABLE(qn(f.m2m_db_table()))
                        )
                    )
        return output

    def prep_for_iexact_query(self, x):
        return x

    def max_name_length(self):
        """
        Returns the maximum length of an identifier.

        Note that the maximum length of an identifier is 63 by default, but can
        be changed by recompiling PostgreSQL after editing the NAMEDATALEN
        macro in src/include/pg_config_manual.h .

        This implementation simply returns 63, but can easily be overridden by a
        custom database backend that inherits most of its behavior from this one.
        """

        return 63

    def distinct_sql(self, fields):
        if fields:
            return 'DISTINCT ON (%s)' % ', '.join(fields)
        else:
            return 'DISTINCT'

    def last_executed_query(self, cursor, sql, params):
        # http://initd.org/psycopg/docs/cursor.html#cursor.query
        # The query attribute is a Psycopg extension to the DB API 2.0.
        if cursor.query is not None:
            return cursor.query.decode('utf-8')
        return None

    def return_insert_id(self):
        return "RETURNING %s", ()

    def bulk_insert_sql(self, fields, num_values):
        items_sql = "(%s)" % ", ".join(["%s"] * len(fields))
        return "VALUES " + ", ".join([items_sql] * num_values)

    def value_to_db_date(self, value):
        return value

    def value_to_db_datetime(self, value):
        return value

    def value_to_db_time(self, value):
        return value

    def value_to_db_ipaddress(self, value):
        if value:
            return Inet(value)
        return None
