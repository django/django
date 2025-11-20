from django.db import NotSupportedError
from django.db.models.expressions import Func
from django.db.models.fields import UUIDField


class UUID4(Func):
    function = "UUIDV4"
    arity = 0
    output_field = UUIDField()

    def as_sql(self, compiler, connection, **extra_context):
        if connection.features.supports_uuid4_function:
            return super().as_sql(compiler, connection, **extra_context)
        raise NotSupportedError("UUID4 is not supported on this database backend.")

    def as_postgresql(self, compiler, connection, **extra_context):
        if connection.features.is_postgresql_18:
            return self.as_sql(compiler, connection, **extra_context)
        return self.as_sql(
            compiler, connection, function="GEN_RANDOM_UUID", **extra_context
        )

    def as_mysql(self, compiler, connection, **extra_context):
        if not connection.features.supports_uuid4_function:
            if connection.mysql_is_mariadb:
                raise NotSupportedError("UUID4 requires MariaDB version 11.7 or later.")
            raise NotSupportedError("UUID4 is not supported on MySQL.")
        return self.as_sql(compiler, connection, function="UUID_V4", **extra_context)

    def as_oracle(self, compiler, connection, **extra_context):
        if not connection.features.supports_uuid4_function:
            raise NotSupportedError(
                "UUID4 requires Oracle version 23ai/26ai (23.9) or later."
            )
        return self.as_sql(compiler, connection, function="UUID", **extra_context)


class UUID7(Func):
    function = "UUIDV7"
    arity = 1
    output_field = UUIDField()

    def __init__(self, shift=None, **extra):
        super().__init__(shift, **extra)

    def _parse_expressions(self, *expressions):
        if expressions[0] is None:
            expressions = expressions[1:]
        return super()._parse_expressions(*expressions)

    def as_sql(self, compiler, connection, **extra_context):
        if not connection.features.supports_uuid7_function:
            raise NotSupportedError("UUID7 is not supported on this database backend.")

        if len(self.source_expressions) == 1:
            if not connection.features.supports_uuid7_function_shift:
                msg = (
                    "The shift argument to UUID7 is not supported "
                    "on this database backend."
                )
                raise NotSupportedError(msg)

        return super().as_sql(compiler, connection, **extra_context)

    def as_postgresql(self, compiler, connection, **extra_context):
        if connection.features.supports_uuid7_function:
            return self.as_sql(compiler, connection, **extra_context)
        raise NotSupportedError("UUID7 requires PostgreSQL version 18 or later.")

    # PY314: When dropping support for 3.14, remove the entire method.
    def as_sqlite(self, compiler, connection, **extra_context):
        if connection.features.supports_uuid7_function:
            return self.as_sql(compiler, connection, **extra_context)
        raise NotSupportedError(
            "UUID7 on SQLite requires Python version 3.14 or later."
        )

    def as_mysql(self, compiler, connection, **extra_context):
        if connection.features.supports_uuid7_function:
            return self.as_sql(
                compiler, connection, function="UUID_V7", **extra_context
            )
        if connection.mysql_is_mariadb:
            raise NotSupportedError("UUID7 requires MariaDB version 11.7 or later.")
        raise NotSupportedError("UUID7 is not supported on MySQL.")
