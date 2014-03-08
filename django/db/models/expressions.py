import copy
import datetime

from django.core.exceptions import FieldError
from django.db.models.constants import LOOKUP_SEP
from django.db.models.fields import FieldDoesNotExist
from django.db.models.query_utils import refs_aggregate
from django.db.models.sql.datastructures import Col
from django.utils.functional import cached_property
from django.utils import tree


class ExpressionNode(tree.Node):
    """
    Base class for all query expressions.
    """

    # Arithmetic connectors
    ADD = '+'
    SUB = '-'
    MUL = '*'
    DIV = '/'
    POW = '^'
    MOD = '%%'  # This is a quoted % operator - it is quoted
                # because it can be used in strings that also
                # have parameter substitution.

    # Bitwise operators - note that these are generated by .bitand()
    # and .bitor(), the '&' and '|' are reserved for boolean operator
    # usage.
    BITAND = '&'
    BITOR = '|'

    validate_name = False

    # aggregate specific fields
    is_aggregate = False
    is_summary = False
    # sql/query.resolve_aggregate uses below to coerce
    is_ordinal = False
    is_computed = False

    def __init__(self, children=None, connector=None, negated=False):
        if children is not None and len(children) > 1 and connector is None:
            raise TypeError('You have to specify a connector.')
        super(ExpressionNode, self).__init__(children, connector, negated)
        self.col = None
        self.source = None

    def _combine(self, other, connector, reversed, node=None):
        if isinstance(other, datetime.timedelta):
            return DateModifierNode([self, other], connector)

        if not isinstance(other, ExpressionNode):
            # everything must be some kind of ExpressionNode, so Value is the fallback
            other = Value(other)

        if reversed:
            obj = ExpressionNode([other], connector)
            obj.add(node or self, connector)
        else:
            obj = node or ExpressionNode([self], connector)
            obj.add(other, connector)

        # having a child aggregate infects the entire tree
        obj.is_aggregate = any(c.is_aggregate for c in obj.children)
        return obj

    def as_sql(self, compiler, connection):
        expressions = []
        expression_params = []
        for child in self.children:
            sql, params = compiler.compile(child)
            expressions.append(sql)
            expression_params.extend(params)

        expression_wrapper = '%s'
        if len(self.children) > 1:
            # order of precedence
            expression_wrapper = '(%s)'

        sql = connection.ops.combine_expression(self.connector, expressions)
        return expression_wrapper % sql, expression_params

    def prepare(self, query=None, allow_joins=True, reuse=None):
        for child in self.children:
            if hasattr(child, 'prepare'):
                child.is_summary = self.is_summary
                child.prepare(query, allow_joins, reuse)
        return self

    @property
    def field(self):
        return self.output_type

    @cached_property
    def output_type(self):
        self._resolve_source()
        return self.source

    def get_lookup(self, lookup):
        return self.output_type.get_lookup(lookup)

    def relabeled_clone(self, change_map):
        clone = copy.copy(self)
        new_children = [
            child.relabeled_clone(change_map) if hasattr(child, 'relabeled_clone')
            else child for child in clone.children]
        clone.children = new_children
        return clone

    def contains_aggregate(self, existing_aggregates):
        for child in self.children:
            agg, lookup = child.contains_aggregate(existing_aggregates)
            if agg:
                return agg, lookup
        return False, ()

    def refs_field(self, aggregate_types, field_types):
        """
        Helper method for check_aggregate_support on backends
        """
        return any(child.refs_field(aggregate_types, field_types) for child in self.children)

    def prepare_database_save(self, unused):
        return self

    def evaluate(self, compiler, connection):
        # this method is here for compatability purposes
        return self.as_sql(compiler, connection)

    def get_cols(self):
        cols = []
        for child in self.children:
            cols.extend(child.get_cols())
        return cols

    def get_group_by_cols(self):
        cols = []
        for child in self.children:
            cols.extend(child.get_group_by_cols())
        return cols

    def get_sources(self):
        sources = [self.source] if self.source is not None else []
        for child in self.children:
            sources.extend(child.get_sources())
        return sources

    def _resolve_source(self):
        if self.source is None:
            sources = self.get_sources()
            num_sources = len(sources)
            if num_sources == 0:
                raise FieldError("Cannot resolve expression type, unknown output_type")
            elif num_sources == 1:
                self.source = sources[0]
            else:
                # this could be smarter by allowing certain combinations
                self.source = sources[0]
                for source in sources:
                    if not isinstance(self.source, source.__class__):
                        raise FieldError(
                            "Expression contains mixed types. You must set output_type")

    @property
    def default_alias(self):
        raise TypeError("Complex expressions require kwargs")

    def __bool__(self):
        """
        For truth value testing.
        """
        return True

    #############
    # OPERATORS #
    #############

    def __add__(self, other):
        return self._combine(other, self.ADD, False)

    def __sub__(self, other):
        return self._combine(other, self.SUB, False)

    def __mul__(self, other):
        return self._combine(other, self.MUL, False)

    def __truediv__(self, other):
        return self._combine(other, self.DIV, False)

    def __div__(self, other):  # Python 2 compatibility
        return type(self).__truediv__(self, other)

    def __mod__(self, other):
        return self._combine(other, self.MOD, False)

    def __pow__(self, other):
        return self._combine(other, self.POW, False)

    def __and__(self, other):
        raise NotImplementedError(
            "Use .bitand() and .bitor() for bitwise logical operations."
        )

    def bitand(self, other):
        return self._combine(other, self.BITAND, False)

    def __or__(self, other):
        raise NotImplementedError(
            "Use .bitand() and .bitor() for bitwise logical operations."
        )

    def bitor(self, other):
        return self._combine(other, self.BITOR, False)

    def __radd__(self, other):
        return self._combine(other, self.ADD, True)

    def __rsub__(self, other):
        return self._combine(other, self.SUB, True)

    def __rmul__(self, other):
        return self._combine(other, self.MUL, True)

    def __rtruediv__(self, other):
        return self._combine(other, self.DIV, True)

    def __rdiv__(self, other):  # Python 2 compatibility
        return type(self).__rtruediv__(self, other)

    def __rmod__(self, other):
        return self._combine(other, self.MOD, True)

    def __rpow__(self, other):
        return self._combine(other, self.POW, True)

    def __rand__(self, other):
        raise NotImplementedError(
            "Use .bitand() and .bitor() for bitwise logical operations."
        )

    def __ror__(self, other):
        raise NotImplementedError(
            "Use .bitand() and .bitor() for bitwise logical operations."
        )


class F(ExpressionNode):
    """
    An expression representing the value of the given field.
    """

    validate_name = True

    def __init__(self, name):
        """
        Arguments:
         * name: the name of the field this expression references
        """
        super(F, self).__init__(None, None, False)
        self.name = name

    def prepare(self, query=None, allow_joins=True, reuse=None):
        if not allow_joins and LOOKUP_SEP in self.name:
            raise FieldError("Joined field references are not permitted in this query")

        self.setup_cols(query, reuse)
        return self

    def as_sql(self, compiler, connection):
        if hasattr(self.col, 'as_sql'):
            return compiler.compile(self.col)
        qn = compiler
        return '%s.%s' % (qn(self.col[0]), qn(self.col[1])), []

    def setup_cols(self, query, reuse):
        if query is None:
            return
        field_list = self.name.split(LOOKUP_SEP)
        if self.name in query.aggregates:
            self.col = query.aggregate_select[self.name]
        else:
            try:
                field, sources, opts, join_list, path = query.setup_joins(
                    field_list, query.get_meta(),
                    query.get_initial_alias(), reuse)
                self._used_joins = join_list
                targets, _, join_list = query.trim_joins(sources, join_list, path)
                if reuse is not None:
                    reuse.update(join_list)
                for t in targets:
                    source = self.source if self.source is not None else sources[0]
                    self.col = Col(join_list[-1], t, source)
                if self.source is None:
                    self.source = sources[0]
            except FieldDoesNotExist:
                raise FieldError("Cannot resolve keyword %r into field. "
                                 "Choices are: %s" % (self.name,
                                                      [f.name for f in self.opts.fields]))

    def get_cols(self):
        cols = []
        if isinstance(self.col, tuple):
            cols.append(self.col)
        elif hasattr(self.col, 'get_cols'):
            cols.extend(self.col.get_cols())
        return cols

    def get_group_by_cols(self):
        cols = []
        if isinstance(self.col, tuple):
            cols.append(self.col)
        elif hasattr(self.col, 'get_group_by_cols'):
            cols.extend(self.col.get_group_by_cols())
        return cols

    def get_sources(self):
        return [self.source] if self.source is not None else []

    def contains_aggregate(self, existing_aggregates):
        return refs_aggregate(self.name.split(LOOKUP_SEP), existing_aggregates)

    def relabeled_clone(self, change_map):
        clone = copy.copy(self)
        if hasattr(clone.col, 'relabeled_clone'):
            clone.col = clone.col.relabeled_clone(change_map)
        elif clone.col:
            clone.col = (change_map.get(clone.col[0], clone.col[0]), clone.col[1])
        return clone


class DateModifierNode(ExpressionNode):
    """
    Node that implements the following syntax:
    filter(end_date__gt=F('start_date') + datetime.timedelta(days=3, seconds=200))

    which translates into:
    POSTGRES:
        WHERE end_date > (start_date + INTERVAL '3 days 200 seconds')

    MYSQL:
        WHERE end_date > (start_date + INTERVAL '3 0:0:200:0' DAY_MICROSECOND)

    ORACLE:
        WHERE end_date > (start_date + INTERVAL '3 00:03:20.000000' DAY(1) TO SECOND(6))

    SQLITE:
        WHERE end_date > django_format_dtdelta(start_date, "+" "3", "200", "0")
        (A custom function is used in order to preserve six digits of fractional
        second information on sqlite, and to format both date and datetime values.)

    Note that microsecond comparisons are not well supported with MySQL, since
    MySQL does not store microsecond information.

    Only adding and subtracting timedeltas is supported, attempts to use other
    operations raise a TypeError.
    """
    def __init__(self, children, connector, negated=False):
        if len(children) != 2:
            raise TypeError('Must specify a node and a timedelta.')
        if not isinstance(children[1], datetime.timedelta):
            raise TypeError('Second child must be a timedelta.')
        if connector not in (self.ADD, self.SUB):
            raise TypeError('Connector must be + or -, not %s' % connector)
        super(DateModifierNode, self).__init__(children, connector, negated)

    def as_sql(self, compiler, connection):
        field, timedelta = self.children
        sql, params = compiler.compile(field)

        if (timedelta.days == timedelta.seconds == timedelta.microseconds == 0):
            return sql, params

        return connection.ops.date_interval_sql(sql, self.connector, timedelta), params


class WrappedExpression(ExpressionNode):
    """
    An expression capable of wrapping the output of another expression.
    Useful for writing and composing functions.
    """

    sql_template = '%(function)s(%(field)s)'
    sql_function = None

    def __init__(self, expression, output_type=None, **extra):
        """
        Arguments:
         * expression: a subclass of ExpressionNode, or a string
           referencing a field on the model.

         * output_type: the Model Field type that this expression will
           return, such as IntegerField() or CharField()

         * **extra: key value pairs that map to a replace param in the
           sql_template. The `sql_template` and `sql_function` can also
           be overriden

        Class Attributes:
         * sql_template: a formattable string describing the SQL that
           should be added to the query.

         * sql_function: the function name to insert into `sql_template`
        """
        super(WrappedExpression, self).__init__(None, None, False)
        if not isinstance(expression, ExpressionNode):
            if hasattr(expression, 'as_sql'):
                expression = ColumnNode(expression)
            else:
                # handle traditional string fields by wrapping
                expression = F(expression)
        self.expression = expression
        self.source = output_type
        self.extra = extra
        if 'sql_template' not in extra:
            self.extra['sql_template'] = self.sql_template
        if 'sql_function' not in extra and self.sql_function is not None:
            self.extra['sql_function'] = self.sql_function

    def prepare(self, query=None, allow_joins=True, reuse=None):
        self.expression.prepare(query, allow_joins, reuse)
        if self.source is None:
            self.source = self.expression.output_type
        return self

    def as_sql(self, compiler, connection):
        if 'function' not in self.extra:
            self.extra['function'] = self.extra.get('sql_function', self.sql_function)
        sql, params = compiler.compile(self.expression)
        self.extra['field'] = sql
        template = self.extra['sql_template']
        return template % self.extra, params

    def get_sources(self):
        if self.source is not None:
            return [self.source]
        return self.expression.get_sources()

    def contains_aggregate(self, existing_aggregates):
        return self.expression.contains_aggregate(existing_aggregates)

    def refs_field(self, aggregate_types, field_types):
        return self.refs_field(self.expression)

    def relabeled_clone(self, change_map):
        clone = copy.copy(self)
        clone.expression = clone.expression.relabeled_clone(change_map)
        return clone


class Value(ExpressionNode):
    """
    Represents a wrapped value as a node, allowing all children
    to act as nodes
    """

    def __init__(self, name, output_type=None):
        """
        Arguments:
         * name: the value this expression represents. The value will be
           added into the sql parameter list and properly quoted

         * output_type: the Model Field type that this expression will
           return, such as IntegerField() or CharField()
        """
        super(Value, self).__init__(None, None, False)
        self.name = name
        self.source = output_type

    def as_sql(self, compiler, connection):
        return '%s', [self.name]


class ColumnNode(Value):
    """
    Represents a node that wraps a column object that adheres to the Query Expression API.
    """

    def __init__(self, column):
        if (not hasattr(column, 'as_sql') or
                not hasattr(column, 'get_lookup') or
                not hasattr(column, 'output_type')):
            raise TypeError("'column' must implement Query Expression API")
        super(ColumnNode, self).__init__(column)
        self.col = column
        self.source = column.output_type

    def relabeled_clone(self, change_map):
        return self.name.relabeled_clone(change_map)

    def as_sql(self, compiler, connection):
        return compiler.compile(self.name)

    def get_cols(self):
        cols = []
        if isinstance(self.col, tuple):
            cols.append(self.col)
        elif hasattr(self.col, 'get_cols'):
            cols.extend(self.col.get_cols())
        return cols
