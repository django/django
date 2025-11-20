from django.db import NotSupportedError
from django.db.models.expressions import Func
from django.db.models.fields import UUIDField


class UUID4(Func):
    function = "UUIDV4"
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
            raise NotSupportedError("UUID4 requires Oracle version 23ai or later.")
        return self.as_sql(compiler, connection, function="UUID", **extra_context)


class UUID7(Func):
    function = "UUIDV7"
    output_field = UUIDField()

    def __init__(self, shift=None, **extra):
        self.shift = shift
        super().__init__(**extra)

    def as_sql(self, compiler, connection, **extra_context):
        if not connection.features.supports_uuid7_function:
            raise NotSupportedError("UUID7 is not supported on this database backend.")

        if self.shift is not None:
            if not connection.features.supports_uuid7_function_shift:
                msg = (
                    "The shift argument to UUID7 is not supported "
                    "on this database backend."
                )
                raise NotSupportedError(msg)
            self.source_expressions = self._parse_expressions(self.shift)

        return super().as_sql(compiler, connection, **extra_context)

    def as_postgresql(self, compiler, connection, **extra_context):
        if connection.features.supports_uuid7_function:
            return self.as_sql(compiler, connection, **extra_context)
        raise NotSupportedError("UUID7 requires PostgreSQL version 18 or later.")

    def as_sqlite(self, compiler, connection, **extra_context):
        if connection.features.supports_uuid7_function:
            return self.as_sql(compiler, connection, **extra_context)
        raise NotSupportedError(
            "UUID7 on sqlite requires Python version 3.14 or later."
        )

    def as_mysql(self, compiler, connection, **extra_context):
        if connection.features.supports_uuid7_function:
            return self.as_sql(
                compiler, connection, function="UUID_V7", **extra_context
            )
        if connection.mysql_is_mariadb:
            raise NotSupportedError("UUID7 requires MariaDB version 11.7 or later.")
        raise NotSupportedError("UUID7 is not supported on MySQL.")
