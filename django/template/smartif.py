"""
Parser and utilities for the smart 'if' tag
"""
import operator

# Using a simple top down parser, as described here:
#    http://effbot.org/zone/simple-top-down-parsing.htm.
# 'led' = left denotation
# 'nud' = null denotation
# 'bp' = binding power (left = lbp, right = rbp)

class TokenBase(object):
    """
    Base class for operators and literals, mainly for debugging and for throwing
    syntax errors.
    """
    id = None # node/token type name
    value = None # used by literals
    first = second = None # used by tree nodes

    def nud(self, parser):
        # Null denotation - called in prefix context
        raise parser.error_class(
            "Not expecting '%s' in this position in if tag." % self.id
        )

    def led(self, left, parser):
        # Left denotation - called in infix context
        raise parser.error_class(
            "Not expecting '%s' as infix operator in if tag." % self.id
        )

    def display(self):
        """
        Returns what to display in error messages for this node
        """
        return self.id

    def __repr__(self):
        out = [str(x) for x in [self.id, self.first, self.second] if x is not None]
        return "(" + " ".join(out) + ")"


def infix(bp, func):
    """
    Creates an infix operator, given a binding power and a function that
    evaluates the node
    """
    class Operator(TokenBase):
        lbp = bp

        def led(self, left, parser):
            self.first = left
            self.second = parser.expression(bp)
            return self

        def eval(self, context):
            try:
                return func(self.first.eval(context), self.second.eval(context))
            except Exception:
                # Templates shouldn't throw exceptions when rendering.  We are
                # most likely to get exceptions for things like {% if foo in bar
                # %} where 'bar' does not support 'in', so default to False
                return False

    return Operator


def prefix(bp, func):
    """
    Creates a prefix operator, given a binding power and a function that
    evaluates the node.
    """
    class Operator(TokenBase):
        lbp = bp

        def nud(self, parser):
            self.first = parser.expression(bp)
            self.second = None
            return self

        def eval(self, context):
            try:
                return func(self.first.eval(context))
            except Exception:
                return False

    return Operator


# Operator precedence follows Python.
# NB - we can get slightly more accurate syntax error messages by not using the
# same object for '==' and '='.

OPERATORS = {
    'or': infix(6, lambda x, y: x or y),
    'and': infix(7, lambda x, y: x and y),
    'not': prefix(8, operator.not_),
    'in': infix(9, lambda x, y: x in y),
    '=': infix(10, operator.eq),
    '==': infix(10, operator.eq),
    '!=': infix(10, operator.ne),
    '>': infix(10, operator.gt),
    '>=': infix(10, operator.ge),
    '<': infix(10, operator.lt),
    '<=': infix(10, operator.le),
}

# Assign 'id' to each:
for key, op in OPERATORS.items():
    op.id = key


class Literal(TokenBase):
    """
    A basic self-resolvable object similar to a Django template variable.
    """
    # IfParser uses Literal in create_var, but TemplateIfParser overrides
    # create_var so that a proper implementation that actually resolves
    # variables, filters etc is used.
    id = "literal"
    lbp = 0

    def __init__(self, value):
        self.value = value

    def display(self):
        return repr(self.value)

    def nud(self, parser):
        return self

    def eval(self, context):
        return self.value

    def __repr__(self):
        return "(%s %r)" % (self.id, self.value)


class EndToken(TokenBase):
    lbp = 0

    def nud(self, parser):
        raise parser.error_class("Unexpected end of expression in if tag.")

EndToken = EndToken()


class IfParser(object):
    error_class = ValueError

    def __init__(self, tokens):
        self.tokens = map(self.translate_tokens, tokens)
        self.pos = 0
        self.current_token = self.next()

    def translate_tokens(self, token):
        try:
            op = OPERATORS[token]
        except (KeyError, TypeError):
            return self.create_var(token)
        else:
            return op()

    def next(self):
        if self.pos >= len(self.tokens):
            return EndToken
        else:
            retval = self.tokens[self.pos]
            self.pos += 1
            return retval

    def parse(self):
        retval = self.expression()
        # Check that we have exhausted all the tokens
        if self.current_token is not EndToken:
            raise self.error_class("Unused '%s' at end of if expression." %
                                   self.current_token.display())
        return retval

    def expression(self, rbp=0):
        t = self.current_token
        self.current_token = self.next()
        left = t.nud(self)
        while rbp < self.current_token.lbp:
            t = self.current_token
            self.current_token = self.next()
            left = t.led(left, self)
        return left

    def create_var(self, value):
        return Literal(value)
