from itertools import groupby

from django.db.models.expressions import DatabaseDefault

from django.db.models.sql.compiler import (  # isort:skip
    SQLAggregateCompiler,
    SQLCompiler,
    SQLDeleteCompiler,
    SQLInsertCompiler as BaseSQLInsertCompiler,
    SQLUpdateCompiler,
)

__all__ = [
    "SQLAggregateCompiler",
    "SQLCompiler",
    "SQLDeleteCompiler",
    "SQLInsertCompiler",
    "SQLUpdateCompiler",
]


class SQLInsertCompiler(BaseSQLInsertCompiler):
    def _is_db_default(self, field, val):
        if isinstance(val, DatabaseDefault):
            return True
        if val is None and field.db_default is not None and not field.null:
            return True
        return False

    def pre_save_val(self, field, obj):
        val = super().pre_save_val(field, obj)
        if self._is_db_default(field, val):
            return None
        return val

    def as_sql(self):
        # SQLite lacks a DEFAULT keyword for INSERT statements. Columns with
        # a DatabaseDefault must be omitted from the column list to trigger
        # the internal database schema default.
        if self.query.objs:
            first_obj = self.query.objs[0]
            base_pre_save_val = super().pre_save_val
            static_fields = [
                field
                for field in self.query.fields
                if not self._is_db_default(field, base_pre_save_val(field, first_obj))
            ]

            original_fields = self.query.fields
            self.query.fields = static_fields
            try:
                return super().as_sql()
            finally:
                self.query.fields = original_fields

        return super().as_sql()

    def execute_sql(self, returning_fields=None):
        if len(self.query.objs) <= 1:
            return super().execute_sql(returning_fields)

        default_fields = [f for f in self.query.fields if f.db_default is not None]
        if not default_fields:
            return super().execute_sql(returning_fields)

        base_pre_save_val = super().pre_save_val

        def get_signature(obj):
            return tuple(
                self._is_db_default(f, base_pre_save_val(f, obj))
                for f in default_fields
            )

        batches = [
            list(group) for _, group in groupby(self.query.objs, key=get_signature)
        ]

        if len(batches) == 1:
            return super().execute_sql(returning_fields)

        # Partition into contiguous batches with identical signatures to
        # maximize bulk efficiency while preserving insertion order.
        results = []
        for batch_objs in batches:
            batch_query = self.query.chain()
            batch_query.objs = batch_objs

            res = batch_query.get_compiler(self.using).execute_sql(returning_fields)
            if returning_fields:
                results.extend(res)
            else:
                results.append(res)

        return results
