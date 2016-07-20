import re
import warnings

from django.db.backends.base.introspection import (
    BaseDatabaseIntrospection, FieldInfo, TableInfo,
)
from django.db.models.indexes import Index
from django.utils.deprecation import RemovedInDjango21Warning


class DatabaseIntrospection(BaseDatabaseIntrospection):
    # Maps type codes to Django Field types.
    data_types_reverse = {
        16: 'BooleanField',
        17: 'BinaryField',
        20: 'BigIntegerField',
        21: 'SmallIntegerField',
        23: 'IntegerField',
        25: 'TextField',
        700: 'FloatField',
        701: 'FloatField',
        869: 'GenericIPAddressField',
        1000: ('django.contrib.postgresql.fields.ArrayField',
               {'__args__': ['models.BooleanField()']}),
        1005: ('django.contrib.postgresql.fields.ArrayField',
               {'__args__': ['models.SmallIntegerField()']}),
        1007: ('django.contrib.postgresql.fields.ArrayField',
               {'__args__': ['models.IntegerField()']}),
        1009: ('django.contrib.postgresql.fields.ArrayField',
               {'__args__': ['models.TextField()']}),
        1015: ('django.contrib.postgresql.fields.ArrayField',
               {'__args__': ['models.CharField(max_length=%(internal_size)d)']}),
        1041: ('django.contrib.postgresql.fields.ArrayField',
               {'__args__': ['models.GenericIPAddressField()']}),
        1042: 'CharField',  # blank-padded
        1043: 'CharField',
        1082: 'DateField',
        1083: 'TimeField',
        1114: 'DateTimeField',
        1182: ('django.contrib.postgresql.fields.ArrayField',
               {'__args__': ['models.DateField()']}),
        1183: ('django.contrib.postgresql.fields.ArrayField',
               {'__args__': ['models.TimeField()']}),
        1184: 'DateTimeField',
        1185: ('django.contrib.postgresql.fields.ArrayField',
               {'__args__': ['models.DateTimeField()']}),
        1231: ('django.contrib.postgresql.fields.ArrayField',
               {'__args__': [
                'models.DecimalField(max_digits=%(precision)d, decimal_places=%(scale)d)']}),
        1266: 'TimeField',
        1700: 'DecimalField',
        2950: 'UUIDField',
        2951: ('django.contrib.postgresql.fields.ArrayField',
               {'__args__': ['models.UUIDField()']}),
        # HStoreField oid is registered in register_hstore_handler
    }

    ignored_tables = []

    _get_indexes_query = """
        SELECT attr.attname, idx.indkey, idx.indisunique, idx.indisprimary
        FROM pg_catalog.pg_class c, pg_catalog.pg_class c2,
            pg_catalog.pg_index idx, pg_catalog.pg_attribute attr
        WHERE c.oid = idx.indrelid
            AND idx.indexrelid = c2.oid
            AND attr.attrelid = c.oid
            AND attr.attnum = idx.indkey[0]
            AND c.relname = %s"""

    def get_field_type(self, data_type, description):
        field_type = super().get_field_type(data_type, description)
        if description.default and 'nextval' in description.default:
            if field_type == 'IntegerField':
                return 'AutoField'
            elif field_type == 'BigIntegerField':
                return 'BigAutoField'
        if data_type in (1015, 1231):
            field_type[1]['__args__'][0] %= description._asdict()
        return field_type

    def get_table_list(self, cursor):
        """Return a list of table and view names in the current database."""
        cursor.execute("""
            SELECT c.relname, c.relkind
            FROM pg_catalog.pg_class c
            LEFT JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
            WHERE c.relkind IN ('r', 'v')
                AND n.nspname NOT IN ('pg_catalog', 'pg_toast')
                AND pg_catalog.pg_table_is_visible(c.oid)""")
        return [TableInfo(row[0], {'r': 't', 'v': 'v'}.get(row[1]))
                for row in cursor.fetchall()
                if row[0] not in self.ignored_tables]

    def get_table_description(self, cursor, table_name):
        """
        Return a description of the table with the DB-API cursor.description
        interface.
        """
        # As cursor.description does not return reliably the nullable property,
        # we have to query the information_schema (#7783)

        def patch_array_decimals(col_details):
            if col_details.type_code == 1231:
                # Getting nested DecimalField max_digits and decimal_places through pg_attributes
                cursor.execute("""
                    SELECT format_type(attr.atttypid, attr.atttypmod)
                    FROM pg_catalog.pg_class c, pg_attribute attr
                    WHERE attr.attname = %s AND c.relname = %s AND attr.attrelid = c.oid
                """, [col_details.name, table_name])
                m = re.match(r'numeric\(([0-9])+,([0-9])+\)', cursor.fetchone()[0])
                col_details = col_details._replace(precision=int(m.groups()[0]), scale=int(m.groups()[1]))
            return col_details[0:6]

        cursor.execute("""
            SELECT column_name, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_name = %s""", [table_name])
        field_map = {line[0]: line[1:] for line in cursor.fetchall()}
        cursor.execute("SELECT * FROM %s LIMIT 1" % self.connection.ops.quote_name(table_name))
        return [
            FieldInfo(
                *(patch_array_decimals(line) +
                (field_map[line.name][0] == 'YES', field_map[line.name][1]))
            ) for line in cursor.description
        ]

    def get_relations(self, cursor, table_name):
        """
        Return a dictionary of {field_name: (field_name_other_table, other_table)}
        representing all relationships to the given table.
        """
        cursor.execute("""
            SELECT c2.relname, a1.attname, a2.attname
            FROM pg_constraint con
            LEFT JOIN pg_class c1 ON con.conrelid = c1.oid
            LEFT JOIN pg_class c2 ON con.confrelid = c2.oid
            LEFT JOIN pg_attribute a1 ON c1.oid = a1.attrelid AND a1.attnum = con.conkey[1]
            LEFT JOIN pg_attribute a2 ON c2.oid = a2.attrelid AND a2.attnum = con.confkey[1]
            WHERE c1.relname = %s
                AND con.contype = 'f'""", [table_name])
        relations = {}
        for row in cursor.fetchall():
            relations[row[1]] = (row[2], row[0])
        return relations

    def get_key_columns(self, cursor, table_name):
        key_columns = []
        cursor.execute("""
            SELECT kcu.column_name, ccu.table_name AS referenced_table, ccu.column_name AS referenced_column
            FROM information_schema.constraint_column_usage ccu
            LEFT JOIN information_schema.key_column_usage kcu
                ON ccu.constraint_catalog = kcu.constraint_catalog
                    AND ccu.constraint_schema = kcu.constraint_schema
                    AND ccu.constraint_name = kcu.constraint_name
            LEFT JOIN information_schema.table_constraints tc
                ON ccu.constraint_catalog = tc.constraint_catalog
                    AND ccu.constraint_schema = tc.constraint_schema
                    AND ccu.constraint_name = tc.constraint_name
            WHERE kcu.table_name = %s AND tc.constraint_type = 'FOREIGN KEY'""", [table_name])
        key_columns.extend(cursor.fetchall())
        return key_columns

    def get_indexes(self, cursor, table_name):
        warnings.warn(
            "get_indexes() is deprecated in favor of get_constraints().",
            RemovedInDjango21Warning, stacklevel=2
        )
        # This query retrieves each index on the given table, including the
        # first associated field name
        cursor.execute(self._get_indexes_query, [table_name])
        indexes = {}
        for row in cursor.fetchall():
            # row[1] (idx.indkey) is stored in the DB as an array. It comes out as
            # a string of space-separated integers. This designates the field
            # indexes (1-based) of the fields that have indexes on the table.
            # Here, we skip any indexes across multiple fields.
            if ' ' in row[1]:
                continue
            if row[0] not in indexes:
                indexes[row[0]] = {'primary_key': False, 'unique': False}
            # It's possible to have the unique and PK constraints in separate indexes.
            if row[3]:
                indexes[row[0]]['primary_key'] = True
            if row[2]:
                indexes[row[0]]['unique'] = True
        return indexes

    def get_constraints(self, cursor, table_name):
        """
        Retrieve any constraints or keys (unique, pk, fk, check, index) across
        one or more columns. Also retrieve the definition of expression-based
        indexes.
        """
        constraints = {}
        # Loop over the key table, collecting things as constraints. The column
        # array must return column names in the same order in which they were
        # created.
        # The subquery containing generate_series can be replaced with
        # "WITH ORDINALITY" when support for PostgreSQL 9.3 is dropped.
        cursor.execute("""
            SELECT
                c.conname,
                array(
                    SELECT attname
                    FROM (
                        SELECT unnest(c.conkey) AS colid,
                               generate_series(1, array_length(c.conkey, 1)) AS arridx
                    ) AS cols
                    JOIN pg_attribute AS ca ON cols.colid = ca.attnum
                    WHERE ca.attrelid = c.conrelid
                    ORDER BY cols.arridx
                ),
                c.contype,
                (SELECT fkc.relname || '.' || fka.attname
                FROM pg_attribute AS fka
                JOIN pg_class AS fkc ON fka.attrelid = fkc.oid
                WHERE fka.attrelid = c.confrelid AND fka.attnum = c.confkey[1]),
                cl.reloptions
            FROM pg_constraint AS c
            JOIN pg_class AS cl ON c.conrelid = cl.oid
            JOIN pg_namespace AS ns ON cl.relnamespace = ns.oid
            WHERE ns.nspname = %s AND cl.relname = %s
        """, ["public", table_name])
        for constraint, columns, kind, used_cols, options in cursor.fetchall():
            constraints[constraint] = {
                "columns": columns,
                "primary_key": kind == "p",
                "unique": kind in ["p", "u"],
                "foreign_key": tuple(used_cols.split(".", 1)) if kind == "f" else None,
                "check": kind == "c",
                "index": False,
                "definition": None,
                "options": options,
            }
        # Now get indexes
        # The row_number() function for ordering the index fields can be
        # replaced by WITH ORDINALITY in the unnest() functions when support
        # for PostgreSQL 9.3 is dropped.
        cursor.execute("""
            SELECT
                indexname, array_agg(attname ORDER BY rnum), indisunique, indisprimary,
                array_agg(ordering ORDER BY rnum), amname, exprdef, s2.attoptions
            FROM (
                SELECT
                    row_number() OVER () as rnum, c2.relname as indexname,
                    idx.*, attr.attname, am.amname,
                    CASE
                        WHEN idx.indexprs IS NOT NULL THEN
                            pg_get_indexdef(idx.indexrelid)
                    END AS exprdef,
                    CASE am.amname
                        WHEN 'btree' THEN
                            CASE (option & 1)
                                WHEN 1 THEN 'DESC' ELSE 'ASC'
                            END
                    END as ordering,
                    c2.reloptions as attoptions
                FROM (
                    SELECT
                        *, unnest(i.indkey) as key, unnest(i.indoption) as option
                    FROM pg_index i
                ) idx
                LEFT JOIN pg_class c ON idx.indrelid = c.oid
                LEFT JOIN pg_class c2 ON idx.indexrelid = c2.oid
                LEFT JOIN pg_am am ON c2.relam = am.oid
                LEFT JOIN pg_attribute attr ON attr.attrelid = c.oid AND attr.attnum = idx.key
                WHERE c.relname = %s
            ) s2
            GROUP BY indexname, indisunique, indisprimary, amname, exprdef, attoptions;
        """, [table_name])
        for index, columns, unique, primary, orders, type_, definition, options in cursor.fetchall():
            if index not in constraints:
                constraints[index] = {
                    "columns": columns if columns != [None] else [],
                    "orders": orders if orders != [None] else [],
                    "primary_key": primary,
                    "unique": unique,
                    "foreign_key": None,
                    "check": False,
                    "index": True,
                    "type": Index.suffix if type_ == 'btree' else type_,
                    "definition": definition,
                    "options": options,
                }
        return constraints
