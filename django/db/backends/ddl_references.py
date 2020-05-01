"""
Helpers to manipulate deferred DDL statements that might need to be adjusted or
discarded within when executing a migration.
"""


class Reference:
    """Base class that defines the reference interface."""

    def references_table(self, table):
        """
        Return whether or not this instance references the specified table.
        """
        return False

    def references_column(self, table, column):
        """
        Return whether or not this instance references the specified column.
        """
        return False

    def rename_table_references(self, old_table, new_table):
        """
        Rename all references to the old_name to the new_table.
        """
        pass

    def rename_column_references(self, table, old_column, new_column):
        """
        Rename all references to the old_column to the new_column.
        """
        pass

    def __repr__(self):
        return '<%s %r>' % (self.__class__.__name__, str(self))

    def __str__(self):
        raise NotImplementedError('Subclasses must define how they should be converted to string.')


class Table(Reference):
    """Hold a reference to a table."""

    def __init__(self, table, quote_name):
        self.table = table
        self.quote_name = quote_name

    def references_table(self, table):
        return self.table == table

    def rename_table_references(self, old_table, new_table):
        if self.table == old_table:
            self.table = new_table

    def __str__(self):
        return self.quote_name(self.table)


class TableColumns(Table):
    """Base class for references to multiple columns of a table."""

    def __init__(self, table, columns):
        self.table = table
        self.columns = columns

    def references_column(self, table, column):
        return self.table == table and column in self.columns

    def rename_column_references(self, table, old_column, new_column):
        if self.table == table:
            for index, column in enumerate(self.columns):
                if column == old_column:
                    self.columns[index] = new_column


class Columns(TableColumns):
    """Hold a reference to one or many columns."""

    def __init__(self, table, columns, quote_name, col_suffixes=()):
        self.quote_name = quote_name
        self.col_suffixes = col_suffixes
        super().__init__(table, columns)

    def __str__(self):
        def col_str(column, idx):
            col = self.quote_name(column)
            try:
                suffix = self.col_suffixes[idx]
                if suffix:
                    col = '{} {}'.format(col, suffix)
            except IndexError:
                pass
            return col

        return ', '.join(col_str(column, idx) for idx, column in enumerate(self.columns))


class IndexName(TableColumns):
    """Hold a reference to an index name."""

    def __init__(self, table, columns, suffix, create_index_name):
        self.suffix = suffix
        self.create_index_name = create_index_name
        super().__init__(table, columns)

    def __str__(self):
        return self.create_index_name(self.table, self.columns, self.suffix)


class IndexColumns(Columns):
    def __init__(self, table, columns, quote_name, col_suffixes=(), opclasses=()):
        self.opclasses = opclasses
        super().__init__(table, columns, quote_name, col_suffixes)

    def __str__(self):
        def col_str(column, idx):
            # Index.__init__() guarantees that self.opclasses is the same
            # length as self.columns.
            col = '{} {}'.format(self.quote_name(column), self.opclasses[idx])
            try:
                suffix = self.col_suffixes[idx]
                if suffix:
                    col = '{} {}'.format(col, suffix)
            except IndexError:
                pass
            return col

        return ', '.join(col_str(column, idx) for idx, column in enumerate(self.columns))


class ForeignKeyName(TableColumns):
    """Hold a reference to a foreign key name."""

    def __init__(self, from_table, from_columns, to_table, to_columns, suffix_template, create_fk_name):
        self.to_reference = TableColumns(to_table, to_columns)
        self.suffix_template = suffix_template
        self.create_fk_name = create_fk_name
        super().__init__(from_table, from_columns,)

    def references_table(self, table):
        return super().references_table(table) or self.to_reference.references_table(table)

    def references_column(self, table, column):
        return (
            super().references_column(table, column) or
            self.to_reference.references_column(table, column)
        )

    def rename_table_references(self, old_table, new_table):
        super().rename_table_references(old_table, new_table)
        self.to_reference.rename_table_references(old_table, new_table)

    def rename_column_references(self, table, old_column, new_column):
        super().rename_column_references(table, old_column, new_column)
        self.to_reference.rename_column_references(table, old_column, new_column)

    def __str__(self):
        suffix = self.suffix_template % {
            'to_table': self.to_reference.table,
            'to_column': self.to_reference.columns[0],
        }
        return self.create_fk_name(self.table, self.columns, suffix)


class Statement(Reference):
    """
    Statement template and formatting parameters container.

    Allows keeping a reference to a statement without interpolating identifiers
    that might have to be adjusted if they're referencing a table or column
    that is removed
    """
    def __init__(self, template, **parts):
        self.template = template
        self.parts = parts

    def references_table(self, table):
        return any(
            hasattr(part, 'references_table') and part.references_table(table)
            for part in self.parts.values()
        )

    def references_column(self, table, column):
        return any(
            hasattr(part, 'references_column') and part.references_column(table, column)
            for part in self.parts.values()
        )

    def rename_table_references(self, old_table, new_table):
        for part in self.parts.values():
            if hasattr(part, 'rename_table_references'):
                part.rename_table_references(old_table, new_table)

    def rename_column_references(self, table, old_column, new_column):
        for part in self.parts.values():
            if hasattr(part, 'rename_column_references'):
                part.rename_column_references(table, old_column, new_column)

    def __str__(self):
        return self.template % self.parts
