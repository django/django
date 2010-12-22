import datetime

from django.utils import tree
from django.utils.copycompat import deepcopy

class ExpressionNode(tree.Node):
    """
    Base class for all query expressions.
    """
    # Arithmetic connectors
    ADD = '+'
    SUB = '-'
    MUL = '*'
    DIV = '/'
    MOD = '%%'  # This is a quoted % operator - it is quoted
                # because it can be used in strings that also
                # have parameter substitution.

    # Bitwise operators
    AND = '&'
    OR = '|'

    def __init__(self, children=None, connector=None, negated=False):
        if children is not None and len(children) > 1 and connector is None:
            raise TypeError('You have to specify a connector.')
        super(ExpressionNode, self).__init__(children, connector, negated)

    def _combine(self, other, connector, reversed, node=None):
        if isinstance(other, datetime.timedelta):
            return DateModifierNode([self, other], connector)

        if reversed:
            obj = ExpressionNode([other], connector)
            obj.add(node or self, connector)
        else:
            obj = node or ExpressionNode([self], connector)
            obj.add(other, connector)
        return obj

    ###################
    # VISITOR METHODS #
    ###################

    def prepare(self, evaluator, query, allow_joins):
        return evaluator.prepare_node(self, query, allow_joins)

    def evaluate(self, evaluator, qn, connection):
        return evaluator.evaluate_node(self, qn, connection)

    #############
    # OPERATORS #
    #############

    def __add__(self, other):
        return self._combine(other, self.ADD, False)

    def __sub__(self, other):
        return self._combine(other, self.SUB, False)

    def __mul__(self, other):
        return self._combine(other, self.MUL, False)

    def __div__(self, other):
        return self._combine(other, self.DIV, False)

    def __mod__(self, other):
        return self._combine(other, self.MOD, False)

    def __and__(self, other):
        return self._combine(other, self.AND, False)

    def __or__(self, other):
        return self._combine(other, self.OR, False)

    def __radd__(self, other):
        return self._combine(other, self.ADD, True)

    def __rsub__(self, other):
        return self._combine(other, self.SUB, True)

    def __rmul__(self, other):
        return self._combine(other, self.MUL, True)

    def __rdiv__(self, other):
        return self._combine(other, self.DIV, True)

    def __rmod__(self, other):
        return self._combine(other, self.MOD, True)

    def __rand__(self, other):
        return self._combine(other, self.AND, True)

    def __ror__(self, other):
        return self._combine(other, self.OR, True)

    def prepare_database_save(self, unused):
        return self

class F(ExpressionNode):
    """
    An expression representing the value of the given field.
    """
    def __init__(self, name):
        super(F, self).__init__(None, None, False)
        self.name = name

    def __deepcopy__(self, memodict):
        obj = super(F, self).__deepcopy__(memodict)
        obj.name = self.name
        return obj

    def prepare(self, evaluator, query, allow_joins):
        return evaluator.prepare_leaf(self, query, allow_joins)

    def evaluate(self, evaluator, qn, connection):
        return evaluator.evaluate_leaf(self, qn, connection)

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

    def evaluate(self, evaluator, qn, connection):
        return evaluator.evaluate_date_modifier_node(self, qn, connection)
