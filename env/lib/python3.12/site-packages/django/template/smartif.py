"""
Parser and utilities for the smart 'if' tag
"""

# Using a simple top down parser, as described here:
#    https://11l-lang.org/archive/simple-top-down-parsing/
# 'led' = left denotation
# 'nud' = null denotation
# 'bp' = binding power (left = lbp, right = rbp)


class TokenBase:
    """
    Base class for operators and literals, mainly for debugging and for throwing
    syntax errors.
    """

    id = None  # node/token type name
    value = None  # used by literals
    first = second = None  # used by tree nodes

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
        Return what to display in error messages for this node
        """
        return self.id

    def __repr__(self):
        out = [str(x) for x in [self.id, self.first, self.second] if x is not None]
        return "(" + " ".join(out) + ")"


def infix(bp, func):
    """
    Create an infix operator, given a binding power and a function that
    evaluates the node.
    """

    class Operator(TokenBase):
        lbp = bp

        def led(self, left, parser):
            self.first = left
            self.second = parser.expression(bp)
            return self

        def eval(self, context):
            try:
                return func(context, self.first, self.second)
            except Exception:
                # Templates shouldn't throw exceptions when rendering.  We are
                # most likely to get exceptions for things like {% if foo in bar
                # %} where 'bar' does not support 'in', so default to False
                return False

    return Operator


def prefix(bp, func):
    """
    Create a prefix operator, given a binding power and a function that
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
                return func(context, self.first)
            except Exception:
                return False

    return Operator


# Operator precedence follows Python.
# We defer variable evaluation to the lambda to ensure that terms are
# lazily evaluated using Python's boolean parsing logic.
OPERATORS = {
    "or": infix(6, lambda context, x, y: x.eval(context) or y.eval(context)),
    "and": infix(7, lambda context, x, y: x.eval(context) and y.eval(context)),
    "not": prefix(8, lambda context, x: not x.eval(context)),
    "in": infix(9, lambda context, x, y: x.eval(context) in y.eval(context)),
    "not in": infix(9, lambda context, x, y: x.eval(context) not in y.eval(context)),
    "is": infix(10, lambda context, x, y: x.eval(context) is y.eval(context)),
    "is not": infix(10, lambda context, x, y: x.eval(context) is not y.eval(context)),
    "==": infix(10, lambda context, x, y: x.eval(context) == y.eval(context)),
    "!=": infix(10, lambda context, x, y: x.eval(context) != y.eval(context)),
    ">": infix(10, lambda context, x, y: x.eval(context) > y.eval(context)),
    ">=": infix(10, lambda context, x, y: x.eval(context) >= y.eval(context)),
    "<": infix(10, lambda context, x, y: x.eval(context) < y.eval(context)),
    "<=": infix(10, lambda context, x, y: x.eval(context) <= y.eval(context)),
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
    # variables, filters etc. is used.
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


class IfParser:
    error_class = ValueError

    def __init__(self, tokens):
        # Turn 'is','not' and 'not','in' into single tokens.
        num_tokens = len(tokens)
        mapped_tokens = []
        i = 0
        while i < num_tokens:
            token = tokens[i]
            if token == "is" and i + 1 < num_tokens and tokens[i + 1] == "not":
                token = "is not"
                i += 1  # skip 'not'
            elif token == "not" and i + 1 < num_tokens and tokens[i + 1] == "in":
                token = "not in"
                i += 1  # skip 'in'
            mapped_tokens.append(self.translate_token(token))
            i += 1

        self.tokens = mapped_tokens
        self.pos = 0
        self.current_token = self.next_token()

    def translate_token(self, token):
        try:
            op = OPERATORS[token]
        except (KeyError, TypeError):
            return self.create_var(token)
        else:
            return op()

    def next_token(self):
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
            raise self.error_class(
                "Unused '%s' at end of if expression." % self.current_token.display()
            )
        return retval

    def expression(self, rbp=0):
        t = self.current_token
        self.current_token = self.next_token()
        left = t.nud(self)
        while rbp < self.current_token.lbp:
            t = self.current_token
            self.current_token = self.next_token()
            left = t.led(left, self)
        return left

    def create_var(self, value):
        return Literal(value)
