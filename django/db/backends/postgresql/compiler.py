from django.db.models.sql.compiler import (
    SQLAggregateCompiler,
    SQLCompiler,
    SQLDeleteCompiler,
)
from django.db.models.sql.compiler import SQLInsertCompiler as BaseSQLInsertCompiler
from django.db.models.sql.compiler import SQLUpdateCompiler

__all__ = [
    "SQLAggregateCompiler",
    "SQLCompiler",
    "SQLDeleteCompiler",
    "SQLInsertCompiler",
    "SQLUpdateCompiler",
]


class InsertUnnest(list):
    """
    Sentinel value to signal DatabaseOperations.bulk_insert_sql() that the
    UNNEST strategy should be used for the bulk insert.
    """

    def __str__(self):
        return "UNNEST(%s)" % ", ".join(self)


class SQLInsertCompiler(BaseSQLInsertCompiler):
    def assemble_as_sql(self, fields, value_rows):
        # Specialize bulk-insertion of literal values through UNNEST to
        # reduce the time spent planning the query.
        if (
            # The optimization is not worth doing if there is a single
            # row as it will result in the same number of placeholders.
            len(value_rows) <= 1
            # Lack of fields denote the usage of the DEFAULT keyword
            # for the insertion of empty rows.
            or any(field is None for field in fields)
            # Fields that don't use standard internal types might not be
            # unnest'able (e.g. array and geometry types are known to be
            # problematic).
            or any(
                (field.target_field if field.is_relation else field).get_internal_type()
                not in self.connection.data_types
                for field in fields
            )
            # Compilable cannot be combined in an array of literal values.
            or any(any(hasattr(value, "as_sql") for value in row) for row in value_rows)
        ):
            return super().assemble_as_sql(fields, value_rows)
        db_types = [field.db_type(self.connection) for field in fields]
        return InsertUnnest(["(%%s)::%s[]" % db_type for db_type in db_types]), [
            list(map(list, zip(*value_rows)))
        ]
