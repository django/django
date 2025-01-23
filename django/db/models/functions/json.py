from django.db import NotSupportedError
from django.db.models.expressions import Func, Value
from django.db.models.fields import TextField
from django.db.models.fields.json import JSONField
from django.db.models.functions import Cast


class JSONArray(Func):
    function = "JSON_ARRAY"
    output_field = JSONField()

    def as_sql(self, compiler, connection, **extra_context):
        if not connection.features.supports_json_field:
            raise NotSupportedError(
                "JSONFields are not supported on this database backend."
            )
        return super().as_sql(compiler, connection, **extra_context)

    def as_native(self, compiler, connection, *, returning, **extra_context):
        # PostgreSQL 16+ and Oracle remove SQL NULL values from the array by
        # default. Adds the NULL ON NULL clause to keep NULL values in the
        # array, mapping them to JSON null values, which matches the behavior
        # of SQLite.
        null_on_null = "NULL ON NULL" if len(self.get_source_expressions()) > 0 else ""

        return self.as_sql(
            compiler,
            connection,
            template=(
                f"%(function)s(%(expressions)s {null_on_null} RETURNING {returning})"
            ),
            **extra_context,
        )

    def as_postgresql(self, compiler, connection, **extra_context):
        # Casting source expressions is only required using JSONB_BUILD_ARRAY
        # or when using JSON_ARRAY on PostgreSQL 16+ with server-side bindings.
        # This is done in all cases for consistency.
        casted_obj = self.copy()
        casted_obj.set_source_expressions(
            [
                (
                    # Conditional Cast to avoid unnecessary wrapping.
                    expression
                    if isinstance(expression, Cast)
                    else Cast(expression, expression.output_field)
                )
                for expression in casted_obj.get_source_expressions()
            ]
        )

        if connection.features.is_postgresql_16:
            return casted_obj.as_native(
                compiler, connection, returning="JSONB", **extra_context
            )

        return casted_obj.as_sql(
            compiler,
            connection,
            function="JSONB_BUILD_ARRAY",
            **extra_context,
        )

    def as_oracle(self, compiler, connection, **extra_context):
        return self.as_native(compiler, connection, returning="CLOB", **extra_context)


class JSONObject(Func):
    function = "JSON_OBJECT"
    output_field = JSONField()

    def __init__(self, **fields):
        expressions = []
        for key, value in fields.items():
            expressions.extend((Value(key), value))
        super().__init__(*expressions)

    def as_sql(self, compiler, connection, **extra_context):
        if not connection.features.has_json_object_function:
            raise NotSupportedError(
                "JSONObject() is not supported on this database backend."
            )
        return super().as_sql(compiler, connection, **extra_context)

    def join(self, args):
        pairs = zip(args[::2], args[1::2], strict=True)
        # Wrap 'key' in parentheses in case of postgres cast :: syntax.
        return ", ".join([f"({key}) VALUE {value}" for key, value in pairs])

    def as_native(self, compiler, connection, *, returning, **extra_context):
        return self.as_sql(
            compiler,
            connection,
            arg_joiner=self,
            template=f"%(function)s(%(expressions)s RETURNING {returning})",
            **extra_context,
        )

    def as_postgresql(self, compiler, connection, **extra_context):
        # Casting keys to text is only required when using JSONB_BUILD_OBJECT
        # or when using JSON_OBJECT on PostgreSQL 16+ with server-side bindings.
        # This is done in all cases for consistency.
        copy = self.copy()
        copy.set_source_expressions(
            [
                Cast(expression, TextField()) if index % 2 == 0 else expression
                for index, expression in enumerate(copy.get_source_expressions())
            ]
        )

        if connection.features.is_postgresql_16:
            return copy.as_native(
                compiler, connection, returning="JSONB", **extra_context
            )

        return super(JSONObject, copy).as_sql(
            compiler,
            connection,
            function="JSONB_BUILD_OBJECT",
            **extra_context,
        )

    def as_oracle(self, compiler, connection, **extra_context):
        return self.as_native(compiler, connection, returning="CLOB", **extra_context)
