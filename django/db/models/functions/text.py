import re

from django.db import NotSupportedError
from django.db.models.expressions import Func, Value
from django.db.models.fields import BooleanField, CharField, IntegerField, TextField
from django.db.models.functions import Cast, Coalesce
from django.db.models.lookups import Transform


class MySQLSHA2Mixin:
    def as_mysql(self, compiler, connection, **extra_context):
        return super().as_sql(
            compiler,
            connection,
            template="SHA2(%%(expressions)s, %s)" % self.function[3:],
            **extra_context,
        )


class OracleHashMixin:
    def as_oracle(self, compiler, connection, **extra_context):
        return super().as_sql(
            compiler,
            connection,
            template=(
                "LOWER(RAWTOHEX(STANDARD_HASH(UTL_I18N.STRING_TO_RAW("
                "%(expressions)s, 'AL32UTF8'), '%(function)s')))"
            ),
            **extra_context,
        )


class PostgreSQLSHAMixin:
    def as_postgresql(self, compiler, connection, **extra_context):
        return super().as_sql(
            compiler,
            connection,
            template="ENCODE(DIGEST(%(expressions)s, '%(function)s'), 'hex')",
            function=self.function.lower(),
            **extra_context,
        )


class Chr(Transform):
    function = "CHR"
    lookup_name = "chr"
    output_field = CharField()

    def as_mysql(self, compiler, connection, **extra_context):
        return super().as_sql(
            compiler,
            connection,
            function="CHAR",
            template="%(function)s(%(expressions)s USING utf16)",
            **extra_context,
        )

    def as_oracle(self, compiler, connection, **extra_context):
        return super().as_sql(
            compiler,
            connection,
            template="%(function)s(%(expressions)s USING NCHAR_CS)",
            **extra_context,
        )

    def as_sqlite(self, compiler, connection, **extra_context):
        return super().as_sql(compiler, connection, function="CHAR", **extra_context)


class ConcatPair(Func):
    """
    Concatenate two arguments together. This is used by `Concat` because not
    all backend databases support more than two arguments.
    """

    function = "CONCAT"

    def as_sqlite(self, compiler, connection, **extra_context):
        coalesced = self.coalesce()
        return super(ConcatPair, coalesced).as_sql(
            compiler,
            connection,
            template="%(expressions)s",
            arg_joiner=" || ",
            **extra_context,
        )

    def as_postgresql(self, compiler, connection, **extra_context):
        copy = self.copy()
        copy.set_source_expressions(
            [
                Cast(expression, TextField())
                for expression in copy.get_source_expressions()
            ]
        )
        return super(ConcatPair, copy).as_sql(
            compiler,
            connection,
            **extra_context,
        )

    def as_mysql(self, compiler, connection, **extra_context):
        # Use CONCAT_WS with an empty separator so that NULLs are ignored.
        return super().as_sql(
            compiler,
            connection,
            function="CONCAT_WS",
            template="%(function)s('', %(expressions)s)",
            **extra_context,
        )

    def coalesce(self):
        # null on either side results in null for expression, wrap with coalesce
        c = self.copy()
        c.set_source_expressions(
            [
                Coalesce(expression, Value(""))
                for expression in c.get_source_expressions()
            ]
        )
        return c


class Concat(Func):
    """
    Concatenate text fields together. Backends that result in an entire
    null expression when any arguments are null will wrap each argument in
    coalesce functions to ensure a non-null result.
    """

    function = None
    template = "%(expressions)s"

    def __init__(self, *expressions, **extra):
        if len(expressions) < 2:
            raise ValueError("Concat must take at least two expressions")
        paired = self._paired(expressions)
        super().__init__(paired, **extra)

    def _paired(self, expressions):
        # wrap pairs of expressions in successive concat functions
        # exp = [a, b, c, d]
        # -> ConcatPair(a, ConcatPair(b, ConcatPair(c, d))))
        if len(expressions) == 2:
            return ConcatPair(*expressions)
        return ConcatPair(expressions[0], self._paired(expressions[1:]))


class Left(Func):
    function = "LEFT"
    arity = 2
    output_field = CharField()

    def __init__(self, expression, length, **extra):
        """
        expression: the name of a field, or an expression returning a string
        length: the number of characters to return from the start of the string
        """
        if not hasattr(length, "resolve_expression"):
            if length < 1:
                raise ValueError("'length' must be greater than 0.")
        super().__init__(expression, length, **extra)

    def get_substr(self):
        return Substr(self.source_expressions[0], Value(1), self.source_expressions[1])

    def as_oracle(self, compiler, connection, **extra_context):
        return self.get_substr().as_oracle(compiler, connection, **extra_context)

    def as_sqlite(self, compiler, connection, **extra_context):
        return self.get_substr().as_sqlite(compiler, connection, **extra_context)


class Length(Transform):
    """Return the number of characters in the expression."""

    function = "LENGTH"
    lookup_name = "length"
    output_field = IntegerField()

    def as_mysql(self, compiler, connection, **extra_context):
        return super().as_sql(
            compiler, connection, function="CHAR_LENGTH", **extra_context
        )


class Lower(Transform):
    function = "LOWER"
    lookup_name = "lower"


class LPad(Func):
    function = "LPAD"
    output_field = CharField()

    def __init__(self, expression, length, fill_text=Value(" "), **extra):
        if (
            not hasattr(length, "resolve_expression")
            and length is not None
            and length < 0
        ):
            raise ValueError("'length' must be greater or equal to 0.")
        super().__init__(expression, length, fill_text, **extra)


class LTrim(Transform):
    function = "LTRIM"
    lookup_name = "ltrim"


class MD5(OracleHashMixin, Transform):
    function = "MD5"
    lookup_name = "md5"


class Ord(Transform):
    function = "ASCII"
    lookup_name = "ord"
    output_field = IntegerField()

    def as_mysql(self, compiler, connection, **extra_context):
        return super().as_sql(compiler, connection, function="ORD", **extra_context)

    def as_sqlite(self, compiler, connection, **extra_context):
        return super().as_sql(compiler, connection, function="UNICODE", **extra_context)


class RegexpMixin:
    def as_sql(self, compiler, connection, **extra_context):
        clone = self.copy()
        expressions = clone.get_source_expressions()

        # Remove arguments that are unsupported by the database backend.
        if s := extra_context.get("skip_arguments"):
            expressions[s] = []

        expression, pattern, *other, flags = expressions

        # Modify the provided flags, performing the following actions:
        # - Prepend default flags used to make backends consistent
        # - Remove duplicate flags preserving the latest occurrence of each
        # - Resolve case-sensitivity flags preferring the latest specified
        # - Map flags from normalized values to backend-specific values
        flags.value = connection.features.regexp_functions_flags_default + flags.value
        flags.value = "".join(reversed(dict.fromkeys(reversed(flags.value))))
        if (index := min(flags.value.find("c"), flags.value.find("i"))) > -1:
            flags.value = flags.value.replace(flags.value[index], "", 1)
        mapping = connection.features.regexp_functions_flags_mapping
        flags.value = flags.value.translate(str.maketrans(mapping))

        if not extra_context.get(
            "force_flags_inline", connection.features.regexp_functions_flags_inline
        ):
            other.append(flags)
        elif pattern.value is not None:
            # Force flags inline in the pattern instead of as an argument.
            # Also convert flags that must be specified in negated form.
            if mapping := connection.features.regexp_functions_flags_inline_negated:
                for old, new in mapping.items():
                    if old in flags.value:
                        flags.value = flags.value.replace(old, "")
                        pattern.value = f"(?-{new}){pattern.value}"
            pattern.value = f"(?{flags.value}){pattern.value}"

        clone.set_source_expressions([expression, pattern, *other])
        return super(RegexpMixin, clone).as_sql(compiler, connection, **extra_context)


class RegexpCount(RegexpMixin, Func):
    function = "REGEXP_COUNT"
    output_field = IntegerField()

    def __init__(
        self,
        expression,
        pattern,
        position=1,
        flags=Value(""),
        **extra,
    ):
        if not hasattr(position, "resolve_expression") and position < 1:
            raise ValueError("'position' must be greater than 0.")
        super().__init__(expression, pattern, position, flags, **extra)

    def get_polyfill(self, *, supports_position=False):
        # Replaces matching patterns with a single unlikely character which can
        # then be replaced with the empty string so that length comparison will
        # give the number of matches. If the position argument to RegexpReplace
        # is unsupported then a Substr can be performed first.
        expression, pattern, position, flags = self.get_source_expressions()
        placeholder = Value("\uffff")
        if not supports_position and position.value > 1:
            expression = Substr(expression, position)
        expr = RegexpReplace(expression, pattern, placeholder, position, 0, flags=flags)
        return Length(expr) - Length(Replace(expr, placeholder))

    def as_mysql(self, compiler, connection, **extra_context):
        # MySQL supports the position argument for REGEXP_REPLACE.
        supports_position = not connection.mysql_is_mariadb
        polyfill = self.get_polyfill(supports_position=supports_position)
        return polyfill.as_sql(compiler, connection, **extra_context)

    def as_postgresql(self, compiler, connection, **extra_context):
        if not connection.features.is_postgresql_15:
            return self.get_polyfill().as_sql(compiler, connection, **extra_context)
        return super().as_sql(compiler, connection, **extra_context)


class RegexpLike(RegexpMixin, Func):
    function = "REGEXP_LIKE"
    output_field = BooleanField()

    def __init__(
        self,
        expression,
        pattern,
        flags=Value(""),
        **extra,
    ):
        super().__init__(expression, pattern, flags, **extra)

    def as_mysql(self, compiler, connection, **extra_context):
        if connection.mysql_is_mariadb:
            return super().as_sql(
                compiler,
                connection,
                template="%(expressions)s",
                arg_joiner=" REGEXP ",
                **extra_context,
            )
        return super().as_sql(compiler, connection, **extra_context)

    def as_postgresql(self, compiler, connection, **extra_context):
        if not connection.features.is_postgresql_15:
            return super().as_sql(
                compiler,
                connection,
                template="%(expressions)s",
                arg_joiner=" ~ ",
                **extra_context | {"force_flags_inline": True},
            )
        return super().as_sql(compiler, connection, **extra_context)


class RegexpReplace(RegexpMixin, Func):
    function = "REGEXP_REPLACE"
    output_field = CharField()

    def __init__(
        self,
        expression,
        pattern,
        replacement=Value(""),
        position=1,
        occurrence=1,
        flags=Value(""),
        **extra,
    ):
        if not hasattr(position, "resolve_expression") and position < 1:
            raise ValueError("'position' must be greater than 0.")
        if not hasattr(occurrence, "resolve_expression") and occurrence < 0:
            raise ValueError("'occurrence' must be greater than or equal to 0.")
        super().__init__(
            expression, pattern, replacement, position, occurrence, flags, **extra
        )

    def as_mysql(self, compiler, connection, **extra_context):
        if connection.mysql_is_mariadb:
            # MariaDB does not support position or occurrence.
            extra_context["skip_arguments"] = slice(3, 5)
            # TODO: Default to replacing all occurrences for compatibility:
            # # MariaDB only supports replacing all occurrences.
            # expressions = self.get_source_expressions()
            # if expressions[4].value != 0:
            #     raise NotSupportedError(
            #         "MariaDB only supports replacing all occurrences."
            #     )
        return super().as_sql(compiler, connection, **extra_context)

    def as_postgresql(self, compiler, connection, **extra_context):
        if not connection.features.is_postgresql_15:
            # PostgreSQL < 15 does not support position or occurrence.
            extra_context["skip_arguments"] = slice(3, 5)
            # PostgreSQL < 15 uses the `g` flag to replace all occurrences.
            clone = self.copy()
            expressions = clone.get_source_expressions()
            if expressions[4].value == 0:
                expressions[5].value += "g"
            clone.set_source_expressions(expressions)
            return clone.as_sql(compiler, connection, **extra_context)
        return super().as_sql(compiler, connection, **extra_context)


class RegexpStrIndex(RegexpMixin, Func):
    function = "REGEXP_INSTR"
    output_field = IntegerField()

    def __init__(
        self,
        expression,
        pattern,
        position=1,
        occurrence=1,
        return_option=0,
        flags=Value(""),
        **extra,
    ):
        if not hasattr(position, "resolve_expression") and position < 1:
            raise ValueError("'position' must be greater than 0.")
        if not hasattr(occurrence, "resolve_expression") and occurrence < 1:
            raise ValueError("'occurrence' must be greater than 0.")
        if not hasattr(return_option, "resolve_expression") and return_option not in (
            0,
            1,
        ):
            raise ValueError("'return_option' must be 0 or 1.")
        super().__init__(
            expression, pattern, position, occurrence, return_option, flags, **extra
        )

    def as_mysql(self, compiler, connection, **extra_context):
        if connection.mysql_is_mariadb:
            # MariaDB does not support position, occurrence or, return_option.
            extra_context["skip_arguments"] = slice(2, 5)
        return super().as_sql(compiler, connection, **extra_context)

    def as_postgresql(self, compiler, connection, **extra_context):
        if not connection.features.is_postgresql_15:
            # This emulated version doesn't handle NULL pattern correctly.
            expression, pattern, *other, flags = self.get_source_expressions()
            expr = RegexpSubstr(expression, pattern, flags=flags, no_wrap=True)
            expr = StrIndex(expression, Coalesce(expr, Value("<<fail>>")))
            return expr.as_postgresql(compiler, connection, **extra_context)
        return super().as_sql(compiler, connection, **extra_context)


class RegexpSubstr(RegexpMixin, Func):
    function = "REGEXP_SUBSTR"
    output_field = CharField()

    def __init__(
        self,
        expression,
        pattern,
        position=1,
        occurrence=1,
        flags=Value(""),
        **extra,
    ):
        if not hasattr(position, "resolve_expression") and position < 1:
            raise ValueError("'position' must be greater than 0.")
        if not hasattr(occurrence, "resolve_expression") and occurrence < 1:
            raise ValueError("'occurrence' must be greater than 0.")
        super().__init__(expression, pattern, position, occurrence, flags, **extra)

    def as_mysql(self, compiler, connection, **extra_context):
        if connection.mysql_is_mariadb:
            # MariaDB does not support position or occurrence.
            extra_context["skip_arguments"] = slice(2, 4)
        return super().as_sql(compiler, connection, **extra_context)

    def as_postgresql(self, compiler, connection, **extra_context):
        if not connection.features.is_postgresql_15:
            clone = self.copy()
            expression, pattern, *other = clone.get_source_expressions()

            # Wrap pattern in group if required and increment backreferences.
            if pattern.value and not extra_context.get("no_wrap"):
                pattern.value = "(%s)" % re.sub(
                    r"\\([0-9])",
                    lambda m: r"\%d" % (int(m[1]) + 1),
                    pattern.value,
                )

            clone.set_source_expressions([expression, pattern, *other])
            extra_context |= {"force_flags_inline": True, "skip_arguments": slice(2, 4)}
            return clone.as_sql(
                compiler,
                connection,
                template="%(function)s(%(expressions)s)",
                arg_joiner=" FROM ",
                function="SUBSTRING",
                **extra_context,
            )

        return super().as_sql(compiler, connection, **extra_context)


class Repeat(Func):
    function = "REPEAT"
    output_field = CharField()

    def __init__(self, expression, number, **extra):
        if (
            not hasattr(number, "resolve_expression")
            and number is not None
            and number < 0
        ):
            raise ValueError("'number' must be greater or equal to 0.")
        super().__init__(expression, number, **extra)

    def as_oracle(self, compiler, connection, **extra_context):
        expression, number = self.source_expressions
        length = None if number is None else Length(expression) * number
        rpad = RPad(expression, length, expression)
        return rpad.as_sql(compiler, connection, **extra_context)


class Replace(Func):
    function = "REPLACE"

    def __init__(self, expression, text, replacement=Value(""), **extra):
        super().__init__(expression, text, replacement, **extra)


class Reverse(Transform):
    function = "REVERSE"
    lookup_name = "reverse"

    def as_oracle(self, compiler, connection, **extra_context):
        # REVERSE in Oracle is undocumented and doesn't support multi-byte
        # strings. Use a special subquery instead.
        sql, params = super().as_sql(
            compiler,
            connection,
            template=(
                "(SELECT LISTAGG(s) WITHIN GROUP (ORDER BY n DESC) FROM "
                "(SELECT LEVEL n, SUBSTR(%(expressions)s, LEVEL, 1) s "
                "FROM DUAL CONNECT BY LEVEL <= LENGTH(%(expressions)s)) "
                "GROUP BY %(expressions)s)"
            ),
            **extra_context,
        )
        return sql, params * 3


class Right(Left):
    function = "RIGHT"

    def get_substr(self):
        return Substr(
            self.source_expressions[0],
            self.source_expressions[1] * Value(-1),
            self.source_expressions[1],
        )


class RPad(LPad):
    function = "RPAD"


class RTrim(Transform):
    function = "RTRIM"
    lookup_name = "rtrim"


class SHA1(OracleHashMixin, PostgreSQLSHAMixin, Transform):
    function = "SHA1"
    lookup_name = "sha1"


class SHA224(MySQLSHA2Mixin, PostgreSQLSHAMixin, Transform):
    function = "SHA224"
    lookup_name = "sha224"

    def as_oracle(self, compiler, connection, **extra_context):
        raise NotSupportedError("SHA224 is not supported on Oracle.")


class SHA256(MySQLSHA2Mixin, OracleHashMixin, PostgreSQLSHAMixin, Transform):
    function = "SHA256"
    lookup_name = "sha256"


class SHA384(MySQLSHA2Mixin, OracleHashMixin, PostgreSQLSHAMixin, Transform):
    function = "SHA384"
    lookup_name = "sha384"


class SHA512(MySQLSHA2Mixin, OracleHashMixin, PostgreSQLSHAMixin, Transform):
    function = "SHA512"
    lookup_name = "sha512"


class StrIndex(Func):
    """
    Return a positive integer corresponding to the 1-indexed position of the
    first occurrence of a substring inside another string, or 0 if the
    substring is not found.
    """

    function = "INSTR"
    arity = 2
    output_field = IntegerField()

    def as_postgresql(self, compiler, connection, **extra_context):
        return super().as_sql(compiler, connection, function="STRPOS", **extra_context)


class Substr(Func):
    function = "SUBSTRING"
    output_field = CharField()

    def __init__(self, expression, pos, length=None, **extra):
        """
        expression: the name of a field, or an expression returning a string
        pos: an integer > 0, or an expression returning an integer
        length: an optional number of characters to return
        """
        if not hasattr(pos, "resolve_expression"):
            if pos < 1:
                raise ValueError("'pos' must be greater than 0")
        expressions = [expression, pos]
        if length is not None:
            expressions.append(length)
        super().__init__(*expressions, **extra)

    def as_sqlite(self, compiler, connection, **extra_context):
        return super().as_sql(compiler, connection, function="SUBSTR", **extra_context)

    def as_oracle(self, compiler, connection, **extra_context):
        return super().as_sql(compiler, connection, function="SUBSTR", **extra_context)


class Trim(Transform):
    function = "TRIM"
    lookup_name = "trim"


class Upper(Transform):
    function = "UPPER"
    lookup_name = "upper"
