from django.db import DatabaseError
from django.db.backends.base.introspection import (
    BaseAsyncDatabaseIntrospection, TableInfo,
)
from django.db.backends.sqlite3.introspection import (
    DatabaseIntrospection as SQLiteDatabaseIntrospection, FieldInfo,
    FlexibleFieldLookupDict, get_field_size,
)
from django.db.models import Index


class DatabaseIntrospection(BaseAsyncDatabaseIntrospection, SQLiteDatabaseIntrospection):
    data_types_reverse = FlexibleFieldLookupDict()

    async def get_field_type(self, data_type, description):
        return super(SQLiteDatabaseIntrospection, self).get_field_type(data_type, description)

    async def get_table_list(self, cursor):
        """Return a list of table and view names in the current database."""
        await cursor.execute("""
            SELECT name, type FROM sqlite_master
            WHERE type in ('table', 'view') AND NOT name='sqlite_sequence'
            ORDER BY name""")
        return [TableInfo(row[0], row[1][0]) for row in await cursor.fetchall()]

    async def get_table_description(self, cursor, table_name):
        """
        Return a description of the table with the DB-API cursor.description
        interface.
        """
        await cursor.execute('PRAGMA table_info(%s)' % self.connection.ops.quote_name(table_name))
        table_info = await cursor.fetchall()
        if not table_info:
            raise DatabaseError(f'Table {table_name} does not exist (empty pragma).')
        collations = await self._get_column_collations(cursor, table_name)
        json_columns = set()
        if self.connection.features.can_introspect_json_field:
            for line in table_info:
                column = line[1]
                json_constraint_sql = '%%json_valid("%s")%%' % column
                await cursor.execute("""
                    SELECT sql
                    FROM sqlite_master
                    WHERE
                        type = 'table' AND
                        name = %s AND
                        sql LIKE %s
                """, [table_name, json_constraint_sql])
                has_json_constraint = await cursor.fetchone()
                if has_json_constraint:
                    json_columns.add(column)
        return [
            FieldInfo(
                name, data_type, None, get_field_size(data_type), None, None,
                not notnull, default, collations.get(name), pk == 1, name in json_columns
            )
            for cid, name, data_type, notnull, default, pk in table_info
        ]

    async def get_sequences(self, cursor, table_name, table_fields=()):
        pk_col = await self.get_primary_key_column(cursor, table_name)
        return [{'table': table_name, 'column': pk_col}]

    async def get_relations(self, cursor, table_name):
        """
        Return a dictionary of {column_name: (ref_column_name, ref_table_name)}
        representing all foreign keys in the given table.
        """
        await cursor.execute(
            'PRAGMA foreign_key_list(%s)' % self.connection.ops.quote_name(table_name)
        )
        return {
            column_name: (ref_column_name, ref_table_name)
            for _, _, ref_table_name, column_name, ref_column_name, *_ in await cursor.fetchall()
        }

    async def get_primary_key_column(self, cursor, table_name):
        """Return the column name of the primary key for the given table."""
        await cursor.execute(
            'PRAGMA table_info(%s)' % self.connection.ops.quote_name(table_name)
        )
        for _, name, *_, pk in await cursor.fetchall():
            if pk:
                return name
        return None

    async def get_constraints(self, cursor, table_name):
        """
        Retrieve any constraints or keys (unique, pk, fk, check, index) across
        one or more columns.
        """
        constraints = {}
        # Find inline check constraints.
        try:
            await cursor.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' and name=%s" % (
                    self.connection.ops.quote_name(table_name),
                )
            )
            table_schema = await cursor.fetchone()[0]
        except TypeError:
            # table_name is a view.
            pass
        else:
            columns = {info.name for info in await self.get_table_description(cursor, table_name)}
            constraints.update(self._parse_table_constraints(table_schema, columns))

        # Get the index info
        await cursor.execute("PRAGMA index_list(%s)" % self.connection.ops.quote_name(table_name))
        for row in await cursor.fetchall():
            # SQLite 3.8.9+ has 5 columns, however older versions only give 3
            # columns. Discard last 2 columns if there.
            number, index, unique = row[:3]
            await cursor.execute(
                "SELECT sql FROM sqlite_master "
                "WHERE type='index' AND name=%s" % self.connection.ops.quote_name(index)
            )
            # There's at most one row.
            sql, = await cursor.fetchone() or (None,)
            # Inline constraints are already detected in
            # _parse_table_constraints(). The reasons to avoid fetching inline
            # constraints from `PRAGMA index_list` are:
            # - Inline constraints can have a different name and information
            #   than what `PRAGMA index_list` gives.
            # - Not all inline constraints may appear in `PRAGMA index_list`.
            if not sql:
                # An inline constraint
                continue
            # Get the index info for that index
            await cursor.execute('PRAGMA index_info(%s)' % self.connection.ops.quote_name(index))
            for index_rank, column_rank, column in await cursor.fetchall():
                if index not in constraints:
                    constraints[index] = {
                        "columns": [],
                        "primary_key": False,
                        "unique": bool(unique),
                        "foreign_key": None,
                        "check": False,
                        "index": True,
                    }
                constraints[index]['columns'].append(column)
            # Add type and column orders for indexes
            if constraints[index]['index']:
                # SQLite doesn't support any index type other than b-tree
                constraints[index]['type'] = Index.suffix
                orders = self._get_index_columns_orders(sql)
                if orders is not None:
                    constraints[index]['orders'] = orders
        # Get the PK
        pk_column = await self.get_primary_key_column(cursor, table_name)
        if pk_column:
            # SQLite doesn't actually give a name to the PK constraint,
            # so we invent one. This is fine, as the SQLite backend never
            # deletes PK constraints by name, as you can't delete constraints
            # in SQLite; we remake the table with a new PK instead.
            constraints["__primary__"] = {
                "columns": [pk_column],
                "primary_key": True,
                "unique": False,  # It's not actually a unique constraint.
                "foreign_key": None,
                "check": False,
                "index": False,
            }
        relations = enumerate((await self.get_relations(cursor, table_name)).items())
        constraints.update({
            f'fk_{index}': {
                'columns': [column_name],
                'primary_key': False,
                'unique': False,
                'foreign_key': (ref_table_name, ref_column_name),
                'check': False,
                'index': False,
            }
            for index, (column_name, (ref_column_name, ref_table_name)) in relations
        })
        return constraints

    async def _get_column_collations(self, cursor, table_name):
        await cursor.execute("""
            SELECT sql
            FROM sqlite_master
            WHERE type = 'table' AND name = %s
        """, [table_name])
        row = await cursor.fetchone()
        return self._process_collations(row) if row else {}
