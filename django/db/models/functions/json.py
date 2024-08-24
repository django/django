from django.db import NotSupportedError
from django.db.models.constants import LOOKUP_SEP
from django.db.models.expressions import Func, Value
from django.db.models.fields import TextField
from django.db.models.fields.json import JSONField, compile_json_path
from django.db.models.functions import Cast


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


class ToJSONB(Func):
    function = "TO_JSONB"


class JSONSet(Func):
    def __init__(self, expression, output_field=None, **fields):
        if not fields:
            raise TypeError("JSONSet requires at least one key-value pair to be set.")
        self.fields = fields
        super().__init__(expression, output_field=output_field)

    def _get_repr_options(self):
        return {**super().get_repr_options(), **self.fields}

    def resolve_expression(
        self, query=None, allow_joins=True, reuse=None, summarize=False, for_save=False
    ):
        c = super().resolve_expression(query, allow_joins, reuse, summarize, for_save)
        # Resolve expressions in the JSON update values.
        c.fields = {
            key: (
                value.resolve_expression(query, allow_joins, reuse, summarize, for_save)
                # If it's an expression, resolve it and use it as-is
                if hasattr(value, "resolve_expression")
                # Otherwise, use Value to serialize the data to string
                else Value(value, output_field=c.output_field)
            )
            for key, value in self.fields.items()
        }
        return c

    def join(self, args):
        key, value = list(self.fields.items())[0]
        key_paths = key.split(LOOKUP_SEP)
        key_paths_join = compile_json_path(key_paths)

        template = f"{args[0]}, SET q'\uffff{key_paths_join}\uffff' = {args[-1]}"

        if isinstance(value, Value):
            # Use the FORMAT JSON clause in JSON_TRANSFORM so the value is automatically
            # treated as JSON.
            return f"{template} FORMAT JSON"
        return template

    def as_sql(
        self,
        compiler,
        connection,
        function=None,
        template=None,
        arg_joiner=None,
        **extra_context,
    ):
        if not connection.features.supports_partial_json_update:
            raise NotSupportedError(
                "JSONSet() is not supported on this database backend."
            )
        copy = self.copy()
        new_source_expressions = copy.get_source_expressions()

        for key, value in self.fields.items():
            key_paths = key.split(LOOKUP_SEP)
            key_paths_join = compile_json_path(key_paths)
            new_source_expressions.append(Value(key_paths_join))

            # If it's a Value, assume it to be a JSON-formatted string.
            # Use Cast to ensure the string is treated as JSON on the database.
            if isinstance(value, Value):
                value = Cast(value, output_field=self.output_field)

            new_source_expressions.append(value)

        copy.set_source_expressions(new_source_expressions)

        return super(JSONSet, copy).as_sql(
            compiler,
            connection,
            function="JSON_SET",
            **extra_context,
        )

    def as_postgresql(self, compiler, connection, **extra_context):
        copy = self.copy()

        all_items = list(self.fields.items())
        key, value = all_items[0]
        rest = all_items[1:]

        # JSONB_SET does not support arbitrary number of arguments,
        # so convert multiple updates into recursive calls.
        if rest:
            copy.fields = {key: value}
            return JSONSet(copy, **dict(rest)).as_postgresql(
                compiler, connection, **extra_context
            )

        new_source_expressions = copy.get_source_expressions()

        key_paths = key.split(LOOKUP_SEP)
        new_source_expressions.append(Value(key_paths))

        if hasattr(value, "resolve_expression") and not isinstance(
            value.output_field, JSONField
        ):
            # Database expressions may return any type. We cannot use Cast() here
            # because ::jsonb only works with JSON-formatted strings, not with
            # other types like integers. The TO_JSONB function is available for
            # this purpose, i.e. to convert any SQL type to JSONB.
            value = ToJSONB(value, output_field=self.output_field)
        elif isinstance(value, Value) and value.value is None:
            # Avoid None from being interpreted as SQL NULL.
            value = Value(None, output_field=self.output_field)

        new_source_expressions.append(value)
        copy.set_source_expressions(new_source_expressions)
        return super(JSONSet, copy).as_sql(
            compiler, connection, function="JSONB_SET", **extra_context
        )

    def as_oracle(self, compiler, connection, **extra_context):
        if not connection.features.supports_partial_json_update:
            raise NotSupportedError(
                "JSONSet() is not supported on this database backend."
            )
        copy = self.copy()

        all_items = list(self.fields.items())
        key, value = all_items[0]
        rest = all_items[1:]

        # JSON_TRANSFORM does not support arbitrary number of arguments,
        # so convert multiple updates into recursive calls.
        if rest:
            copy.fields = {key: value}
            return JSONSet(copy, **dict(rest)).as_oracle(
                compiler, connection, **extra_context
            )

        new_source_expressions = copy.get_source_expressions()

        if isinstance(value, Value):
            # We do not need Cast() because we use the FORMAT JSON clause instead.
            value = Value(value, output_field=self.output_field)

        new_source_expressions.append(value)
        copy.set_source_expressions(new_source_expressions)

        return super(JSONSet, copy).as_sql(
            compiler,
            connection,
            function="JSON_TRANSFORM",
            arg_joiner=self,
            **extra_context,
        )


class JSONRemove(Func):
    def __init__(self, expression, *paths, **kwargs):
        if not paths:
            raise TypeError("JSONRemove requires at least one path to remove")
        self.paths = paths
        super().__init__(expression, **kwargs)

    def _get_repr_options(self):
        return {**super().get_repr_options(), **self.fields}

    def join(self, args):
        path = self.paths[0]
        key_paths = path.split(LOOKUP_SEP)
        key_paths_join = compile_json_path(key_paths)

        return f"{args[0]}, REMOVE q'\uffff{key_paths_join}\uffff'"

    def as_sql(
        self,
        compiler,
        connection,
        function=None,
        template=None,
        arg_joiner=None,
        **extra_context,
    ):
        if not connection.features.supports_partial_json_update:
            raise NotSupportedError(
                "JSONRemove() is not supported on this database backend."
            )

        copy = self.copy()
        new_source_expressions = copy.get_source_expressions()

        for path in self.paths:
            key_paths = path.split(LOOKUP_SEP)
            key_paths_join = compile_json_path(key_paths)
            new_source_expressions.append(Value(key_paths_join))

        copy.set_source_expressions(new_source_expressions)

        return super(JSONRemove, copy).as_sql(
            compiler,
            connection,
            function="JSON_REMOVE",
            **extra_context,
        )

    def as_postgresql(self, compiler, connection, **extra_context):
        copy = self.copy()
        path, *rest = self.paths

        if rest:
            copy.paths = (path,)
            return JSONRemove(copy, *rest).as_postgresql(
                compiler, connection, **extra_context
            )

        new_source_expressions = copy.get_source_expressions()
        key_paths = path.split(LOOKUP_SEP)
        new_source_expressions.append(Value(key_paths))
        copy.set_source_expressions(new_source_expressions)

        return super(JSONRemove, copy).as_sql(
            compiler,
            connection,
            template="%(expressions)s",
            arg_joiner="#- ",
            **extra_context,
        )

    def as_oracle(self, compiler, connection, **extra_context):
        if not connection.features.supports_partial_json_update:
            raise NotSupportedError(
                "JSONRemove() is not supported on this database backend."
            )

        copy = self.copy()

        all_items = self.paths
        path, *rest = all_items

        if rest:
            copy.paths = (path,)
            return JSONRemove(copy, *rest).as_oracle(
                compiler, connection, **extra_context
            )

        return super(JSONRemove, copy).as_sql(
            compiler,
            connection,
            function="JSON_TRANSFORM",
            arg_joiner=self,
            **extra_context,
        )
