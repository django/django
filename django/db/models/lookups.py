import itertools
import math

from django.core.exceptions import EmptyResultSet
from django.db.models.expressions import Case, Expression, Func, Value, When
from django.db.models.fields import (
    BooleanField,
    CharField,
    DateTimeField,
    Field,
    IntegerField,
    UUIDField,
)
from django.db.models.query_utils import RegisterLookupMixin
from django.utils.datastructures import OrderedSet
from django.utils.functional import cached_property
from django.utils.hashable import make_hashable


class Lookup(Expression):
    lookup_name = None
    prepare_rhs = True
    can_use_none_as_rhs = False

    def __init__(self, lhs, rhs):
        self.lhs, self.rhs = lhs, rhs
        self.rhs = self.get_prep_lookup()
        self.lhs = self.get_prep_lhs()
        if hasattr(self.lhs, "get_bilateral_transforms"):
            bilateral_transforms = self.lhs.get_bilateral_transforms()
        else:
            bilateral_transforms = []
        if bilateral_transforms:
            # Warn the user as soon as possible if they are trying to apply
            # a bilateral transformation on a nested QuerySet: that won't work.
            from django.db.models.sql.query import Query  # avoid circular import

            if isinstance(rhs, Query):
                raise NotImplementedError(
                    "Bilateral transformations on nested querysets are not implemented."
                )
        self.bilateral_transforms = bilateral_transforms

    def apply_bilateral_transforms(self, value):
        for transform in self.bilateral_transforms:
            value = transform(value)
        return value

    def __repr__(self):
        return f"{self.__class__.__name__}({self.lhs!r}, {self.rhs!r})"

    def batch_process_rhs(self, compiler, connection, rhs=None):
        if rhs is None:
            rhs = self.rhs
        if self.bilateral_transforms:
            sqls, sqls_params = [], []
            for p in rhs:
                value = Value(p, output_field=self.lhs.output_field)
                value = self.apply_bilateral_transforms(value)
                value = value.resolve_expression(compiler.query)
                sql, sql_params = compiler.compile(value)
                sqls.append(sql)
                sqls_params.extend(sql_params)
        else:
            _, params = self.get_db_prep_lookup(rhs, connection)
            sqls, sqls_params = ["%s"] * len(params), params
        return sqls, sqls_params

    def get_source_expressions(self):
        if self.rhs_is_direct_value():
            return [self.lhs]
        return [self.lhs, self.rhs]

    def set_source_expressions(self, new_exprs):
        if len(new_exprs) == 1:
            self.lhs = new_exprs[0]
        else:
            self.lhs, self.rhs = new_exprs

    def get_prep_lookup(self):
        if not self.prepare_rhs or hasattr(self.rhs, "resolve_expression"):
            return self.rhs
        if hasattr(self.lhs, "output_field"):
            if hasattr(self.lhs.output_field, "get_prep_value"):
                return self.lhs.output_field.get_prep_value(self.rhs)
        elif self.rhs_is_direct_value():
            return Value(self.rhs)
        return self.rhs

    def get_prep_lhs(self):
        if hasattr(self.lhs, "resolve_expression"):
            return self.lhs
        return Value(self.lhs)

    def get_db_prep_lookup(self, value, connection):
        return ("%s", [value])

    def process_lhs(self, compiler, connection, lhs=None):
        lhs = lhs or self.lhs
        if hasattr(lhs, "resolve_expression"):
            lhs = lhs.resolve_expression(compiler.query)
        sql, params = compiler.compile(lhs)
        if isinstance(lhs, Lookup):
            # Wrapped in parentheses to respect operator precedence.
            sql = f"({sql})"
        return sql, params

    def process_rhs(self, compiler, connection):
        value = self.rhs
        if self.bilateral_transforms:
            if self.rhs_is_direct_value():
                # Do not call get_db_prep_lookup here as the value will be
                # transformed before being used for lookup
                value = Value(value, output_field=self.lhs.output_field)
            value = self.apply_bilateral_transforms(value)
            value = value.resolve_expression(compiler.query)
        if hasattr(value, "as_sql"):
            sql, params = compiler.compile(value)
            # Ensure expression is wrapped in parentheses to respect operator
            # precedence but avoid double wrapping as it can be misinterpreted
            # on some backends (e.g. subqueries on SQLite).
            if sql and sql[0] != "(":
                sql = "(%s)" % sql
            return sql, params
        else:
            return self.get_db_prep_lookup(value, connection)

    def rhs_is_direct_value(self):
        return not hasattr(self.rhs, "as_sql")

    def get_group_by_cols(self, alias=None):
        cols = []
        for source in self.get_source_expressions():
            cols.extend(source.get_group_by_cols())
        return cols

    def as_oracle(self, compiler, connection):
        # Oracle doesn't allow EXISTS() and filters to be compared to another
        # expression unless they're wrapped in a CASE WHEN.
        wrapped = False
        exprs = []
        for expr in (self.lhs, self.rhs):
            if connection.ops.conditional_expression_supported_in_where_clause(expr):
                expr = Case(When(expr, then=True), default=False)
                wrapped = True
            exprs.append(expr)
        lookup = type(self)(*exprs) if wrapped else self
        return lookup.as_sql(compiler, connection)

    @cached_property
    def output_field(self):
        return BooleanField()

    @property
    def identity(self):
        return self.__class__, self.lhs, self.rhs

    def __eq__(self, other):
        if not isinstance(other, Lookup):
            return NotImplemented
        return self.identity == other.identity

    def __hash__(self):
        return hash(make_hashable(self.identity))

    def resolve_expression(
        self, query=None, allow_joins=True, reuse=None, summarize=False, for_save=False
    ):
        c = self.copy()
        c.is_summary = summarize
        c.lhs = self.lhs.resolve_expression(
            query, allow_joins, reuse, summarize, for_save
        )
        c.rhs = self.rhs.resolve_expression(
            query, allow_joins, reuse, summarize, for_save
        )
        return c

    def select_format(self, compiler, sql, params):
        # Wrap filters with a CASE WHEN expression if a database backend
        # (e.g. Oracle) doesn't support boolean expression in SELECT or GROUP
        # BY list.
        if not compiler.connection.features.supports_boolean_expr_in_select_clause:
            sql = f"CASE WHEN {sql} THEN 1 ELSE 0 END"
        return sql, params


class Transform(RegisterLookupMixin, Func):
    """
    RegisterLookupMixin() is first so that get_lookup() and get_transform()
    first examine self and then check output_field.
    """

    bilateral = False
    arity = 1

    @property
    def lhs(self):
        return self.get_source_expressions()[0]

    def get_bilateral_transforms(self):
        if hasattr(self.lhs, "get_bilateral_transforms"):
            bilateral_transforms = self.lhs.get_bilateral_transforms()
        else:
            bilateral_transforms = []
        if self.bilateral:
            bilateral_transforms.append(self.__class__)
        return bilateral_transforms


class BuiltinLookup(Lookup):
    def process_lhs(self, compiler, connection, lhs=None):
        lhs_sql, params = super().process_lhs(compiler, connection, lhs)
        field_internal_type = self.lhs.output_field.get_internal_type()
        db_type = self.lhs.output_field.db_type(connection=connection)
        lhs_sql = connection.ops.field_cast_sql(db_type, field_internal_type) % lhs_sql
        lhs_sql = (
            connection.ops.lookup_cast(self.lookup_name, field_internal_type) % lhs_sql
        )
        return lhs_sql, list(params)

    def as_sql(self, compiler, connection):
        lhs_sql, params = self.process_lhs(compiler, connection)
        rhs_sql, rhs_params = self.process_rhs(compiler, connection)
        params.extend(rhs_params)
        rhs_sql = self.get_rhs_op(connection, rhs_sql)
        return "%s %s" % (lhs_sql, rhs_sql), params

    def get_rhs_op(self, connection, rhs):
        return connection.operators[self.lookup_name] % rhs


class FieldGetDbPrepValueMixin:
    """
    Some lookups require Field.get_db_prep_value() to be called on their
    inputs.
    """

    get_db_prep_lookup_value_is_iterable = False

    def get_db_prep_lookup(self, value, connection):
        # For relational fields, use the 'target_field' attribute of the
        # output_field.
        field = getattr(self.lhs.output_field, "target_field", None)
        get_db_prep_value = (
            getattr(field, "get_db_prep_value", None)
            or self.lhs.output_field.get_db_prep_value
        )
        return (
            "%s",
            [get_db_prep_value(v, connection, prepared=True) for v in value]
            if self.get_db_prep_lookup_value_is_iterable
            else [get_db_prep_value(value, connection, prepared=True)],
        )


class FieldGetDbPrepValueIterableMixin(FieldGetDbPrepValueMixin):
    """
    Some lookups require Field.get_db_prep_value() to be called on each value
    in an iterable.
    """

    get_db_prep_lookup_value_is_iterable = True

    def get_prep_lookup(self):
        if hasattr(self.rhs, "resolve_expression"):
            return self.rhs
        prepared_values = []
        for rhs_value in self.rhs:
            if hasattr(rhs_value, "resolve_expression"):
                # An expression will be handled by the database but can coexist
                # alongside real values.
                pass
            elif self.prepare_rhs and hasattr(self.lhs.output_field, "get_prep_value"):
                rhs_value = self.lhs.output_field.get_prep_value(rhs_value)
            prepared_values.append(rhs_value)
        return prepared_values

    def process_rhs(self, compiler, connection):
        if self.rhs_is_direct_value():
            # rhs should be an iterable of values. Use batch_process_rhs()
            # to prepare/transform those values.
            return self.batch_process_rhs(compiler, connection)
        else:
            return super().process_rhs(compiler, connection)

    def resolve_expression_parameter(self, compiler, connection, sql, param):
        params = [param]
        if hasattr(param, "resolve_expression"):
            param = param.resolve_expression(compiler.query)
        if hasattr(param, "as_sql"):
            sql, params = compiler.compile(param)
        return sql, params

    def batch_process_rhs(self, compiler, connection, rhs=None):
        pre_processed = super().batch_process_rhs(compiler, connection, rhs)
        # The params list may contain expressions which compile to a
        # sql/param pair. Zip them to get sql and param pairs that refer to the
        # same argument and attempt to replace them with the result of
        # compiling the param step.
        sql, params = zip(
            *(
                self.resolve_expression_parameter(compiler, connection, sql, param)
                for sql, param in zip(*pre_processed)
            )
        )
        params = itertools.chain.from_iterable(params)
        return sql, tuple(params)


class PostgresOperatorLookup(FieldGetDbPrepValueMixin, Lookup):
    """Lookup defined by operators on PostgreSQL."""

    postgres_operator = None

    def as_postgresql(self, compiler, connection):
        lhs, lhs_params = self.process_lhs(compiler, connection)
        rhs, rhs_params = self.process_rhs(compiler, connection)
        params = tuple(lhs_params) + tuple(rhs_params)
        return "%s %s %s" % (lhs, self.postgres_operator, rhs), params


@Field.register_lookup
class Exact(FieldGetDbPrepValueMixin, BuiltinLookup):
    lookup_name = "exact"

    def get_prep_lookup(self):
        from django.db.models.sql.query import Query  # avoid circular import

        if isinstance(self.rhs, Query):
            if self.rhs.has_limit_one():
                if not self.rhs.has_select_fields:
                    self.rhs.clear_select_clause()
                    self.rhs.add_fields(["pk"])
            else:
                raise ValueError(
                    "The QuerySet value for an exact lookup must be limited to "
                    "one result using slicing."
                )
        return super().get_prep_lookup()

    def as_sql(self, compiler, connection):
        # Avoid comparison against direct rhs if lhs is a boolean value. That
        # turns "boolfield__exact=True" into "WHERE boolean_field" instead of
        # "WHERE boolean_field = True" when allowed.
        if (
            isinstance(self.rhs, bool)
            and getattr(self.lhs, "conditional", False)
            and connection.ops.conditional_expression_supported_in_where_clause(
                self.lhs
            )
        ):
            lhs_sql, params = self.process_lhs(compiler, connection)
            template = "%s" if self.rhs else "NOT %s"
            return template % lhs_sql, params
        return super().as_sql(compiler, connection)


@Field.register_lookup
class IExact(BuiltinLookup):
    lookup_name = "iexact"
    prepare_rhs = False

    def process_rhs(self, qn, connection):
        rhs, params = super().process_rhs(qn, connection)
        if params:
            params[0] = connection.ops.prep_for_iexact_query(params[0])
        return rhs, params


@Field.register_lookup
class GreaterThan(FieldGetDbPrepValueMixin, BuiltinLookup):
    lookup_name = "gt"


@Field.register_lookup
class GreaterThanOrEqual(FieldGetDbPrepValueMixin, BuiltinLookup):
    lookup_name = "gte"


@Field.register_lookup
class LessThan(FieldGetDbPrepValueMixin, BuiltinLookup):
    lookup_name = "lt"


@Field.register_lookup
class LessThanOrEqual(FieldGetDbPrepValueMixin, BuiltinLookup):
    lookup_name = "lte"


class IntegerFieldFloatRounding:
    """
    Allow floats to work as query values for IntegerField. Without this, the
    decimal portion of the float would always be discarded.
    """

    def get_prep_lookup(self):
        if isinstance(self.rhs, float):
            self.rhs = math.ceil(self.rhs)
        return super().get_prep_lookup()


@IntegerField.register_lookup
class IntegerGreaterThanOrEqual(IntegerFieldFloatRounding, GreaterThanOrEqual):
    pass


@IntegerField.register_lookup
class IntegerLessThan(IntegerFieldFloatRounding, LessThan):
    pass


@Field.register_lookup
class In(FieldGetDbPrepValueIterableMixin, BuiltinLookup):
    lookup_name = "in"

    def get_prep_lookup(self):
        from django.db.models.sql.query import Query  # avoid circular import

        if isinstance(self.rhs, Query):
            self.rhs.clear_ordering(clear_default=True)
            if not self.rhs.has_select_fields:
                self.rhs.clear_select_clause()
                self.rhs.add_fields(["pk"])
        return super().get_prep_lookup()

    def process_rhs(self, compiler, connection):
        db_rhs = getattr(self.rhs, "_db", None)
        if db_rhs is not None and db_rhs != connection.alias:
            raise ValueError(
                "Subqueries aren't allowed across different databases. Force "
                "the inner query to be evaluated using `list(inner_query)`."
            )

        if self.rhs_is_direct_value():
            # Remove None from the list as NULL is never equal to anything.
            try:
                rhs = OrderedSet(self.rhs)
                rhs.discard(None)
            except TypeError:  # Unhashable items in self.rhs
                rhs = [r for r in self.rhs if r is not None]

            if not rhs:
                raise EmptyResultSet

            # rhs should be an iterable; use batch_process_rhs() to
            # prepare/transform those values.
            sqls, sqls_params = self.batch_process_rhs(compiler, connection, rhs)
            placeholder = "(" + ", ".join(sqls) + ")"
            return (placeholder, sqls_params)
        return super().process_rhs(compiler, connection)

    def get_rhs_op(self, connection, rhs):
        return "IN %s" % rhs

    def as_sql(self, compiler, connection):
        max_in_list_size = connection.ops.max_in_list_size()
        if (
            self.rhs_is_direct_value()
            and max_in_list_size
            and len(self.rhs) > max_in_list_size
        ):
            return self.split_parameter_list_as_sql(compiler, connection)
        return super().as_sql(compiler, connection)

    def split_parameter_list_as_sql(self, compiler, connection):
        # This is a special case for databases which limit the number of
        # elements which can appear in an 'IN' clause.
        max_in_list_size = connection.ops.max_in_list_size()
        lhs, lhs_params = self.process_lhs(compiler, connection)
        rhs, rhs_params = self.batch_process_rhs(compiler, connection)
        in_clause_elements = ["("]
        params = []
        for offset in range(0, len(rhs_params), max_in_list_size):
            if offset > 0:
                in_clause_elements.append(" OR ")
            in_clause_elements.append("%s IN (" % lhs)
            params.extend(lhs_params)
            sqls = rhs[offset : offset + max_in_list_size]
            sqls_params = rhs_params[offset : offset + max_in_list_size]
            param_group = ", ".join(sqls)
            in_clause_elements.append(param_group)
            in_clause_elements.append(")")
            params.extend(sqls_params)
        in_clause_elements.append(")")
        return "".join(in_clause_elements), params


class PatternLookup(BuiltinLookup):
    param_pattern = "%%%s%%"
    prepare_rhs = False

    def get_rhs_op(self, connection, rhs):
        # Assume we are in startswith. We need to produce SQL like:
        #     col LIKE %s, ['thevalue%']
        # For python values we can (and should) do that directly in Python,
        # but if the value is for example reference to other column, then
        # we need to add the % pattern match to the lookup by something like
        #     col LIKE othercol || '%%'
        # So, for Python values we don't need any special pattern, but for
        # SQL reference values or SQL transformations we need the correct
        # pattern added.
        if hasattr(self.rhs, "as_sql") or self.bilateral_transforms:
            pattern = connection.pattern_ops[self.lookup_name].format(
                connection.pattern_esc
            )
            return pattern.format(rhs)
        else:
            return super().get_rhs_op(connection, rhs)

    def process_rhs(self, qn, connection):
        rhs, params = super().process_rhs(qn, connection)
        if self.rhs_is_direct_value() and params and not self.bilateral_transforms:
            params[0] = self.param_pattern % connection.ops.prep_for_like_query(
                params[0]
            )
        return rhs, params


@Field.register_lookup
class Contains(PatternLookup):
    lookup_name = "contains"


@Field.register_lookup
class IContains(Contains):
    lookup_name = "icontains"


@Field.register_lookup
class StartsWith(PatternLookup):
    lookup_name = "startswith"
    param_pattern = "%s%%"


@Field.register_lookup
class IStartsWith(StartsWith):
    lookup_name = "istartswith"


@Field.register_lookup
class EndsWith(PatternLookup):
    lookup_name = "endswith"
    param_pattern = "%%%s"


@Field.register_lookup
class IEndsWith(EndsWith):
    lookup_name = "iendswith"


@Field.register_lookup
class Range(FieldGetDbPrepValueIterableMixin, BuiltinLookup):
    lookup_name = "range"

    def get_rhs_op(self, connection, rhs):
        return "BETWEEN %s AND %s" % (rhs[0], rhs[1])


@Field.register_lookup
class IsNull(BuiltinLookup):
    lookup_name = "isnull"
    prepare_rhs = False

    def as_sql(self, compiler, connection):
        if not isinstance(self.rhs, bool):
            raise ValueError(
                "The QuerySet value for an isnull lookup must be True or False."
            )
        sql, params = compiler.compile(self.lhs)
        if self.rhs:
            return "%s IS NULL" % sql, params
        else:
            return "%s IS NOT NULL" % sql, params


@Field.register_lookup
class Regex(BuiltinLookup):
    lookup_name = "regex"
    prepare_rhs = False

    def as_sql(self, compiler, connection):
        if self.lookup_name in connection.operators:
            return super().as_sql(compiler, connection)
        else:
            lhs, lhs_params = self.process_lhs(compiler, connection)
            rhs, rhs_params = self.process_rhs(compiler, connection)
            sql_template = connection.ops.regex_lookup(self.lookup_name)
            return sql_template % (lhs, rhs), lhs_params + rhs_params


@Field.register_lookup
class IRegex(Regex):
    lookup_name = "iregex"


class YearLookup(Lookup):
    def year_lookup_bounds(self, connection, year):
        from django.db.models.functions import ExtractIsoYear

        iso_year = isinstance(self.lhs, ExtractIsoYear)
        output_field = self.lhs.lhs.output_field
        if isinstance(output_field, DateTimeField):
            bounds = connection.ops.year_lookup_bounds_for_datetime_field(
                year,
                iso_year=iso_year,
            )
        else:
            bounds = connection.ops.year_lookup_bounds_for_date_field(
                year,
                iso_year=iso_year,
            )
        return bounds

    def as_sql(self, compiler, connection):
        # Avoid the extract operation if the rhs is a direct value to allow
        # indexes to be used.
        if self.rhs_is_direct_value():
            # Skip the extract part by directly using the originating field,
            # that is self.lhs.lhs.
            lhs_sql, params = self.process_lhs(compiler, connection, self.lhs.lhs)
            rhs_sql, _ = self.process_rhs(compiler, connection)
            rhs_sql = self.get_direct_rhs_sql(connection, rhs_sql)
            start, finish = self.year_lookup_bounds(connection, self.rhs)
            params.extend(self.get_bound_params(start, finish))
            return "%s %s" % (lhs_sql, rhs_sql), params
        return super().as_sql(compiler, connection)

    def get_direct_rhs_sql(self, connection, rhs):
        return connection.operators[self.lookup_name] % rhs

    def get_bound_params(self, start, finish):
        raise NotImplementedError(
            "subclasses of YearLookup must provide a get_bound_params() method"
        )


class YearExact(YearLookup, Exact):
    def get_direct_rhs_sql(self, connection, rhs):
        return "BETWEEN %s AND %s"

    def get_bound_params(self, start, finish):
        return (start, finish)


class YearGt(YearLookup, GreaterThan):
    def get_bound_params(self, start, finish):
        return (finish,)


class YearGte(YearLookup, GreaterThanOrEqual):
    def get_bound_params(self, start, finish):
        return (start,)


class YearLt(YearLookup, LessThan):
    def get_bound_params(self, start, finish):
        return (start,)


class YearLte(YearLookup, LessThanOrEqual):
    def get_bound_params(self, start, finish):
        return (finish,)


class UUIDTextMixin:
    """
    Strip hyphens from a value when filtering a UUIDField on backends without
    a native datatype for UUID.
    """

    def process_rhs(self, qn, connection):
        if not connection.features.has_native_uuid_field:
            from django.db.models.functions import Replace

            if self.rhs_is_direct_value():
                self.rhs = Value(self.rhs)
            self.rhs = Replace(
                self.rhs, Value("-"), Value(""), output_field=CharField()
            )
        rhs, params = super().process_rhs(qn, connection)
        return rhs, params


@UUIDField.register_lookup
class UUIDIExact(UUIDTextMixin, IExact):
    pass


@UUIDField.register_lookup
class UUIDContains(UUIDTextMixin, Contains):
    pass


@UUIDField.register_lookup
class UUIDIContains(UUIDTextMixin, IContains):
    pass


@UUIDField.register_lookup
class UUIDStartsWith(UUIDTextMixin, StartsWith):
    pass


@UUIDField.register_lookup
class UUIDIStartsWith(UUIDTextMixin, IStartsWith):
    pass


@UUIDField.register_lookup
class UUIDEndsWith(UUIDTextMixin, EndsWith):
    pass


@UUIDField.register_lookup
class UUIDIEndsWith(UUIDTextMixin, IEndsWith):
    pass
