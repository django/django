from django.db.models.sql import compiler
from django.db.models.sql.constants import LOOKUP_SEP

class SQLCompiler(compiler.SQLCompiler):
    def resolve_columns(self, row, fields=()):
        values = []
        index_extra_select = len(self.query.extra_select.keys())
        for value, field in map(None, row[index_extra_select:], fields):
            if (field and field.get_internal_type() in ("BooleanField", "NullBooleanField") and
                value in (0, 1)):
                value = bool(value)
            values.append(value)
        return row[:index_extra_select] + tuple(values)

    def get_distinct(self):
        """MySQL DISTINCT for several fields.

        Implementation in MySQL:
        SELECT `field1`, `field2`, ..., `fieldN` FROM `table` GROUP BY `field1`, `field2`, ..., `fieldN` ORDER BY NULL;

        For a similar statement in PostgreSQL:
        SELECT DISTINCT ON(`field1`, `field2`, ..., `fieldN`) `field1`, `field2`, ..., `fieldN` FROM `table`;
        """

        qn = self.quote_name_unless_alias
        qn2 = self.connection.ops.quote_name
        result = []
        opts = self.query.model._meta

        self.query.group_by = self.query.group_by or []
        for name in self.query.distinct_fields:
            parts = name.split(LOOKUP_SEP)
            field, col, alias, _, _ = self._setup_joins(parts, opts, None)
            col, alias = self._final_join_removal(col, alias)
            self.query.group_by.append((qn(alias), qn2(col)))  # self.query.model._meta.db_table, field[0].column

        # Suppression: NotImplementedError("annotate() + distinct(fields) not implemented.")
        if self.query.distinct_fields:
            return []
        else:
            return None

class SQLInsertCompiler(compiler.SQLInsertCompiler, SQLCompiler):
    pass

class SQLDeleteCompiler(compiler.SQLDeleteCompiler, SQLCompiler):
    pass

class SQLUpdateCompiler(compiler.SQLUpdateCompiler, SQLCompiler):
    pass

class SQLAggregateCompiler(compiler.SQLAggregateCompiler, SQLCompiler):
    pass

class SQLDateCompiler(compiler.SQLDateCompiler, SQLCompiler):
    pass
