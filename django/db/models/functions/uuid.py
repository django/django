from django.db import NotSupportedError
from django.db.models.expressions import Func
from django.db.models.fields import UUIDField


class UUID4(Func):
    output_field = UUIDField()

    def as_sql(self, compiler, connection, **extra_context):
        raise NotSupportedError("UUID4 is not supported on this database backend.")

    def as_postgresql(self, compiler, connection, **extra_context):
        if connection.features.is_postgresql_18:
            function = "UUIDV4"
        else:
            function = "GEN_RANDOM_UUID"
        return super().as_sql(compiler, connection, function=function, **extra_context)

    def as_mysql(self, compiler, connection, **extra_context):
        if connection.features.supports_uuid4_function:
            return super().as_sql(
                compiler, connection, function="UUID_V4", **extra_context
            )
        if connection.mysql_is_mariadb:
            raise NotSupportedError("UUID4 requires MariaDB version 11.7 or later.")
        raise NotSupportedError("UUID4 is not supported on MySQL.")

    def as_oracle(self, compiler, connection, **extra_context):
        if connection.features.supports_uuid4_function:
            return super().as_sql(
                compiler, connection, function="UUID", **extra_context
            )
        raise NotSupportedError("UUID4 requires Oracle version 23ai or later.")


class UUID7(Func):
    output_field = UUIDField()

    def as_sql(self, compiler, connection, **extra_context):
        raise NotSupportedError("UUID7 is not supported on this database backend.")

    def as_postgresql(self, compiler, connection, **extra_context):
        if connection.features.supports_uuid7_function:
            return super().as_sql(
                compiler, connection, function="UUIDV7", **extra_context
            )
        raise NotSupportedError("UUID7 requires PostgreSQL version 18 or later.")

    def as_mysql(self, compiler, connection, **extra_context):
        if connection.features.supports_uuid7_function:
            return super().as_sql(
                compiler, connection, function="UUID_V7", **extra_context
            )
        if connection.mysql_is_mariadb:
            raise NotSupportedError("UUID7 requires MariaDB version 11.7 or later.")
        raise NotSupportedError("UUID7 is not supported on MySQL.")
