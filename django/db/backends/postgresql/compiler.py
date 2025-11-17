from django.db.models.sql.compiler import (  # isort:skip
    SQLAggregateCompiler,
    SQLCompiler as BaseSQLCompiler,
    SQLDeleteCompiler,
    SQLInsertCompiler,
    SQLUpdateCompiler,
)

__all__ = [
    "SQLAggregateCompiler",
    "SQLCompiler",
    "SQLDeleteCompiler",
    "SQLInsertCompiler",
    "SQLUpdateCompiler",
]


class SQLCompiler(BaseSQLCompiler):
    def quote_name_unless_alias(self, name):
        if "$" in name:
            raise ValueError(
                "Dollar signs are not permitted in column aliases on PostgreSQL."
            )
        return super().quote_name_unless_alias(name)
