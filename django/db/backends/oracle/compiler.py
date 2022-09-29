from django.db.models.sql import compiler


class SQLCompiler(compiler.SQLCompiler):
    pass


class SQLInsertCompiler(compiler.SQLInsertCompiler, SQLCompiler):
    pass


class SQLDeleteCompiler(compiler.SQLDeleteCompiler, SQLCompiler):
    pass


class SQLUpdateCompiler(compiler.SQLUpdateCompiler, SQLCompiler):
    pass


class SQLAggregateCompiler(compiler.SQLAggregateCompiler, SQLCompiler):
    pass


class SQLCheckCompiler(compiler.SQLCheckCompiler, SQLCompiler):
    # Oracle doesn't support boolean types yet PL/SQL does, meaning that although we
    # can't compare boolean expressions to NULL in SELECT or WHERE clauses we can in
    # a function which we can then call from a WHERE clause.
    check_sql = """\
WITH
  FUNCTION f RETURN NUMBER IS
    b BOOLEAN;
  BEGIN
    b := COALESCE(%s, TRUE);
    IF b THEN
        RETURN 1;
    ELSE
        RETURN 0;
    END IF;
  END f;
SELECT 1 FROM dual WHERE f = 1
"""

    def as_sql(self):
        # Avoid case wrapping.
        self.connection.vendor = "sqlite"
        condition, params = self.compile(self.query.where)
        self.connection.vendor = "oracle"

        # Oracle doesn't allow binding params within functions so bind manually
        # with quote_value().
        condition %= tuple(
            self.connection.schema_editor().quote_value(param) for param in params
        )
        check_sql = self.check_sql % condition
        return check_sql, []
