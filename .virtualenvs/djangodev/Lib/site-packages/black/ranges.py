"""Functions related to Black's formatting by line ranges feature."""

import difflib
from dataclasses import dataclass
from typing import Collection, Iterator, List, Sequence, Set, Tuple, Union

from black.nodes import (
    LN,
    STANDALONE_COMMENT,
    Leaf,
    Node,
    Visitor,
    first_leaf,
    furthest_ancestor_with_last_leaf,
    last_leaf,
    syms,
)
from blib2to3.pgen2.token import ASYNC, NEWLINE


def parse_line_ranges(line_ranges: Sequence[str]) -> List[Tuple[int, int]]:
    lines: List[Tuple[int, int]] = []
    for lines_str in line_ranges:
        parts = lines_str.split("-")
        if len(parts) != 2:
            raise ValueError(
                "Incorrect --line-ranges format, expect 'START-END', found"
                f" {lines_str!r}"
            )
        try:
            start = int(parts[0])
            end = int(parts[1])
        except ValueError:
            raise ValueError(
                "Incorrect --line-ranges value, expect integer ranges, found"
                f" {lines_str!r}"
            ) from None
        else:
            lines.append((start, end))
    return lines


def is_valid_line_range(lines: Tuple[int, int]) -> bool:
    """Returns whether the line range is valid."""
    return not lines or lines[0] <= lines[1]


def sanitized_lines(
    lines: Collection[Tuple[int, int]], src_contents: str
) -> Collection[Tuple[int, int]]:
    """Returns the valid line ranges for the given source.

    This removes ranges that are entirely outside the valid lines.

    Other ranges are normalized so that the start values are at least 1 and the
    end values are at most the (1-based) index of the last source line.
    """
    if not src_contents:
        return []
    good_lines = []
    src_line_count = src_contents.count("\n")
    if not src_contents.endswith("\n"):
        src_line_count += 1
    for start, end in lines:
        if start > src_line_count:
            continue
        # line-ranges are 1-based
        start = max(start, 1)
        if end < start:
            continue
        end = min(end, src_line_count)
        good_lines.append((start, end))
    return good_lines


def adjusted_lines(
    lines: Collection[Tuple[int, int]],
    original_source: str,
    modified_source: str,
) -> List[Tuple[int, int]]:
    """Returns the adjusted line ranges based on edits from the original code.

    This computes the new line ranges by diffing original_source and
    modified_source, and adjust each range based on how the range overlaps with
    the diffs.

    Note the diff can contain lines outside of the original line ranges. This can
    happen when the formatting has to be done in adjacent to maintain consistent
    local results. For example:

    1. def my_func(arg1, arg2,
    2.             arg3,):
    3.   pass

    If it restricts to line 2-2, it can't simply reformat line 2, it also has
    to reformat line 1:

    1. def my_func(
    2.     arg1,
    3.     arg2,
    4.     arg3,
    5. ):
    6.   pass

    In this case, we will expand the line ranges to also include the whole diff
    block.

    Args:
      lines: a collection of line ranges.
      original_source: the original source.
      modified_source: the modified source.
    """
    lines_mappings = _calculate_lines_mappings(original_source, modified_source)

    new_lines = []
    # Keep an index of the current search. Since the lines and lines_mappings are
    # sorted, this makes the search complexity linear.
    current_mapping_index = 0
    for start, end in sorted(lines):
        start_mapping_index = _find_lines_mapping_index(
            start,
            lines_mappings,
            current_mapping_index,
        )
        end_mapping_index = _find_lines_mapping_index(
            end,
            lines_mappings,
            start_mapping_index,
        )
        current_mapping_index = start_mapping_index
        if start_mapping_index >= len(lines_mappings) or end_mapping_index >= len(
            lines_mappings
        ):
            # Protect against invalid inputs.
            continue
        start_mapping = lines_mappings[start_mapping_index]
        end_mapping = lines_mappings[end_mapping_index]
        if start_mapping.is_changed_block:
            # When the line falls into a changed block, expands to the whole block.
            new_start = start_mapping.modified_start
        else:
            new_start = (
                start - start_mapping.original_start + start_mapping.modified_start
            )
        if end_mapping.is_changed_block:
            # When the line falls into a changed block, expands to the whole block.
            new_end = end_mapping.modified_end
        else:
            new_end = end - end_mapping.original_start + end_mapping.modified_start
        new_range = (new_start, new_end)
        if is_valid_line_range(new_range):
            new_lines.append(new_range)
    return new_lines


def convert_unchanged_lines(src_node: Node, lines: Collection[Tuple[int, int]]) -> None:
    """Converts unchanged lines to STANDALONE_COMMENT.

    The idea is similar to how `# fmt: on/off` is implemented. It also converts the
    nodes between those markers as a single `STANDALONE_COMMENT` leaf node with
    the unformatted code as its value. `STANDALONE_COMMENT` is a "fake" token
    that will be formatted as-is with its prefix normalized.

    Here we perform two passes:

    1. Visit the top-level statements, and convert them to a single
       `STANDALONE_COMMENT` when unchanged. This speeds up formatting when some
       of the top-level statements aren't changed.
    2. Convert unchanged "unwrapped lines" to `STANDALONE_COMMENT` nodes line by
       line. "unwrapped lines" are divided by the `NEWLINE` token. e.g. a
       multi-line statement is *one* "unwrapped line" that ends with `NEWLINE`,
       even though this statement itself can span multiple lines, and the
       tokenizer only sees the last '\n' as the `NEWLINE` token.

    NOTE: During pass (2), comment prefixes and indentations are ALWAYS
    normalized even when the lines aren't changed. This is fixable by moving
    more formatting to pass (1). However, it's hard to get it correct when
    incorrect indentations are used. So we defer this to future optimizations.
    """
    lines_set: Set[int] = set()
    for start, end in lines:
        lines_set.update(range(start, end + 1))
    visitor = _TopLevelStatementsVisitor(lines_set)
    _ = list(visitor.visit(src_node))  # Consume all results.
    _convert_unchanged_line_by_line(src_node, lines_set)


def _contains_standalone_comment(node: LN) -> bool:
    if isinstance(node, Leaf):
        return node.type == STANDALONE_COMMENT
    else:
        for child in node.children:
            if _contains_standalone_comment(child):
                return True
        return False


class _TopLevelStatementsVisitor(Visitor[None]):
    """
    A node visitor that converts unchanged top-level statements to
    STANDALONE_COMMENT.

    This is used in addition to _convert_unchanged_line_by_line, to
    speed up formatting when there are unchanged top-level
    classes/functions/statements.
    """

    def __init__(self, lines_set: Set[int]):
        self._lines_set = lines_set

    def visit_simple_stmt(self, node: Node) -> Iterator[None]:
        # This is only called for top-level statements, since `visit_suite`
        # won't visit its children nodes.
        yield from []
        newline_leaf = last_leaf(node)
        if not newline_leaf:
            return
        assert (
            newline_leaf.type == NEWLINE
        ), f"Unexpectedly found leaf.type={newline_leaf.type}"
        # We need to find the furthest ancestor with the NEWLINE as the last
        # leaf, since a `suite` can simply be a `simple_stmt` when it puts
        # its body on the same line. Example: `if cond: pass`.
        ancestor = furthest_ancestor_with_last_leaf(newline_leaf)
        if not _get_line_range(ancestor).intersection(self._lines_set):
            _convert_node_to_standalone_comment(ancestor)

    def visit_suite(self, node: Node) -> Iterator[None]:
        yield from []
        # If there is a STANDALONE_COMMENT node, it means parts of the node tree
        # have fmt on/off/skip markers. Those STANDALONE_COMMENT nodes can't
        # be simply converted by calling str(node). So we just don't convert
        # here.
        if _contains_standalone_comment(node):
            return
        # Find the semantic parent of this suite. For `async_stmt` and
        # `async_funcdef`, the ASYNC token is defined on a separate level by the
        # grammar.
        semantic_parent = node.parent
        if semantic_parent is not None:
            if (
                semantic_parent.prev_sibling is not None
                and semantic_parent.prev_sibling.type == ASYNC
            ):
                semantic_parent = semantic_parent.parent
        if semantic_parent is not None and not _get_line_range(
            semantic_parent
        ).intersection(self._lines_set):
            _convert_node_to_standalone_comment(semantic_parent)


def _convert_unchanged_line_by_line(node: Node, lines_set: Set[int]) -> None:
    """Converts unchanged to STANDALONE_COMMENT line by line."""
    for leaf in node.leaves():
        if leaf.type != NEWLINE:
            # We only consider "unwrapped lines", which are divided by the NEWLINE
            # token.
            continue
        if leaf.parent and leaf.parent.type == syms.match_stmt:
            # The `suite` node is defined as:
            #   match_stmt: "match" subject_expr ':' NEWLINE INDENT case_block+ DEDENT
            # Here we need to check `subject_expr`. The `case_block+` will be
            # checked by their own NEWLINEs.
            nodes_to_ignore: List[LN] = []
            prev_sibling = leaf.prev_sibling
            while prev_sibling:
                nodes_to_ignore.insert(0, prev_sibling)
                prev_sibling = prev_sibling.prev_sibling
            if not _get_line_range(nodes_to_ignore).intersection(lines_set):
                _convert_nodes_to_standalone_comment(nodes_to_ignore, newline=leaf)
        elif leaf.parent and leaf.parent.type == syms.suite:
            # The `suite` node is defined as:
            #   suite: simple_stmt | NEWLINE INDENT stmt+ DEDENT
            # We will check `simple_stmt` and `stmt+` separately against the lines set
            parent_sibling = leaf.parent.prev_sibling
            nodes_to_ignore = []
            while parent_sibling and not parent_sibling.type == syms.suite:
                # NOTE: Multiple suite nodes can exist as siblings in e.g. `if_stmt`.
                nodes_to_ignore.insert(0, parent_sibling)
                parent_sibling = parent_sibling.prev_sibling
            # Special case for `async_stmt` and `async_funcdef` where the ASYNC
            # token is on the grandparent node.
            grandparent = leaf.parent.parent
            if (
                grandparent is not None
                and grandparent.prev_sibling is not None
                and grandparent.prev_sibling.type == ASYNC
            ):
                nodes_to_ignore.insert(0, grandparent.prev_sibling)
            if not _get_line_range(nodes_to_ignore).intersection(lines_set):
                _convert_nodes_to_standalone_comment(nodes_to_ignore, newline=leaf)
        else:
            ancestor = furthest_ancestor_with_last_leaf(leaf)
            # Consider multiple decorators as a whole block, as their
            # newlines have different behaviors than the rest of the grammar.
            if (
                ancestor.type == syms.decorator
                and ancestor.parent
                and ancestor.parent.type == syms.decorators
            ):
                ancestor = ancestor.parent
            if not _get_line_range(ancestor).intersection(lines_set):
                _convert_node_to_standalone_comment(ancestor)


def _convert_node_to_standalone_comment(node: LN) -> None:
    """Convert node to STANDALONE_COMMENT by modifying the tree inline."""
    parent = node.parent
    if not parent:
        return
    first = first_leaf(node)
    last = last_leaf(node)
    if not first or not last:
        return
    if first is last:
        # This can happen on the following edge cases:
        # 1. A block of `# fmt: off/on` code except the `# fmt: on` is placed
        #    on the end of the last line instead of on a new line.
        # 2. A single backslash on its own line followed by a comment line.
        # Ideally we don't want to format them when not requested, but fixing
        # isn't easy. These cases are also badly formatted code, so it isn't
        # too bad we reformat them.
        return
    # The prefix contains comments and indentation whitespaces. They are
    # reformatted accordingly to the correct indentation level.
    # This also means the indentation will be changed on the unchanged lines, and
    # this is actually required to not break incremental reformatting.
    prefix = first.prefix
    first.prefix = ""
    index = node.remove()
    if index is not None:
        # Remove the '\n', as STANDALONE_COMMENT will have '\n' appended when
        # generating the formatted code.
        value = str(node)[:-1]
        parent.insert_child(
            index,
            Leaf(
                STANDALONE_COMMENT,
                value,
                prefix=prefix,
                fmt_pass_converted_first_leaf=first,
            ),
        )


def _convert_nodes_to_standalone_comment(nodes: Sequence[LN], *, newline: Leaf) -> None:
    """Convert nodes to STANDALONE_COMMENT by modifying the tree inline."""
    if not nodes:
        return
    parent = nodes[0].parent
    first = first_leaf(nodes[0])
    if not parent or not first:
        return
    prefix = first.prefix
    first.prefix = ""
    value = "".join(str(node) for node in nodes)
    # The prefix comment on the NEWLINE leaf is the trailing comment of the statement.
    if newline.prefix:
        value += newline.prefix
        newline.prefix = ""
    index = nodes[0].remove()
    for node in nodes[1:]:
        node.remove()
    if index is not None:
        parent.insert_child(
            index,
            Leaf(
                STANDALONE_COMMENT,
                value,
                prefix=prefix,
                fmt_pass_converted_first_leaf=first,
            ),
        )


def _leaf_line_end(leaf: Leaf) -> int:
    """Returns the line number of the leaf node's last line."""
    if leaf.type == NEWLINE:
        return leaf.lineno
    else:
        # Leaf nodes like multiline strings can occupy multiple lines.
        return leaf.lineno + str(leaf).count("\n")


def _get_line_range(node_or_nodes: Union[LN, List[LN]]) -> Set[int]:
    """Returns the line range of this node or list of nodes."""
    if isinstance(node_or_nodes, list):
        nodes = node_or_nodes
        if not nodes:
            return set()
        first = first_leaf(nodes[0])
        last = last_leaf(nodes[-1])
        if first and last:
            line_start = first.lineno
            line_end = _leaf_line_end(last)
            return set(range(line_start, line_end + 1))
        else:
            return set()
    else:
        node = node_or_nodes
        if isinstance(node, Leaf):
            return set(range(node.lineno, _leaf_line_end(node) + 1))
        else:
            first = first_leaf(node)
            last = last_leaf(node)
            if first and last:
                return set(range(first.lineno, _leaf_line_end(last) + 1))
            else:
                return set()


@dataclass
class _LinesMapping:
    """1-based lines mapping from original source to modified source.

    Lines [original_start, original_end] from original source
    are mapped to [modified_start, modified_end].

    The ranges are inclusive on both ends.
    """

    original_start: int
    original_end: int
    modified_start: int
    modified_end: int
    # Whether this range corresponds to a changed block, or an unchanged block.
    is_changed_block: bool


def _calculate_lines_mappings(
    original_source: str,
    modified_source: str,
) -> Sequence[_LinesMapping]:
    """Returns a sequence of _LinesMapping by diffing the sources.

    For example, given the following diff:
        import re
      - def func(arg1,
      -   arg2, arg3):
      + def func(arg1, arg2, arg3):
          pass
    It returns the following mappings:
      original -> modified
       (1, 1)  ->  (1, 1), is_changed_block=False (the "import re" line)
       (2, 3)  ->  (2, 2), is_changed_block=True (the diff)
       (4, 4)  ->  (3, 3), is_changed_block=False (the "pass" line)

    You can think of this visually as if it brings up a side-by-side diff, and tries
    to map the line ranges from the left side to the right side:

      (1, 1)->(1, 1)    1. import re          1. import re
      (2, 3)->(2, 2)    2. def func(arg1,     2. def func(arg1, arg2, arg3):
                        3.   arg2, arg3):
      (4, 4)->(3, 3)    4.   pass             3.   pass

    Args:
      original_source: the original source.
      modified_source: the modified source.
    """
    matcher = difflib.SequenceMatcher(
        None,
        original_source.splitlines(keepends=True),
        modified_source.splitlines(keepends=True),
    )
    matching_blocks = matcher.get_matching_blocks()
    lines_mappings: List[_LinesMapping] = []
    # matching_blocks is a sequence of "same block of code ranges", see
    # https://docs.python.org/3/library/difflib.html#difflib.SequenceMatcher.get_matching_blocks
    # Each block corresponds to a _LinesMapping with is_changed_block=False,
    # and the ranges between two blocks corresponds to a _LinesMapping with
    # is_changed_block=True,
    # NOTE: matching_blocks is 0-based, but _LinesMapping is 1-based.
    for i, block in enumerate(matching_blocks):
        if i == 0:
            if block.a != 0 or block.b != 0:
                lines_mappings.append(
                    _LinesMapping(
                        original_start=1,
                        original_end=block.a,
                        modified_start=1,
                        modified_end=block.b,
                        is_changed_block=False,
                    )
                )
        else:
            previous_block = matching_blocks[i - 1]
            lines_mappings.append(
                _LinesMapping(
                    original_start=previous_block.a + previous_block.size + 1,
                    original_end=block.a,
                    modified_start=previous_block.b + previous_block.size + 1,
                    modified_end=block.b,
                    is_changed_block=True,
                )
            )
        if i < len(matching_blocks) - 1:
            lines_mappings.append(
                _LinesMapping(
                    original_start=block.a + 1,
                    original_end=block.a + block.size,
                    modified_start=block.b + 1,
                    modified_end=block.b + block.size,
                    is_changed_block=False,
                )
            )
    return lines_mappings


def _find_lines_mapping_index(
    original_line: int,
    lines_mappings: Sequence[_LinesMapping],
    start_index: int,
) -> int:
    """Returns the original index of the lines mappings for the original line."""
    index = start_index
    while index < len(lines_mappings):
        mapping = lines_mappings[index]
        if mapping.original_start <= original_line <= mapping.original_end:
            return index
        index += 1
    return index
