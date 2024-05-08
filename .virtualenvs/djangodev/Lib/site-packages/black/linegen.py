"""
Generating lines of code.
"""

import re
import sys
from dataclasses import replace
from enum import Enum, auto
from functools import partial, wraps
from typing import Collection, Iterator, List, Optional, Set, Union, cast

from black.brackets import (
    COMMA_PRIORITY,
    DOT_PRIORITY,
    STRING_PRIORITY,
    get_leaves_inside_matching_brackets,
    max_delimiter_priority_in_atom,
)
from black.comments import FMT_OFF, generate_comments, list_comments
from black.lines import (
    Line,
    RHSResult,
    append_leaves,
    can_be_split,
    can_omit_invisible_parens,
    is_line_short_enough,
    line_to_string,
)
from black.mode import Feature, Mode, Preview
from black.nodes import (
    ASSIGNMENTS,
    BRACKETS,
    CLOSING_BRACKETS,
    OPENING_BRACKETS,
    STANDALONE_COMMENT,
    STATEMENT,
    WHITESPACE,
    Visitor,
    ensure_visible,
    fstring_to_string,
    get_annotation_type,
    is_arith_like,
    is_async_stmt_or_funcdef,
    is_atom_with_invisible_parens,
    is_docstring,
    is_empty_tuple,
    is_lpar_token,
    is_multiline_string,
    is_name_token,
    is_one_sequence_between,
    is_one_tuple,
    is_parent_function_or_class,
    is_part_of_annotation,
    is_rpar_token,
    is_stub_body,
    is_stub_suite,
    is_tuple_containing_walrus,
    is_type_ignore_comment_string,
    is_vararg,
    is_walrus_assignment,
    is_yield,
    syms,
    wrap_in_parentheses,
)
from black.numerics import normalize_numeric_literal
from black.strings import (
    fix_docstring,
    get_string_prefix,
    normalize_string_prefix,
    normalize_string_quotes,
    normalize_unicode_escape_sequences,
)
from black.trans import (
    CannotTransform,
    StringMerger,
    StringParenStripper,
    StringParenWrapper,
    StringSplitter,
    Transformer,
    hug_power_op,
)
from blib2to3.pgen2 import token
from blib2to3.pytree import Leaf, Node

# types
LeafID = int
LN = Union[Leaf, Node]


class CannotSplit(CannotTransform):
    """A readable split that fits the allotted line length is impossible."""


# This isn't a dataclass because @dataclass + Generic breaks mypyc.
# See also https://github.com/mypyc/mypyc/issues/827.
class LineGenerator(Visitor[Line]):
    """Generates reformatted Line objects.  Empty lines are not emitted.

    Note: destroys the tree it's visiting by mutating prefixes of its leaves
    in ways that will no longer stringify to valid Python code on the tree.
    """

    def __init__(self, mode: Mode, features: Collection[Feature]) -> None:
        self.mode = mode
        self.features = features
        self.current_line: Line
        self.__post_init__()

    def line(self, indent: int = 0) -> Iterator[Line]:
        """Generate a line.

        If the line is empty, only emit if it makes sense.
        If the line is too long, split it first and then generate.

        If any lines were generated, set up a new current_line.
        """
        if not self.current_line:
            self.current_line.depth += indent
            return  # Line is empty, don't emit. Creating a new one unnecessary.

        if len(self.current_line.leaves) == 1 and is_async_stmt_or_funcdef(
            self.current_line.leaves[0]
        ):
            # Special case for async def/for/with statements. `visit_async_stmt`
            # adds an `ASYNC` leaf then visits the child def/for/with statement
            # nodes. Line yields from those nodes shouldn't treat the former
            # `ASYNC` leaf as a complete line.
            return

        complete_line = self.current_line
        self.current_line = Line(mode=self.mode, depth=complete_line.depth + indent)
        yield complete_line

    def visit_default(self, node: LN) -> Iterator[Line]:
        """Default `visit_*()` implementation. Recurses to children of `node`."""
        if isinstance(node, Leaf):
            any_open_brackets = self.current_line.bracket_tracker.any_open_brackets()
            for comment in generate_comments(node):
                if any_open_brackets:
                    # any comment within brackets is subject to splitting
                    self.current_line.append(comment)
                elif comment.type == token.COMMENT:
                    # regular trailing comment
                    self.current_line.append(comment)
                    yield from self.line()

                else:
                    # regular standalone comment
                    yield from self.line()

                    self.current_line.append(comment)
                    yield from self.line()

            if any_open_brackets:
                node.prefix = ""
            if node.type not in WHITESPACE:
                self.current_line.append(node)
        yield from super().visit_default(node)

    def visit_test(self, node: Node) -> Iterator[Line]:
        """Visit an `x if y else z` test"""

        already_parenthesized = (
            node.prev_sibling and node.prev_sibling.type == token.LPAR
        )

        if not already_parenthesized:
            # Similar to logic in wrap_in_parentheses
            lpar = Leaf(token.LPAR, "")
            rpar = Leaf(token.RPAR, "")
            prefix = node.prefix
            node.prefix = ""
            lpar.prefix = prefix
            node.insert_child(0, lpar)
            node.append_child(rpar)

        yield from self.visit_default(node)

    def visit_INDENT(self, node: Leaf) -> Iterator[Line]:
        """Increase indentation level, maybe yield a line."""
        # In blib2to3 INDENT never holds comments.
        yield from self.line(+1)
        yield from self.visit_default(node)

    def visit_DEDENT(self, node: Leaf) -> Iterator[Line]:
        """Decrease indentation level, maybe yield a line."""
        # The current line might still wait for trailing comments.  At DEDENT time
        # there won't be any (they would be prefixes on the preceding NEWLINE).
        # Emit the line then.
        yield from self.line()

        # While DEDENT has no value, its prefix may contain standalone comments
        # that belong to the current indentation level.  Get 'em.
        yield from self.visit_default(node)

        # Finally, emit the dedent.
        yield from self.line(-1)

    def visit_stmt(
        self, node: Node, keywords: Set[str], parens: Set[str]
    ) -> Iterator[Line]:
        """Visit a statement.

        This implementation is shared for `if`, `while`, `for`, `try`, `except`,
        `def`, `with`, `class`, `assert`, and assignments.

        The relevant Python language `keywords` for a given statement will be
        NAME leaves within it. This methods puts those on a separate line.

        `parens` holds a set of string leaf values immediately after which
        invisible parens should be put.
        """
        normalize_invisible_parens(
            node, parens_after=parens, mode=self.mode, features=self.features
        )
        for child in node.children:
            if is_name_token(child) and child.value in keywords:
                yield from self.line()

            yield from self.visit(child)

    def visit_typeparams(self, node: Node) -> Iterator[Line]:
        yield from self.visit_default(node)
        node.children[0].prefix = ""

    def visit_typevartuple(self, node: Node) -> Iterator[Line]:
        yield from self.visit_default(node)
        node.children[1].prefix = ""

    def visit_paramspec(self, node: Node) -> Iterator[Line]:
        yield from self.visit_default(node)
        node.children[1].prefix = ""

    def visit_dictsetmaker(self, node: Node) -> Iterator[Line]:
        if Preview.wrap_long_dict_values_in_parens in self.mode:
            for i, child in enumerate(node.children):
                if i == 0:
                    continue
                if node.children[i - 1].type == token.COLON:
                    if (
                        child.type == syms.atom
                        and child.children[0].type in OPENING_BRACKETS
                        and not is_walrus_assignment(child)
                    ):
                        maybe_make_parens_invisible_in_atom(
                            child,
                            parent=node,
                            remove_brackets_around_comma=False,
                        )
                    else:
                        wrap_in_parentheses(node, child, visible=False)
        yield from self.visit_default(node)

    def visit_funcdef(self, node: Node) -> Iterator[Line]:
        """Visit function definition."""
        yield from self.line()

        # Remove redundant brackets around return type annotation.
        is_return_annotation = False
        for child in node.children:
            if child.type == token.RARROW:
                is_return_annotation = True
            elif is_return_annotation:
                if child.type == syms.atom and child.children[0].type == token.LPAR:
                    if maybe_make_parens_invisible_in_atom(
                        child,
                        parent=node,
                        remove_brackets_around_comma=False,
                    ):
                        wrap_in_parentheses(node, child, visible=False)
                else:
                    wrap_in_parentheses(node, child, visible=False)
                is_return_annotation = False

        for child in node.children:
            yield from self.visit(child)

    def visit_match_case(self, node: Node) -> Iterator[Line]:
        """Visit either a match or case statement."""
        normalize_invisible_parens(
            node, parens_after=set(), mode=self.mode, features=self.features
        )

        yield from self.line()
        for child in node.children:
            yield from self.visit(child)

    def visit_suite(self, node: Node) -> Iterator[Line]:
        """Visit a suite."""
        if is_stub_suite(node):
            yield from self.visit(node.children[2])
        else:
            yield from self.visit_default(node)

    def visit_simple_stmt(self, node: Node) -> Iterator[Line]:
        """Visit a statement without nested statements."""
        prev_type: Optional[int] = None
        for child in node.children:
            if (prev_type is None or prev_type == token.SEMI) and is_arith_like(child):
                wrap_in_parentheses(node, child, visible=False)
            prev_type = child.type

        if node.parent and node.parent.type in STATEMENT:
            if is_parent_function_or_class(node) and is_stub_body(node):
                yield from self.visit_default(node)
            else:
                yield from self.line(+1)
                yield from self.visit_default(node)
                yield from self.line(-1)

        else:
            if node.parent and is_stub_suite(node.parent):
                node.prefix = ""
                yield from self.visit_default(node)
                return
            yield from self.line()
            yield from self.visit_default(node)

    def visit_async_stmt(self, node: Node) -> Iterator[Line]:
        """Visit `async def`, `async for`, `async with`."""
        yield from self.line()

        children = iter(node.children)
        for child in children:
            yield from self.visit(child)

            if child.type == token.ASYNC or child.type == STANDALONE_COMMENT:
                # STANDALONE_COMMENT happens when `# fmt: skip` is applied on the async
                # line.
                break

        internal_stmt = next(children)
        yield from self.visit(internal_stmt)

    def visit_decorators(self, node: Node) -> Iterator[Line]:
        """Visit decorators."""
        for child in node.children:
            yield from self.line()
            yield from self.visit(child)

    def visit_power(self, node: Node) -> Iterator[Line]:
        for idx, leaf in enumerate(node.children[:-1]):
            next_leaf = node.children[idx + 1]

            if not isinstance(leaf, Leaf):
                continue

            value = leaf.value.lower()
            if (
                leaf.type == token.NUMBER
                and next_leaf.type == syms.trailer
                # Ensure that we are in an attribute trailer
                and next_leaf.children[0].type == token.DOT
                # It shouldn't wrap hexadecimal, binary and octal literals
                and not value.startswith(("0x", "0b", "0o"))
                # It shouldn't wrap complex literals
                and "j" not in value
            ):
                wrap_in_parentheses(node, leaf)

        remove_await_parens(node)

        yield from self.visit_default(node)

    def visit_SEMI(self, leaf: Leaf) -> Iterator[Line]:
        """Remove a semicolon and put the other statement on a separate line."""
        yield from self.line()

    def visit_ENDMARKER(self, leaf: Leaf) -> Iterator[Line]:
        """End of file. Process outstanding comments and end with a newline."""
        yield from self.visit_default(leaf)
        yield from self.line()

    def visit_STANDALONE_COMMENT(self, leaf: Leaf) -> Iterator[Line]:
        if not self.current_line.bracket_tracker.any_open_brackets():
            yield from self.line()
        yield from self.visit_default(leaf)

    def visit_factor(self, node: Node) -> Iterator[Line]:
        """Force parentheses between a unary op and a binary power:

        -2 ** 8 -> -(2 ** 8)
        """
        _operator, operand = node.children
        if (
            operand.type == syms.power
            and len(operand.children) == 3
            and operand.children[1].type == token.DOUBLESTAR
        ):
            lpar = Leaf(token.LPAR, "(")
            rpar = Leaf(token.RPAR, ")")
            index = operand.remove() or 0
            node.insert_child(index, Node(syms.atom, [lpar, operand, rpar]))
        yield from self.visit_default(node)

    def visit_tname(self, node: Node) -> Iterator[Line]:
        """
        Add potential parentheses around types in function parameter lists to be made
        into real parentheses in case the type hint is too long to fit on a line
        Examples:
        def foo(a: int, b: float = 7): ...

        ->

        def foo(a: (int), b: (float) = 7): ...
        """
        assert len(node.children) == 3
        if maybe_make_parens_invisible_in_atom(node.children[2], parent=node):
            wrap_in_parentheses(node, node.children[2], visible=False)

        yield from self.visit_default(node)

    def visit_STRING(self, leaf: Leaf) -> Iterator[Line]:
        if Preview.hex_codes_in_unicode_sequences in self.mode:
            normalize_unicode_escape_sequences(leaf)

        if is_docstring(leaf, self.mode) and not re.search(r"\\\s*\n", leaf.value):
            # We're ignoring docstrings with backslash newline escapes because changing
            # indentation of those changes the AST representation of the code.
            if self.mode.string_normalization:
                docstring = normalize_string_prefix(leaf.value)
                # We handle string normalization at the end of this method, but since
                # what we do right now acts differently depending on quote style (ex.
                # see padding logic below), there's a possibility for unstable
                # formatting. To avoid a situation where this function formats a
                # docstring differently on the second pass, normalize it early.
                docstring = normalize_string_quotes(docstring)
            else:
                docstring = leaf.value
            prefix = get_string_prefix(docstring)
            docstring = docstring[len(prefix) :]  # Remove the prefix
            quote_char = docstring[0]
            # A natural way to remove the outer quotes is to do:
            #   docstring = docstring.strip(quote_char)
            # but that breaks on """""x""" (which is '""x').
            # So we actually need to remove the first character and the next two
            # characters but only if they are the same as the first.
            quote_len = 1 if docstring[1] != quote_char else 3
            docstring = docstring[quote_len:-quote_len]
            docstring_started_empty = not docstring
            indent = " " * 4 * self.current_line.depth

            if is_multiline_string(leaf):
                docstring = fix_docstring(docstring, indent)
            else:
                docstring = docstring.strip()

            has_trailing_backslash = False
            if docstring:
                # Add some padding if the docstring starts / ends with a quote mark.
                if docstring[0] == quote_char:
                    docstring = " " + docstring
                if docstring[-1] == quote_char:
                    docstring += " "
                if docstring[-1] == "\\":
                    backslash_count = len(docstring) - len(docstring.rstrip("\\"))
                    if backslash_count % 2:
                        # Odd number of tailing backslashes, add some padding to
                        # avoid escaping the closing string quote.
                        docstring += " "
                        has_trailing_backslash = True
            elif not docstring_started_empty:
                docstring = " "

            # We could enforce triple quotes at this point.
            quote = quote_char * quote_len

            # It's invalid to put closing single-character quotes on a new line.
            if quote_len == 3:
                # We need to find the length of the last line of the docstring
                # to find if we can add the closing quotes to the line without
                # exceeding the maximum line length.
                # If docstring is one line, we don't put the closing quotes on a
                # separate line because it looks ugly (#3320).
                lines = docstring.splitlines()
                last_line_length = len(lines[-1]) if docstring else 0

                # If adding closing quotes would cause the last line to exceed
                # the maximum line length, and the closing quote is not
                # prefixed by a newline then put a line break before
                # the closing quotes
                if (
                    len(lines) > 1
                    and last_line_length + quote_len > self.mode.line_length
                    and len(indent) + quote_len <= self.mode.line_length
                    and not has_trailing_backslash
                ):
                    if (
                        Preview.docstring_check_for_newline in self.mode
                        and leaf.value[-1 - quote_len] == "\n"
                    ):
                        leaf.value = prefix + quote + docstring + quote
                    else:
                        leaf.value = prefix + quote + docstring + "\n" + indent + quote
                else:
                    leaf.value = prefix + quote + docstring + quote
            else:
                leaf.value = prefix + quote + docstring + quote

        if self.mode.string_normalization and leaf.type == token.STRING:
            leaf.value = normalize_string_prefix(leaf.value)
            leaf.value = normalize_string_quotes(leaf.value)
        yield from self.visit_default(leaf)

    def visit_NUMBER(self, leaf: Leaf) -> Iterator[Line]:
        normalize_numeric_literal(leaf)
        yield from self.visit_default(leaf)

    def visit_fstring(self, node: Node) -> Iterator[Line]:
        # currently we don't want to format and split f-strings at all.
        string_leaf = fstring_to_string(node)
        node.replace(string_leaf)
        yield from self.visit_STRING(string_leaf)

        # TODO: Uncomment Implementation to format f-string children
        # fstring_start = node.children[0]
        # fstring_end = node.children[-1]
        # assert isinstance(fstring_start, Leaf)
        # assert isinstance(fstring_end, Leaf)

        # quote_char = fstring_end.value[0]
        # quote_idx = fstring_start.value.index(quote_char)
        # prefix, quote = (
        #     fstring_start.value[:quote_idx],
        #     fstring_start.value[quote_idx:]
        # )

        # if not is_docstring(node, self.mode):
        #     prefix = normalize_string_prefix(prefix)

        # assert quote == fstring_end.value

        # is_raw_fstring = "r" in prefix or "R" in prefix
        # middles = [
        #     leaf
        #     for leaf in node.leaves()
        #     if leaf.type == token.FSTRING_MIDDLE
        # ]

        # if self.mode.string_normalization:
        #     middles, quote = normalize_fstring_quotes(quote, middles, is_raw_fstring)

        # fstring_start.value = prefix + quote
        # fstring_end.value = quote

        # yield from self.visit_default(node)

    def __post_init__(self) -> None:
        """You are in a twisty little maze of passages."""
        self.current_line = Line(mode=self.mode)

        v = self.visit_stmt
        Ø: Set[str] = set()
        self.visit_assert_stmt = partial(v, keywords={"assert"}, parens={"assert", ","})
        self.visit_if_stmt = partial(
            v, keywords={"if", "else", "elif"}, parens={"if", "elif"}
        )
        self.visit_while_stmt = partial(v, keywords={"while", "else"}, parens={"while"})
        self.visit_for_stmt = partial(v, keywords={"for", "else"}, parens={"for", "in"})
        self.visit_try_stmt = partial(
            v, keywords={"try", "except", "else", "finally"}, parens=Ø
        )
        self.visit_except_clause = partial(v, keywords={"except"}, parens={"except"})
        self.visit_with_stmt = partial(v, keywords={"with"}, parens={"with"})
        self.visit_classdef = partial(v, keywords={"class"}, parens=Ø)

        self.visit_expr_stmt = partial(v, keywords=Ø, parens=ASSIGNMENTS)
        self.visit_return_stmt = partial(v, keywords={"return"}, parens={"return"})
        self.visit_import_from = partial(v, keywords=Ø, parens={"import"})
        self.visit_del_stmt = partial(v, keywords=Ø, parens={"del"})
        self.visit_async_funcdef = self.visit_async_stmt
        self.visit_decorated = self.visit_decorators

        # PEP 634
        self.visit_match_stmt = self.visit_match_case
        self.visit_case_block = self.visit_match_case
        if Preview.remove_redundant_guard_parens in self.mode:
            self.visit_guard = partial(v, keywords=Ø, parens={"if"})


def _hugging_power_ops_line_to_string(
    line: Line,
    features: Collection[Feature],
    mode: Mode,
) -> Optional[str]:
    try:
        return line_to_string(next(hug_power_op(line, features, mode)))
    except CannotTransform:
        return None


def transform_line(
    line: Line, mode: Mode, features: Collection[Feature] = ()
) -> Iterator[Line]:
    """Transform a `line`, potentially splitting it into many lines.

    They should fit in the allotted `line_length` but might not be able to.

    `features` are syntactical features that may be used in the output.
    """
    if line.is_comment:
        yield line
        return

    line_str = line_to_string(line)

    # We need the line string when power operators are hugging to determine if we should
    # split the line. Default to line_str, if no power operator are present on the line.
    line_str_hugging_power_ops = (
        _hugging_power_ops_line_to_string(line, features, mode) or line_str
    )

    ll = mode.line_length
    sn = mode.string_normalization
    string_merge = StringMerger(ll, sn)
    string_paren_strip = StringParenStripper(ll, sn)
    string_split = StringSplitter(ll, sn)
    string_paren_wrap = StringParenWrapper(ll, sn)

    transformers: List[Transformer]
    if (
        not line.contains_uncollapsable_type_comments()
        and not line.should_split_rhs
        and not line.magic_trailing_comma
        and (
            is_line_short_enough(line, mode=mode, line_str=line_str_hugging_power_ops)
            or line.contains_unsplittable_type_ignore()
        )
        and not (line.inside_brackets and line.contains_standalone_comments())
        and not line.contains_implicit_multiline_string_with_comments()
    ):
        # Only apply basic string preprocessing, since lines shouldn't be split here.
        if Preview.string_processing in mode:
            transformers = [string_merge, string_paren_strip]
        else:
            transformers = []
    elif line.is_def and not should_split_funcdef_with_rhs(line, mode):
        transformers = [left_hand_split]
    else:

        def _rhs(
            self: object, line: Line, features: Collection[Feature], mode: Mode
        ) -> Iterator[Line]:
            """Wraps calls to `right_hand_split`.

            The calls increasingly `omit` right-hand trailers (bracket pairs with
            content), meaning the trailers get glued together to split on another
            bracket pair instead.
            """
            for omit in generate_trailers_to_omit(line, mode.line_length):
                lines = list(right_hand_split(line, mode, features, omit=omit))
                # Note: this check is only able to figure out if the first line of the
                # *current* transformation fits in the line length.  This is true only
                # for simple cases.  All others require running more transforms via
                # `transform_line()`.  This check doesn't know if those would succeed.
                if is_line_short_enough(lines[0], mode=mode):
                    yield from lines
                    return

            # All splits failed, best effort split with no omits.
            # This mostly happens to multiline strings that are by definition
            # reported as not fitting a single line, as well as lines that contain
            # trailing commas (those have to be exploded).
            yield from right_hand_split(line, mode, features=features)

        # HACK: nested functions (like _rhs) compiled by mypyc don't retain their
        # __name__ attribute which is needed in `run_transformer` further down.
        # Unfortunately a nested class breaks mypyc too. So a class must be created
        # via type ... https://github.com/mypyc/mypyc/issues/884
        rhs = type("rhs", (), {"__call__": _rhs})()

        if Preview.string_processing in mode:
            if line.inside_brackets:
                transformers = [
                    string_merge,
                    string_paren_strip,
                    string_split,
                    delimiter_split,
                    standalone_comment_split,
                    string_paren_wrap,
                    rhs,
                ]
            else:
                transformers = [
                    string_merge,
                    string_paren_strip,
                    string_split,
                    string_paren_wrap,
                    rhs,
                ]
        else:
            if line.inside_brackets:
                transformers = [delimiter_split, standalone_comment_split, rhs]
            else:
                transformers = [rhs]
    # It's always safe to attempt hugging of power operations and pretty much every line
    # could match.
    transformers.append(hug_power_op)

    for transform in transformers:
        # We are accumulating lines in `result` because we might want to abort
        # mission and return the original line in the end, or attempt a different
        # split altogether.
        try:
            result = run_transformer(line, transform, mode, features, line_str=line_str)
        except CannotTransform:
            continue
        else:
            yield from result
            break

    else:
        yield line


def should_split_funcdef_with_rhs(line: Line, mode: Mode) -> bool:
    """If a funcdef has a magic trailing comma in the return type, then we should first
    split the line with rhs to respect the comma.
    """
    return_type_leaves: List[Leaf] = []
    in_return_type = False

    for leaf in line.leaves:
        if leaf.type == token.COLON:
            in_return_type = False
        if in_return_type:
            return_type_leaves.append(leaf)
        if leaf.type == token.RARROW:
            in_return_type = True

    # using `bracket_split_build_line` will mess with whitespace, so we duplicate a
    # couple lines from it.
    result = Line(mode=line.mode, depth=line.depth)
    leaves_to_track = get_leaves_inside_matching_brackets(return_type_leaves)
    for leaf in return_type_leaves:
        result.append(
            leaf,
            preformatted=True,
            track_bracket=id(leaf) in leaves_to_track,
        )

    # we could also return true if the line is too long, and the return type is longer
    # than the param list. Or if `should_split_rhs` returns True.
    return result.magic_trailing_comma is not None


class _BracketSplitComponent(Enum):
    head = auto()
    body = auto()
    tail = auto()


def left_hand_split(
    line: Line, _features: Collection[Feature], mode: Mode
) -> Iterator[Line]:
    """Split line into many lines, starting with the first matching bracket pair.

    Note: this usually looks weird, only use this for function definitions.
    Prefer RHS otherwise.  This is why this function is not symmetrical with
    :func:`right_hand_split` which also handles optional parentheses.
    """
    tail_leaves: List[Leaf] = []
    body_leaves: List[Leaf] = []
    head_leaves: List[Leaf] = []
    current_leaves = head_leaves
    matching_bracket: Optional[Leaf] = None
    for leaf in line.leaves:
        if (
            current_leaves is body_leaves
            and leaf.type in CLOSING_BRACKETS
            and leaf.opening_bracket is matching_bracket
            and isinstance(matching_bracket, Leaf)
        ):
            ensure_visible(leaf)
            ensure_visible(matching_bracket)
            current_leaves = tail_leaves if body_leaves else head_leaves
        current_leaves.append(leaf)
        if current_leaves is head_leaves:
            if leaf.type in OPENING_BRACKETS:
                matching_bracket = leaf
                current_leaves = body_leaves
    if not matching_bracket or not tail_leaves:
        raise CannotSplit("No brackets found")

    head = bracket_split_build_line(
        head_leaves, line, matching_bracket, component=_BracketSplitComponent.head
    )
    body = bracket_split_build_line(
        body_leaves, line, matching_bracket, component=_BracketSplitComponent.body
    )
    tail = bracket_split_build_line(
        tail_leaves, line, matching_bracket, component=_BracketSplitComponent.tail
    )
    bracket_split_succeeded_or_raise(head, body, tail)
    for result in (head, body, tail):
        if result:
            yield result


def right_hand_split(
    line: Line,
    mode: Mode,
    features: Collection[Feature] = (),
    omit: Collection[LeafID] = (),
) -> Iterator[Line]:
    """Split line into many lines, starting with the last matching bracket pair.

    If the split was by optional parentheses, attempt splitting without them, too.
    `omit` is a collection of closing bracket IDs that shouldn't be considered for
    this split.

    Note: running this function modifies `bracket_depth` on the leaves of `line`.
    """
    rhs_result = _first_right_hand_split(line, omit=omit)
    yield from _maybe_split_omitting_optional_parens(
        rhs_result, line, mode, features=features, omit=omit
    )


def _first_right_hand_split(
    line: Line,
    omit: Collection[LeafID] = (),
) -> RHSResult:
    """Split the line into head, body, tail starting with the last bracket pair.

    Note: this function should not have side effects. It's relied upon by
    _maybe_split_omitting_optional_parens to get an opinion whether to prefer
    splitting on the right side of an assignment statement.
    """
    tail_leaves: List[Leaf] = []
    body_leaves: List[Leaf] = []
    head_leaves: List[Leaf] = []
    current_leaves = tail_leaves
    opening_bracket: Optional[Leaf] = None
    closing_bracket: Optional[Leaf] = None
    for leaf in reversed(line.leaves):
        if current_leaves is body_leaves:
            if leaf is opening_bracket:
                current_leaves = head_leaves if body_leaves else tail_leaves
        current_leaves.append(leaf)
        if current_leaves is tail_leaves:
            if leaf.type in CLOSING_BRACKETS and id(leaf) not in omit:
                opening_bracket = leaf.opening_bracket
                closing_bracket = leaf
                current_leaves = body_leaves
    if not (opening_bracket and closing_bracket and head_leaves):
        # If there is no opening or closing_bracket that means the split failed and
        # all content is in the tail.  Otherwise, if `head_leaves` are empty, it means
        # the matching `opening_bracket` wasn't available on `line` anymore.
        raise CannotSplit("No brackets found")

    tail_leaves.reverse()
    body_leaves.reverse()
    head_leaves.reverse()

    body: Optional[Line] = None
    if (
        Preview.hug_parens_with_braces_and_square_brackets in line.mode
        and tail_leaves[0].value
        and tail_leaves[0].opening_bracket is head_leaves[-1]
    ):
        inner_body_leaves = list(body_leaves)
        hugged_opening_leaves: List[Leaf] = []
        hugged_closing_leaves: List[Leaf] = []
        is_unpacking = body_leaves[0].type in [token.STAR, token.DOUBLESTAR]
        unpacking_offset: int = 1 if is_unpacking else 0
        while (
            len(inner_body_leaves) >= 2 + unpacking_offset
            and inner_body_leaves[-1].type in CLOSING_BRACKETS
            and inner_body_leaves[-1].opening_bracket
            is inner_body_leaves[unpacking_offset]
        ):
            if unpacking_offset:
                hugged_opening_leaves.append(inner_body_leaves.pop(0))
                unpacking_offset = 0
            hugged_opening_leaves.append(inner_body_leaves.pop(0))
            hugged_closing_leaves.insert(0, inner_body_leaves.pop())

        if hugged_opening_leaves and inner_body_leaves:
            inner_body = bracket_split_build_line(
                inner_body_leaves,
                line,
                hugged_opening_leaves[-1],
                component=_BracketSplitComponent.body,
            )
            if (
                line.mode.magic_trailing_comma
                and inner_body_leaves[-1].type == token.COMMA
            ):
                should_hug = True
            else:
                line_length = line.mode.line_length - sum(
                    len(str(leaf))
                    for leaf in hugged_opening_leaves + hugged_closing_leaves
                )
                if is_line_short_enough(
                    inner_body, mode=replace(line.mode, line_length=line_length)
                ):
                    # Do not hug if it fits on a single line.
                    should_hug = False
                else:
                    should_hug = True
            if should_hug:
                body_leaves = inner_body_leaves
                head_leaves.extend(hugged_opening_leaves)
                tail_leaves = hugged_closing_leaves + tail_leaves
                body = inner_body  # No need to re-calculate the body again later.

    head = bracket_split_build_line(
        head_leaves, line, opening_bracket, component=_BracketSplitComponent.head
    )
    if body is None:
        body = bracket_split_build_line(
            body_leaves, line, opening_bracket, component=_BracketSplitComponent.body
        )
    tail = bracket_split_build_line(
        tail_leaves, line, opening_bracket, component=_BracketSplitComponent.tail
    )
    bracket_split_succeeded_or_raise(head, body, tail)
    return RHSResult(head, body, tail, opening_bracket, closing_bracket)


def _maybe_split_omitting_optional_parens(
    rhs: RHSResult,
    line: Line,
    mode: Mode,
    features: Collection[Feature] = (),
    omit: Collection[LeafID] = (),
) -> Iterator[Line]:
    if (
        Feature.FORCE_OPTIONAL_PARENTHESES not in features
        # the opening bracket is an optional paren
        and rhs.opening_bracket.type == token.LPAR
        and not rhs.opening_bracket.value
        # the closing bracket is an optional paren
        and rhs.closing_bracket.type == token.RPAR
        and not rhs.closing_bracket.value
        # it's not an import (optional parens are the only thing we can split on
        # in this case; attempting a split without them is a waste of time)
        and not line.is_import
        # and we can actually remove the parens
        and can_omit_invisible_parens(rhs, mode.line_length)
    ):
        omit = {id(rhs.closing_bracket), *omit}
        try:
            # The RHSResult Omitting Optional Parens.
            rhs_oop = _first_right_hand_split(line, omit=omit)
            is_split_right_after_equal = (
                len(rhs.head.leaves) >= 2 and rhs.head.leaves[-2].type == token.EQUAL
            )
            rhs_head_contains_brackets = any(
                leaf.type in BRACKETS for leaf in rhs.head.leaves[:-1]
            )
            # the -1 is for the ending optional paren
            rhs_head_short_enough = is_line_short_enough(
                rhs.head, mode=replace(mode, line_length=mode.line_length - 1)
            )
            rhs_head_explode_blocked_by_magic_trailing_comma = (
                rhs.head.magic_trailing_comma is None
            )
            if (
                not (
                    is_split_right_after_equal
                    and rhs_head_contains_brackets
                    and rhs_head_short_enough
                    and rhs_head_explode_blocked_by_magic_trailing_comma
                )
                # the omit optional parens split is preferred by some other reason
                or _prefer_split_rhs_oop_over_rhs(rhs_oop, rhs, mode)
            ):
                yield from _maybe_split_omitting_optional_parens(
                    rhs_oop, line, mode, features=features, omit=omit
                )
                return

        except CannotSplit as e:
            # For chained assignments we want to use the previous successful split
            if line.is_chained_assignment:
                pass

            elif not can_be_split(rhs.body) and not is_line_short_enough(
                rhs.body, mode=mode
            ):
                raise CannotSplit(
                    "Splitting failed, body is still too long and can't be split."
                ) from e

            elif (
                rhs.head.contains_multiline_strings()
                or rhs.tail.contains_multiline_strings()
            ):
                raise CannotSplit(
                    "The current optional pair of parentheses is bound to fail to"
                    " satisfy the splitting algorithm because the head or the tail"
                    " contains multiline strings which by definition never fit one"
                    " line."
                ) from e

    ensure_visible(rhs.opening_bracket)
    ensure_visible(rhs.closing_bracket)
    for result in (rhs.head, rhs.body, rhs.tail):
        if result:
            yield result


def _prefer_split_rhs_oop_over_rhs(
    rhs_oop: RHSResult, rhs: RHSResult, mode: Mode
) -> bool:
    """
    Returns whether we should prefer the result from a split omitting optional parens
    (rhs_oop) over the original (rhs).
    """
    # If we have multiple targets, we prefer more `=`s on the head vs pushing them to
    # the body
    rhs_head_equal_count = [leaf.type for leaf in rhs.head.leaves].count(token.EQUAL)
    rhs_oop_head_equal_count = [leaf.type for leaf in rhs_oop.head.leaves].count(
        token.EQUAL
    )
    if rhs_head_equal_count > 1 and rhs_head_equal_count > rhs_oop_head_equal_count:
        return False

    has_closing_bracket_after_assign = False
    for leaf in reversed(rhs_oop.head.leaves):
        if leaf.type == token.EQUAL:
            break
        if leaf.type in CLOSING_BRACKETS:
            has_closing_bracket_after_assign = True
            break
    return (
        # contains matching brackets after the `=` (done by checking there is a
        # closing bracket)
        has_closing_bracket_after_assign
        or (
            # the split is actually from inside the optional parens (done by checking
            # the first line still contains the `=`)
            any(leaf.type == token.EQUAL for leaf in rhs_oop.head.leaves)
            # the first line is short enough
            and is_line_short_enough(rhs_oop.head, mode=mode)
        )
        # contains unsplittable type ignore
        or rhs_oop.head.contains_unsplittable_type_ignore()
        or rhs_oop.body.contains_unsplittable_type_ignore()
        or rhs_oop.tail.contains_unsplittable_type_ignore()
    )


def bracket_split_succeeded_or_raise(head: Line, body: Line, tail: Line) -> None:
    """Raise :exc:`CannotSplit` if the last left- or right-hand split failed.

    Do nothing otherwise.

    A left- or right-hand split is based on a pair of brackets. Content before
    (and including) the opening bracket is left on one line, content inside the
    brackets is put on a separate line, and finally content starting with and
    following the closing bracket is put on a separate line.

    Those are called `head`, `body`, and `tail`, respectively. If the split
    produced the same line (all content in `head`) or ended up with an empty `body`
    and the `tail` is just the closing bracket, then it's considered failed.
    """
    tail_len = len(str(tail).strip())
    if not body:
        if tail_len == 0:
            raise CannotSplit("Splitting brackets produced the same line")

        elif tail_len < 3:
            raise CannotSplit(
                f"Splitting brackets on an empty body to save {tail_len} characters is"
                " not worth it"
            )


def bracket_split_build_line(
    leaves: List[Leaf],
    original: Line,
    opening_bracket: Leaf,
    *,
    component: _BracketSplitComponent,
) -> Line:
    """Return a new line with given `leaves` and respective comments from `original`.

    If it's the head component, brackets will be tracked so trailing commas are
    respected.

    If it's the body component, the result line is one-indented inside brackets and as
    such has its first leaf's prefix normalized and a trailing comma added when
    expected.
    """
    result = Line(mode=original.mode, depth=original.depth)
    if component is _BracketSplitComponent.body:
        result.inside_brackets = True
        result.depth += 1
        if leaves:
            no_commas = (
                # Ensure a trailing comma for imports and standalone function arguments
                original.is_def
                # Don't add one after any comments or within type annotations
                and opening_bracket.value == "("
                # Don't add one if there's already one there
                and not any(
                    leaf.type == token.COMMA
                    and (
                        Preview.typed_params_trailing_comma not in original.mode
                        or not is_part_of_annotation(leaf)
                    )
                    for leaf in leaves
                )
                # Don't add one inside parenthesized return annotations
                and get_annotation_type(leaves[0]) != "return"
                # Don't add one inside PEP 604 unions
                and not (
                    leaves[0].parent
                    and leaves[0].parent.next_sibling
                    and leaves[0].parent.next_sibling.type == token.VBAR
                )
            )

            if original.is_import or no_commas:
                for i in range(len(leaves) - 1, -1, -1):
                    if leaves[i].type == STANDALONE_COMMENT:
                        continue

                    if leaves[i].type != token.COMMA:
                        new_comma = Leaf(token.COMMA, ",")
                        leaves.insert(i + 1, new_comma)
                    break

    leaves_to_track: Set[LeafID] = set()
    if component is _BracketSplitComponent.head:
        leaves_to_track = get_leaves_inside_matching_brackets(leaves)
    # Populate the line
    for leaf in leaves:
        result.append(
            leaf,
            preformatted=True,
            track_bracket=id(leaf) in leaves_to_track,
        )
        for comment_after in original.comments_after(leaf):
            result.append(comment_after, preformatted=True)
    if component is _BracketSplitComponent.body and should_split_line(
        result, opening_bracket
    ):
        result.should_split_rhs = True
    return result


def dont_increase_indentation(split_func: Transformer) -> Transformer:
    """Normalize prefix of the first leaf in every line returned by `split_func`.

    This is a decorator over relevant split functions.
    """

    @wraps(split_func)
    def split_wrapper(
        line: Line, features: Collection[Feature], mode: Mode
    ) -> Iterator[Line]:
        for split_line in split_func(line, features, mode):
            split_line.leaves[0].prefix = ""
            yield split_line

    return split_wrapper


def _get_last_non_comment_leaf(line: Line) -> Optional[int]:
    for leaf_idx in range(len(line.leaves) - 1, 0, -1):
        if line.leaves[leaf_idx].type != STANDALONE_COMMENT:
            return leaf_idx
    return None


def _can_add_trailing_comma(leaf: Leaf, features: Collection[Feature]) -> bool:
    if is_vararg(leaf, within={syms.typedargslist}):
        return Feature.TRAILING_COMMA_IN_DEF in features
    if is_vararg(leaf, within={syms.arglist, syms.argument}):
        return Feature.TRAILING_COMMA_IN_CALL in features
    return True


def _safe_add_trailing_comma(safe: bool, delimiter_priority: int, line: Line) -> Line:
    if (
        safe
        and delimiter_priority == COMMA_PRIORITY
        and line.leaves[-1].type != token.COMMA
        and line.leaves[-1].type != STANDALONE_COMMENT
    ):
        new_comma = Leaf(token.COMMA, ",")
        line.append(new_comma)
    return line


MIGRATE_COMMENT_DELIMITERS = {STRING_PRIORITY, COMMA_PRIORITY}


@dont_increase_indentation
def delimiter_split(
    line: Line, features: Collection[Feature], mode: Mode
) -> Iterator[Line]:
    """Split according to delimiters of the highest priority.

    If the appropriate Features are given, the split will add trailing commas
    also in function signatures and calls that contain `*` and `**`.
    """
    if len(line.leaves) == 0:
        raise CannotSplit("Line empty") from None
    last_leaf = line.leaves[-1]

    bt = line.bracket_tracker
    try:
        delimiter_priority = bt.max_delimiter_priority(exclude={id(last_leaf)})
    except ValueError:
        raise CannotSplit("No delimiters found") from None

    if (
        delimiter_priority == DOT_PRIORITY
        and bt.delimiter_count_with_priority(delimiter_priority) == 1
    ):
        raise CannotSplit("Splitting a single attribute from its owner looks wrong")

    current_line = Line(
        mode=line.mode, depth=line.depth, inside_brackets=line.inside_brackets
    )
    lowest_depth = sys.maxsize
    trailing_comma_safe = True

    def append_to_line(leaf: Leaf) -> Iterator[Line]:
        """Append `leaf` to current line or to new line if appending impossible."""
        nonlocal current_line
        try:
            current_line.append_safe(leaf, preformatted=True)
        except ValueError:
            yield current_line

            current_line = Line(
                mode=line.mode, depth=line.depth, inside_brackets=line.inside_brackets
            )
            current_line.append(leaf)

    def append_comments(leaf: Leaf) -> Iterator[Line]:
        for comment_after in line.comments_after(leaf):
            yield from append_to_line(comment_after)

    last_non_comment_leaf = _get_last_non_comment_leaf(line)
    for leaf_idx, leaf in enumerate(line.leaves):
        yield from append_to_line(leaf)

        previous_priority = leaf_idx > 0 and bt.delimiters.get(
            id(line.leaves[leaf_idx - 1])
        )
        if (
            previous_priority != delimiter_priority
            or delimiter_priority in MIGRATE_COMMENT_DELIMITERS
        ):
            yield from append_comments(leaf)

        lowest_depth = min(lowest_depth, leaf.bracket_depth)
        if trailing_comma_safe and leaf.bracket_depth == lowest_depth:
            trailing_comma_safe = _can_add_trailing_comma(leaf, features)

        if last_leaf.type == STANDALONE_COMMENT and leaf_idx == last_non_comment_leaf:
            current_line = _safe_add_trailing_comma(
                trailing_comma_safe, delimiter_priority, current_line
            )

        leaf_priority = bt.delimiters.get(id(leaf))
        if leaf_priority == delimiter_priority:
            if (
                leaf_idx + 1 < len(line.leaves)
                and delimiter_priority not in MIGRATE_COMMENT_DELIMITERS
            ):
                yield from append_comments(line.leaves[leaf_idx + 1])

            yield current_line
            current_line = Line(
                mode=line.mode, depth=line.depth, inside_brackets=line.inside_brackets
            )

    if current_line:
        current_line = _safe_add_trailing_comma(
            trailing_comma_safe, delimiter_priority, current_line
        )
        yield current_line


@dont_increase_indentation
def standalone_comment_split(
    line: Line, features: Collection[Feature], mode: Mode
) -> Iterator[Line]:
    """Split standalone comments from the rest of the line."""
    if not line.contains_standalone_comments():
        raise CannotSplit("Line does not have any standalone comments")

    current_line = Line(
        mode=line.mode, depth=line.depth, inside_brackets=line.inside_brackets
    )

    def append_to_line(leaf: Leaf) -> Iterator[Line]:
        """Append `leaf` to current line or to new line if appending impossible."""
        nonlocal current_line
        try:
            current_line.append_safe(leaf, preformatted=True)
        except ValueError:
            yield current_line

            current_line = Line(
                line.mode, depth=line.depth, inside_brackets=line.inside_brackets
            )
            current_line.append(leaf)

    for leaf in line.leaves:
        yield from append_to_line(leaf)

        for comment_after in line.comments_after(leaf):
            yield from append_to_line(comment_after)

    if current_line:
        yield current_line


def normalize_invisible_parens(  # noqa: C901
    node: Node, parens_after: Set[str], *, mode: Mode, features: Collection[Feature]
) -> None:
    """Make existing optional parentheses invisible or create new ones.

    `parens_after` is a set of string leaf values immediately after which parens
    should be put.

    Standardizes on visible parentheses for single-element tuples, and keeps
    existing visible parentheses for other tuples and generator expressions.
    """
    for pc in list_comments(node.prefix, is_endmarker=False):
        if pc.value in FMT_OFF:
            # This `node` has a prefix with `# fmt: off`, don't mess with parens.
            return

    # The multiple context managers grammar has a different pattern, thus this is
    # separate from the for-loop below. This possibly wraps them in invisible parens,
    # and later will be removed in remove_with_parens when needed.
    if node.type == syms.with_stmt:
        _maybe_wrap_cms_in_parens(node, mode, features)

    check_lpar = False
    for index, child in enumerate(list(node.children)):
        # Fixes a bug where invisible parens are not properly stripped from
        # assignment statements that contain type annotations.
        if isinstance(child, Node) and child.type == syms.annassign:
            normalize_invisible_parens(
                child, parens_after=parens_after, mode=mode, features=features
            )

        # Fixes a bug where invisible parens are not properly wrapped around
        # case blocks.
        if isinstance(child, Node) and child.type == syms.case_block:
            normalize_invisible_parens(
                child, parens_after={"case"}, mode=mode, features=features
            )

        # Add parentheses around if guards in case blocks
        if (
            isinstance(child, Node)
            and child.type == syms.guard
            and Preview.parens_for_long_if_clauses_in_case_block in mode
        ):
            normalize_invisible_parens(
                child, parens_after={"if"}, mode=mode, features=features
            )

        # Add parentheses around long tuple unpacking in assignments.
        if (
            index == 0
            and isinstance(child, Node)
            and child.type == syms.testlist_star_expr
        ):
            check_lpar = True

        if check_lpar:
            if (
                child.type == syms.atom
                and node.type == syms.for_stmt
                and isinstance(child.prev_sibling, Leaf)
                and child.prev_sibling.type == token.NAME
                and child.prev_sibling.value == "for"
            ):
                if maybe_make_parens_invisible_in_atom(
                    child,
                    parent=node,
                    remove_brackets_around_comma=True,
                ):
                    wrap_in_parentheses(node, child, visible=False)
            elif isinstance(child, Node) and node.type == syms.with_stmt:
                remove_with_parens(child, node)
            elif child.type == syms.atom:
                if maybe_make_parens_invisible_in_atom(
                    child,
                    parent=node,
                ):
                    wrap_in_parentheses(node, child, visible=False)
            elif is_one_tuple(child):
                wrap_in_parentheses(node, child, visible=True)
            elif node.type == syms.import_from:
                _normalize_import_from(node, child, index)
                break
            elif (
                index == 1
                and child.type == token.STAR
                and node.type == syms.except_clause
            ):
                # In except* (PEP 654), the star is actually part of
                # of the keyword. So we need to skip the insertion of
                # invisible parentheses to work more precisely.
                continue

            elif (
                isinstance(child, Leaf)
                and child.next_sibling is not None
                and child.next_sibling.type == token.COLON
                and child.value == "case"
            ):
                # A special patch for "case case:" scenario, the second occurrence
                # of case will be not parsed as a Python keyword.
                break

            elif not is_multiline_string(child):
                wrap_in_parentheses(node, child, visible=False)

        comma_check = child.type == token.COMMA

        check_lpar = isinstance(child, Leaf) and (
            child.value in parens_after or comma_check
        )


def _normalize_import_from(parent: Node, child: LN, index: int) -> None:
    # "import from" nodes store parentheses directly as part of
    # the statement
    if is_lpar_token(child):
        assert is_rpar_token(parent.children[-1])
        # make parentheses invisible
        child.value = ""
        parent.children[-1].value = ""
    elif child.type != token.STAR:
        # insert invisible parentheses
        parent.insert_child(index, Leaf(token.LPAR, ""))
        parent.append_child(Leaf(token.RPAR, ""))


def remove_await_parens(node: Node) -> None:
    if node.children[0].type == token.AWAIT and len(node.children) > 1:
        if (
            node.children[1].type == syms.atom
            and node.children[1].children[0].type == token.LPAR
        ):
            if maybe_make_parens_invisible_in_atom(
                node.children[1],
                parent=node,
                remove_brackets_around_comma=True,
            ):
                wrap_in_parentheses(node, node.children[1], visible=False)

            # Since await is an expression we shouldn't remove
            # brackets in cases where this would change
            # the AST due to operator precedence.
            # Therefore we only aim to remove brackets around
            # power nodes that aren't also await expressions themselves.
            # https://peps.python.org/pep-0492/#updated-operator-precedence-table
            # N.B. We've still removed any redundant nested brackets though :)
            opening_bracket = cast(Leaf, node.children[1].children[0])
            closing_bracket = cast(Leaf, node.children[1].children[-1])
            bracket_contents = node.children[1].children[1]
            if isinstance(bracket_contents, Node) and (
                bracket_contents.type != syms.power
                or bracket_contents.children[0].type == token.AWAIT
                or any(
                    isinstance(child, Leaf) and child.type == token.DOUBLESTAR
                    for child in bracket_contents.children
                )
            ):
                ensure_visible(opening_bracket)
                ensure_visible(closing_bracket)


def _maybe_wrap_cms_in_parens(
    node: Node, mode: Mode, features: Collection[Feature]
) -> None:
    """When enabled and safe, wrap the multiple context managers in invisible parens.

    It is only safe when `features` contain Feature.PARENTHESIZED_CONTEXT_MANAGERS.
    """
    if (
        Feature.PARENTHESIZED_CONTEXT_MANAGERS not in features
        or len(node.children) <= 2
        # If it's an atom, it's already wrapped in parens.
        or node.children[1].type == syms.atom
    ):
        return
    colon_index: Optional[int] = None
    for i in range(2, len(node.children)):
        if node.children[i].type == token.COLON:
            colon_index = i
            break
    if colon_index is not None:
        lpar = Leaf(token.LPAR, "")
        rpar = Leaf(token.RPAR, "")
        context_managers = node.children[1:colon_index]
        for child in context_managers:
            child.remove()
        # After wrapping, the with_stmt will look like this:
        #   with_stmt
        #     NAME 'with'
        #     atom
        #       LPAR ''
        #       testlist_gexp
        #         ... <-- context_managers
        #       /testlist_gexp
        #       RPAR ''
        #     /atom
        #     COLON ':'
        new_child = Node(
            syms.atom, [lpar, Node(syms.testlist_gexp, context_managers), rpar]
        )
        node.insert_child(1, new_child)


def remove_with_parens(node: Node, parent: Node) -> None:
    """Recursively hide optional parens in `with` statements."""
    # Removing all unnecessary parentheses in with statements in one pass is a tad
    # complex as different variations of bracketed statements result in pretty
    # different parse trees:
    #
    # with (open("file")) as f:                       # this is an asexpr_test
    #     ...
    #
    # with (open("file") as f):                       # this is an atom containing an
    #     ...                                         # asexpr_test
    #
    # with (open("file")) as f, (open("file")) as f:  # this is asexpr_test, COMMA,
    #     ...                                         # asexpr_test
    #
    # with (open("file") as f, open("file") as f):    # an atom containing a
    #     ...                                         # testlist_gexp which then
    #                                                 # contains multiple asexpr_test(s)
    if node.type == syms.atom:
        if maybe_make_parens_invisible_in_atom(
            node,
            parent=parent,
            remove_brackets_around_comma=True,
        ):
            wrap_in_parentheses(parent, node, visible=False)
        if isinstance(node.children[1], Node):
            remove_with_parens(node.children[1], node)
    elif node.type == syms.testlist_gexp:
        for child in node.children:
            if isinstance(child, Node):
                remove_with_parens(child, node)
    elif node.type == syms.asexpr_test and not any(
        leaf.type == token.COLONEQUAL for leaf in node.leaves()
    ):
        if maybe_make_parens_invisible_in_atom(
            node.children[0],
            parent=node,
            remove_brackets_around_comma=True,
        ):
            wrap_in_parentheses(node, node.children[0], visible=False)


def maybe_make_parens_invisible_in_atom(
    node: LN,
    parent: LN,
    remove_brackets_around_comma: bool = False,
) -> bool:
    """If it's safe, make the parens in the atom `node` invisible, recursively.
    Additionally, remove repeated, adjacent invisible parens from the atom `node`
    as they are redundant.

    Returns whether the node should itself be wrapped in invisible parentheses.
    """
    if (
        node.type not in (syms.atom, syms.expr)
        or is_empty_tuple(node)
        or is_one_tuple(node)
        or (is_yield(node) and parent.type != syms.expr_stmt)
        or (
            # This condition tries to prevent removing non-optional brackets
            # around a tuple, however, can be a bit overzealous so we provide
            # and option to skip this check for `for` and `with` statements.
            not remove_brackets_around_comma
            and max_delimiter_priority_in_atom(node) >= COMMA_PRIORITY
        )
        or is_tuple_containing_walrus(node)
    ):
        return False

    if is_walrus_assignment(node):
        if parent.type in [
            syms.annassign,
            syms.expr_stmt,
            syms.assert_stmt,
            syms.return_stmt,
            syms.except_clause,
            syms.funcdef,
            syms.with_stmt,
            syms.tname,
            # these ones aren't useful to end users, but they do please fuzzers
            syms.for_stmt,
            syms.del_stmt,
            syms.for_stmt,
        ]:
            return False

    first = node.children[0]
    last = node.children[-1]
    if is_lpar_token(first) and is_rpar_token(last):
        middle = node.children[1]
        # make parentheses invisible
        if (
            # If the prefix of `middle` includes a type comment with
            # ignore annotation, then we do not remove the parentheses
            not is_type_ignore_comment_string(middle.prefix.strip())
        ):
            first.value = ""
            if first.prefix.strip():
                # Preserve comments before first paren
                middle.prefix = first.prefix + middle.prefix
            last.value = ""
        maybe_make_parens_invisible_in_atom(
            middle,
            parent=parent,
            remove_brackets_around_comma=remove_brackets_around_comma,
        )

        if is_atom_with_invisible_parens(middle):
            # Strip the invisible parens from `middle` by replacing
            # it with the child in-between the invisible parens
            middle.replace(middle.children[1])
            if middle.children[-1].prefix.strip():
                # Preserve comments before last paren
                last.prefix = middle.children[-1].prefix + last.prefix

        return False

    return True


def should_split_line(line: Line, opening_bracket: Leaf) -> bool:
    """Should `line` be immediately split with `delimiter_split()` after RHS?"""

    if not (opening_bracket.parent and opening_bracket.value in "[{("):
        return False

    # We're essentially checking if the body is delimited by commas and there's more
    # than one of them (we're excluding the trailing comma and if the delimiter priority
    # is still commas, that means there's more).
    exclude = set()
    trailing_comma = False
    try:
        last_leaf = line.leaves[-1]
        if last_leaf.type == token.COMMA:
            trailing_comma = True
            exclude.add(id(last_leaf))
        max_priority = line.bracket_tracker.max_delimiter_priority(exclude=exclude)
    except (IndexError, ValueError):
        return False

    return max_priority == COMMA_PRIORITY and (
        (line.mode.magic_trailing_comma and trailing_comma)
        # always explode imports
        or opening_bracket.parent.type in {syms.atom, syms.import_from}
    )


def generate_trailers_to_omit(line: Line, line_length: int) -> Iterator[Set[LeafID]]:
    """Generate sets of closing bracket IDs that should be omitted in a RHS.

    Brackets can be omitted if the entire trailer up to and including
    a preceding closing bracket fits in one line.

    Yielded sets are cumulative (contain results of previous yields, too).  First
    set is empty, unless the line should explode, in which case bracket pairs until
    the one that needs to explode are omitted.
    """

    omit: Set[LeafID] = set()
    if not line.magic_trailing_comma:
        yield omit

    length = 4 * line.depth
    opening_bracket: Optional[Leaf] = None
    closing_bracket: Optional[Leaf] = None
    inner_brackets: Set[LeafID] = set()
    for index, leaf, leaf_length in line.enumerate_with_length(is_reversed=True):
        length += leaf_length
        if length > line_length:
            break

        has_inline_comment = leaf_length > len(leaf.value) + len(leaf.prefix)
        if leaf.type == STANDALONE_COMMENT or has_inline_comment:
            break

        if opening_bracket:
            if leaf is opening_bracket:
                opening_bracket = None
            elif leaf.type in CLOSING_BRACKETS:
                prev = line.leaves[index - 1] if index > 0 else None
                if (
                    prev
                    and prev.type == token.COMMA
                    and leaf.opening_bracket is not None
                    and not is_one_sequence_between(
                        leaf.opening_bracket, leaf, line.leaves
                    )
                ):
                    # Never omit bracket pairs with trailing commas.
                    # We need to explode on those.
                    break

                inner_brackets.add(id(leaf))
        elif leaf.type in CLOSING_BRACKETS:
            prev = line.leaves[index - 1] if index > 0 else None
            if prev and prev.type in OPENING_BRACKETS:
                # Empty brackets would fail a split so treat them as "inner"
                # brackets (e.g. only add them to the `omit` set if another
                # pair of brackets was good enough.
                inner_brackets.add(id(leaf))
                continue

            if closing_bracket:
                omit.add(id(closing_bracket))
                omit.update(inner_brackets)
                inner_brackets.clear()
                yield omit

            if (
                prev
                and prev.type == token.COMMA
                and leaf.opening_bracket is not None
                and not is_one_sequence_between(leaf.opening_bracket, leaf, line.leaves)
            ):
                # Never omit bracket pairs with trailing commas.
                # We need to explode on those.
                break

            if leaf.value:
                opening_bracket = leaf.opening_bracket
                closing_bracket = leaf


def run_transformer(
    line: Line,
    transform: Transformer,
    mode: Mode,
    features: Collection[Feature],
    *,
    line_str: str = "",
) -> List[Line]:
    if not line_str:
        line_str = line_to_string(line)
    result: List[Line] = []
    for transformed_line in transform(line, features, mode):
        if str(transformed_line).strip("\n") == line_str:
            raise CannotTransform("Line transformer returned an unchanged result")

        result.extend(transform_line(transformed_line, mode=mode, features=features))

    features_set = set(features)
    if (
        Feature.FORCE_OPTIONAL_PARENTHESES in features_set
        or transform.__class__.__name__ != "rhs"
        or not line.bracket_tracker.invisible
        or any(bracket.value for bracket in line.bracket_tracker.invisible)
        or line.contains_multiline_strings()
        or result[0].contains_uncollapsable_type_comments()
        or result[0].contains_unsplittable_type_ignore()
        or is_line_short_enough(result[0], mode=mode)
        # If any leaves have no parents (which _can_ occur since
        # `transform(line)` potentially destroys the line's underlying node
        # structure), then we can't proceed. Doing so would cause the below
        # call to `append_leaves()` to fail.
        or any(leaf.parent is None for leaf in line.leaves)
    ):
        return result

    line_copy = line.clone()
    append_leaves(line_copy, line, line.leaves)
    features_fop = features_set | {Feature.FORCE_OPTIONAL_PARENTHESES}
    second_opinion = run_transformer(
        line_copy, transform, mode, features_fop, line_str=line_str
    )
    if all(is_line_short_enough(ln, mode=mode) for ln in second_opinion):
        result = second_opinion
    return result
