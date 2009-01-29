from copy import deepcopy
from datetime import datetime

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

    def evaluate(self, evaluator, qn):
        return evaluator.evaluate_node(self, qn)

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

    def evaluate(self, evaluator, qn):
        return evaluator.evaluate_leaf(self, qn)
