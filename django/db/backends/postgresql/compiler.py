from django.db.models.sql.compiler import (
    SQLAggregateCompiler,
    SQLCompiler as BaseSQLCompiler,
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


class SQLCompiler(BaseSQLCompiler):
    def quote_name_unless_alias(self, name):
        if "$" in name:
            raise ValueError(
                "Dollar signs are not permitted in column aliases on PostgreSQL."
            )
        return super().quote_name_unless_alias(name)


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
            # Field.get_placeholder takes value as an argument, so the
            # resulting placeholder might be dependent on the value.
            # in UNNEST requires a single placeholder to "fit all values" in
            # the array.
            or any(hasattr(field, "get_placeholder") for field in fields)
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
        # Manually remove parameters from `db_type` to ensure no data
        # truncation takes place (e.g. varchar[] instead of varchar(50)[]).
        db_types = [field.db_type(self.connection).split("(")[0] for field in fields]
        return InsertUnnest(["(%%s)::%s[]" % db_type for db_type in db_types]), [
            list(map(list, zip(*value_rows)))
        ]
