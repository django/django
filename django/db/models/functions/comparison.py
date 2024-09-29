"""Database functions that do comparisons or type conversions."""

import json
from django.db import NotSupportedError
from django.db.models.expressions import Func, Value, F, CombinedExpression, Expression
from django.db.models.fields import TextField
from django.db.models.fields.json import JSONField
from django.utils.regex_helper import _lazy_re_compile

from django.forms.fields import BooleanField, CharField, IntegerField, FloatField


class Cast(Func):
    """Coerce an expression to a new field type."""

    function = "CAST"
    template = "%(function)s(%(expressions)s AS %(db_type)s)"

    def __init__(self, expression, output_field):
        super().__init__(expression, output_field=output_field)

    def as_sql(self, compiler, connection, **extra_context):
        extra_context["db_type"] = self.output_field.cast_db_type(connection)
        return super().as_sql(compiler, connection, **extra_context)

    def as_sqlite(self, compiler, connection, **extra_context):
        db_type = self.output_field.db_type(connection)
        if db_type in {"datetime", "time"}:
            # Use strftime as datetime/time don't keep fractional seconds.
            template = "strftime(%%s, %(expressions)s)"
            sql, params = super().as_sql(
                compiler, connection, template=template, **extra_context
            )
            format_string = "%H:%M:%f" if db_type == "time" else "%Y-%m-%d %H:%M:%f"
            params.insert(0, format_string)
            return sql, params
        elif db_type == "date":
            template = "date(%(expressions)s)"
            return super().as_sql(
                compiler, connection, template=template, **extra_context
            )
        return self.as_sql(compiler, connection, **extra_context)

    def as_mysql(self, compiler, connection, **extra_context):
        template = None
        output_type = self.output_field.get_internal_type()
        # MySQL doesn't support explicit cast to float.
        if output_type == "FloatField":
            template = "(%(expressions)s + 0.0)"
        # MariaDB doesn't support explicit cast to JSON.
        elif output_type == "JSONField" and connection.mysql_is_mariadb:
            template = "JSON_EXTRACT(%(expressions)s, '$')"
        return self.as_sql(compiler, connection, template=template, **extra_context)

    def as_postgresql(self, compiler, connection, **extra_context):
        # CAST would be valid too, but the :: shortcut syntax is more readable.
        # 'expressions' is wrapped in parentheses in case it's a complex
        # expression.
        return self.as_sql(
            compiler,
            connection,
            template="(%(expressions)s)::%(db_type)s",
            **extra_context,
        )

    def as_oracle(self, compiler, connection, **extra_context):
        if self.output_field.get_internal_type() == "JSONField":
            # Oracle doesn't support explicit cast to JSON.
            template = "JSON_QUERY(%(expressions)s, '$')"
            return super().as_sql(
                compiler, connection, template=template, **extra_context
            )
        return self.as_sql(compiler, connection, **extra_context)


class Coalesce(Func):
    """Return, from left to right, the first non-null expression."""

    function = "COALESCE"

    def __init__(self, *expressions, **extra):
        if len(expressions) < 2:
            raise ValueError("Coalesce must take at least two expressions")
        super().__init__(*expressions, **extra)

    @property
    def empty_result_set_value(self):
        for expression in self.get_source_expressions():
            result = expression.empty_result_set_value
            if result is NotImplemented or result is not None:
                return result
        return None

    def as_oracle(self, compiler, connection, **extra_context):
        # Oracle prohibits mixing TextField (NCLOB) and CharField (NVARCHAR2),
        # so convert all fields to NCLOB when that type is expected.
        if self.output_field.get_internal_type() == "TextField":
            clone = self.copy()
            clone.set_source_expressions(
                [
                    Func(expression, function="TO_NCLOB")
                    for expression in self.get_source_expressions()
                ]
            )
            return super(Coalesce, clone).as_sql(compiler, connection, **extra_context)
        return self.as_sql(compiler, connection, **extra_context)


class Collate(Func):
    function = "COLLATE"
    template = "%(expressions)s %(function)s %(collation)s"
    allowed_default = False
    # Inspired from
    # https://www.postgresql.org/docs/current/sql-syntax-lexical.html#SQL-SYNTAX-IDENTIFIERS
    collation_re = _lazy_re_compile(r"^[\w-]+$")

    def __init__(self, expression, collation):
        if not (collation and self.collation_re.match(collation)):
            raise ValueError("Invalid collation name: %r." % collation)
        self.collation = collation
        super().__init__(expression)

    def as_sql(self, compiler, connection, **extra_context):
        extra_context.setdefault("collation", connection.ops.quote_name(self.collation))
        return super().as_sql(compiler, connection, **extra_context)


class Greatest(Func):
    """
    Return the maximum expression.

    If any expression is null the return value is database-specific:
    On PostgreSQL, the maximum not-null expression is returned.
    On MySQL, Oracle, and SQLite, if any expression is null, null is returned.
    """

    function = "GREATEST"

    def __init__(self, *expressions, **extra):
        if len(expressions) < 2:
            raise ValueError("Greatest must take at least two expressions")
        super().__init__(*expressions, **extra)

    def as_sqlite(self, compiler, connection, **extra_context):
        """Use the MAX function on SQLite."""
        return super().as_sqlite(compiler, connection, function="MAX", **extra_context)


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

    def as_native(self, compiler, connection, *, returning, **extra_context):
        class ArgJoiner:
            def join(self, args):
                pairs = zip(args[::2], args[1::2], strict=True)
                return ", ".join([" VALUE ".join(pair) for pair in pairs])

        return self.as_sql(
            compiler,
            connection,
            arg_joiner=ArgJoiner(),
            template=f"%(function)s(%(expressions)s RETURNING {returning})",
            **extra_context,
        )

    def as_postgresql(self, compiler, connection, **extra_context):
        if (
            not connection.features.is_postgresql_16
            or connection.features.uses_server_side_binding
        ):
            copy = self.copy()
            copy.set_source_expressions(
                [
                    Cast(expression, TextField()) if index % 2 == 0 else expression
                    for index, expression in enumerate(copy.get_source_expressions())
                ]
            )
            return super(JSONObject, copy).as_sql(
                compiler,
                connection,
                function="JSONB_BUILD_OBJECT",
                **extra_context,
            )
        return self.as_native(compiler, connection, returning="JSONB", **extra_context)

    def as_oracle(self, compiler, connection, **extra_context):
        return self.as_native(compiler, connection, returning="CLOB", **extra_context)


class JSONSet(Func):
    function = "JSON_SET"
    lookup_name = "set"
    output_field = JSONField()

    def __init__(self, **updates):
        if not updates:
            raise ValueError("JSONSet requires at least one update.")
        self.updates = updates
        super().__init__()

    def resolve_expression(self, query=None, allow_joins=True, reuse=None, summarize=False, for_save=False):
        # This method is called during query compilation
        if self.source_expressions:
            return super().resolve_expression(query, allow_joins, reuse, summarize, for_save)

        # Find the JSON field in the model
        model = query.model
        json_fields = [f for f in model._meta.fields if isinstance(f, JSONField)]
        if len(json_fields) != 1:
            raise ValueError(f"Expected exactly one JSONField in {model.__name__}, found {len(json_fields)}")
        
        field = json_fields[0]
        self.source_expressions = [F(field.name)]
        for key, value in self.updates.items():
            self.source_expressions.extend([Value(key), value])

        return super().resolve_expression(query, allow_joins, reuse, summarize, for_save)

    def _build_postgres_path(self, key):
        return '{' + ','.join(f'"{part}"' for part in key.split('__')) + '}'

    def _build_mysql_path(self, key):
        return '$.' + '.'.join(f'"{part}"' for part in key.split('__'))

    def _build_sqlite_path(self, key):
        parts = key.split('__')
        path = '$'
        for part in parts:
            if part.isdigit():
                path += f'[{part}]'
            elif part == '#':
                path += '[#]'
            else:
                path += f'."{part}"'
        return path

    def as_sqlite(self, compiler, connection, **extra_context):
        lhs, params = compiler.compile(self.source_expressions[0])
        for i in range(1, len(self.source_expressions), 2):
            key, value = self.source_expressions[i:i+2]
            key_sql, key_params = compiler.compile(key)
            key_params = [self._build_sqlite_path(x) for x in key_params]
            value_sql, value_params = compiler.compile(value)
            lhs = f"JSON_SET({lhs}, {key_sql}, {value_sql})"
            params.extend(key_params)
            params.extend(value_params)
        return lhs, params

    def as_postgresql(self, compiler, connection, **extra_context):
        lhs, params = compiler.compile(self.source_expressions[0])
        for i in range(1, len(self.source_expressions), 2):
            key, value = self.source_expressions[i:i+2]
            key_sql, key_params = compiler.compile(key)
            value_sql, value_params = compiler.compile(value)
            path = self._build_postgres_path(key_params[0])
            value_sql = f"to_jsonb({value_sql})"
            lhs = f"jsonb_set(({lhs})::jsonb, '{path}'::text[], {value_sql}, true)"
            params.extend(value_params)
        return lhs, params

    def as_mysql(self, compiler, connection, **extra_context):
        lhs, params = compiler.compile(self.source_expressions[0])
        for i in range(1, len(self.source_expressions), 2):
            key, value = self.source_expressions[i:i+2]
            key_sql, key_params = compiler.compile(key)
            key_params = [self._build_sqlite_path(x) for x in key_params]
            value_sql, value_params = compiler.compile(value)
            lhs = f"JSON_SET({lhs}, {key_sql}, {value_sql})"
            params.extend(key_params)
            params.extend(value_params)
        return lhs, params

    def as_sql(self, compiler, connection, **extra_context):
        vendor = connection.vendor
        if vendor == 'sqlite':
            return self.as_sqlite(compiler, connection, **extra_context)
        elif vendor in ['mysql', 'maria']:
            return self.as_mysql(compiler, connection, **extra_context)
        elif vendor == 'postgresql':
            return self.as_postgresql(compiler, connection, **extra_context)
        else:
            # Implement Oracle specific logic here if needed
            raise NotImplementedError(f"JSONSet for {vendor} is not implemented yet.")


class JSONExtract(Func):
    function = 'JSON_EXTRACT'

    def as_postgresql(self, compiler, connection):
        lhs, lhs_params = compiler.compile(self.source_expressions[0])
        paths = []
        for expr in self.source_expressions[1:]:
            _, path_params = compiler.compile(expr)
            path = path_params[0].strip('"').replace('.', ',')
            paths.append('{' + path + '}')
        
        if len(paths) == 1:
            return f"({lhs} #>> %s)", lhs_params + paths
        else:
            path_placeholders = ['%s'] * len(paths)
            placeholders = []
            for placeholder in path_placeholders:
                sub_selection = f'({lhs} #>> {placeholder})'
                placeholders.append(sub_selection)
            array_select = ', '.join(placeholders)
            return f"ARRAY[{array_select}]", lhs_params + paths

    def as_sqlite(self, compiler, connection, **extra_context):
        lhs, lhs_params = compiler.compile(self.source_expressions[0])
        paths = []
        for expr in self.source_expressions[1:]:
            _, path_params = compiler.compile(expr)
            path = f'$.{path_params[0]}' if isinstance(path_params[0], str) else f'$[{path_params[0]}]'
            paths.append(path)
        
        if len(paths) == 1:
            return f"{self.function}({lhs}, %s)", lhs_params + paths
        else:
            path_extractions = ', '.join([f"{self.function}({lhs}, %s)" for _ in paths])
            return f"json_array({path_extractions})", lhs_params + paths

    def as_mysql(self, compiler, connection, **extra_context):
        lhs, lhs_params = compiler.compile(self.source_expressions[0])
        paths = []
        for expr in self.source_expressions[1:]:
            _, path_params = compiler.compile(expr)
            path = f'$.{path_params[0]}' if isinstance(path_params[0], str) else f'$[{path_params[0]}]'
            paths.append(path)
        
        if len(paths) == 1:
            return f"JSON_UNQUOTE({self.function}({lhs}, %s))", lhs_params + paths
        else:
            path_extractions = ', '.join([f"JSON_UNQUOTE({self.function}({lhs}, %s))" for _ in paths])
            return f"JSON_ARRAY({path_extractions})", lhs_params + paths

class JSONRemove(Func):
    function = "JSON_REMOVE"
    output_field = JSONField()
    lookup_name = "remove"

    def __init__(self, *updates):
        if not updates:
            raise ValueError("JSONSet requires at least one update.")
        self.updates = updates
        super().__init__()

    def resolve_expression(self, query=None, allow_joins=True, reuse=None, summarize=False, for_save=False):
        # This method is called during query compilation
        if self.source_expressions:
            return super().resolve_expression(query, allow_joins, reuse, summarize, for_save)

        # Find the JSON field in the model
        model = query.model
        json_fields = [f for f in model._meta.fields if isinstance(f, JSONField)]
        if len(json_fields) != 1:
            raise ValueError(f"Expected exactly one JSONField in {model.__name__}, found {len(json_fields)}")
        
        field = json_fields[0]
        self.source_expressions = [F(field.name)]
        for path in self.updates:
            self.source_expressions.extend([Value(path)])

        return super().resolve_expression(query, allow_joins, reuse, summarize, for_save)

    def _build_sqlite_path(self, key):
        return f'$.{key}'

    def _build_postgres_path(self, path):
        return '{' + ','.join(f'"{part}"' for part in path.split('.')) + '}'

    def as_sqlite(self, compiler, connection, **extra_context):
        lhs, params = compiler.compile(self.source_expressions[0])
        path_params = [self._build_sqlite_path(path) for path in self.updates]
        placeholders = ', '.join(['%s'] * len(path_params))
        sql = f"JSON_REMOVE({lhs}, {placeholders})"
        return sql, params + path_params

    def as_postgresql(self, compiler, connection, **extra_context):
        lhs, params = compiler.compile(self.source_expressions[0])
        for path in self.updates:
            postgres_path = self._build_postgres_path(path)
            lhs = f"({lhs})::jsonb #- %s"
            params.append(postgres_path)
        return lhs, params

    def as_mysql(self, compiler, connection, **extra_context):
        lhs, params = compiler.compile(self.source_expressions[0])
        path_params = [self._build_sqlite_path(path) for path in self.updates]
        placeholders = ', '.join(['%s'] * len(path_params))
        sql = f"JSON_REMOVE({lhs}, {placeholders})"
        return sql, params + path_params

    def as_sql(self, compiler, connection, **extra_context):
        vendor = connection.vendor
        if vendor == 'sqlite':
            return self.as_sqlite(compiler, connection, **extra_context)
        elif vendor in ['mysql', 'mariadb']:
            return self.as_mysql(compiler, connection, **extra_context)
        elif vendor == 'postgresql':
            return self.as_postgresql(compiler, connection, **extra_context)
        else:
            raise NotImplementedError(f"JSONRemove is not supported for {vendor}.")

class Least(Func):
    """
    Return the minimum expression.

    If any expression is null the return value is database-specific:
    On PostgreSQL, return the minimum not-null expression.
    On MySQL, Oracle, and SQLite, if any expression is null, return null.
    """

    function = "LEAST"

    def __init__(self, *expressions, **extra):
        if len(expressions) < 2:
            raise ValueError("Least must take at least two expressions")
        super().__init__(*expressions, **extra)

    def as_sqlite(self, compiler, connection, **extra_context):
        """Use the MIN function on SQLite."""
        return super().as_sqlite(compiler, connection, function="MIN", **extra_context)


class NullIf(Func):
    function = "NULLIF"
    arity = 2

    def as_oracle(self, compiler, connection, **extra_context):
        expression1 = self.get_source_expressions()[0]
        if isinstance(expression1, Value) and expression1.value is None:
            raise ValueError("Oracle does not allow Value(None) for expression1.")
        return super().as_sql(compiler, connection, **extra_context)


JSONField.register_lookup(JSONSet)
JSONField.register_lookup(JSONRemove)
