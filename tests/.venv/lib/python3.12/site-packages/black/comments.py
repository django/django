import re
from collections.abc import Collection, Iterator
from dataclasses import dataclass
from functools import lru_cache
from typing import Final, Union

from black.mode import Mode, Preview
from black.nodes import (
    CLOSING_BRACKETS,
    STANDALONE_COMMENT,
    STATEMENT,
    WHITESPACE,
    container_of,
    first_leaf_of,
    is_type_comment_string,
    make_simple_prefix,
    preceding_leaf,
    syms,
)
from blib2to3.pgen2 import token
from blib2to3.pytree import Leaf, Node

# types
LN = Union[Leaf, Node]

FMT_OFF: Final = {"# fmt: off", "# fmt:off", "# yapf: disable"}
FMT_SKIP: Final = {"# fmt: skip", "# fmt:skip"}
FMT_ON: Final = {"# fmt: on", "# fmt:on", "# yapf: enable"}

# Compound statements we care about for fmt: skip handling
# (excludes except_clause and case_block which aren't standalone compound statements)
_COMPOUND_STATEMENTS: Final = STATEMENT - {syms.except_clause, syms.case_block}

COMMENT_EXCEPTIONS = " !:#'"
_COMMENT_PREFIX = "# "
_COMMENT_LIST_SEPARATOR = ";"


@dataclass
class ProtoComment:
    """Describes a piece of syntax that is a comment.

    It's not a :class:`blib2to3.pytree.Leaf` so that:

    * it can be cached (`Leaf` objects should not be reused more than once as
      they store their lineno, column, prefix, and parent information);
    * `newlines` and `consumed` fields are kept separate from the `value`. This
      simplifies handling of special marker comments like ``# fmt: off/on``.
    """

    type: int  # token.COMMENT or STANDALONE_COMMENT
    value: str  # content of the comment
    newlines: int  # how many newlines before the comment
    consumed: int  # how many characters of the original leaf's prefix did we consume
    form_feed: bool  # is there a form feed before the comment
    leading_whitespace: str  # leading whitespace before the comment, if any


def generate_comments(leaf: LN, mode: Mode) -> Iterator[Leaf]:
    """Clean the prefix of the `leaf` and generate comments from it, if any.

    Comments in lib2to3 are shoved into the whitespace prefix.  This happens
    in `pgen2/driver.py:Driver.parse_tokens()`.  This was a brilliant implementation
    move because it does away with modifying the grammar to include all the
    possible places in which comments can be placed.

    The sad consequence for us though is that comments don't "belong" anywhere.
    This is why this function generates simple parentless Leaf objects for
    comments.  We simply don't know what the correct parent should be.

    No matter though, we can live without this.  We really only need to
    differentiate between inline and standalone comments.  The latter don't
    share the line with any code.

    Inline comments are emitted as regular token.COMMENT leaves.  Standalone
    are emitted with a fake STANDALONE_COMMENT token identifier.
    """
    total_consumed = 0
    for pc in list_comments(
        leaf.prefix, is_endmarker=leaf.type == token.ENDMARKER, mode=mode
    ):
        total_consumed = pc.consumed
        prefix = make_simple_prefix(pc.newlines, pc.form_feed)
        yield Leaf(pc.type, pc.value, prefix=prefix)
    normalize_trailing_prefix(leaf, total_consumed)


@lru_cache(maxsize=4096)
def list_comments(prefix: str, *, is_endmarker: bool, mode: Mode) -> list[ProtoComment]:
    """Return a list of :class:`ProtoComment` objects parsed from the given `prefix`."""
    result: list[ProtoComment] = []
    if not prefix or "#" not in prefix:
        return result

    consumed = 0
    nlines = 0
    ignored_lines = 0
    form_feed = False
    for index, full_line in enumerate(re.split("\r?\n|\r", prefix)):
        consumed += len(full_line) + 1  # adding the length of the split '\n'
        match = re.match(r"^(\s*)(\S.*|)$", full_line)
        assert match
        whitespace, line = match.groups()
        if not line:
            nlines += 1
            if "\f" in full_line:
                form_feed = True
        if not line.startswith("#"):
            # Escaped newlines outside of a comment are not really newlines at
            # all. We treat a single-line comment following an escaped newline
            # as a simple trailing comment.
            if line.endswith("\\"):
                ignored_lines += 1
            continue

        if index == ignored_lines and not is_endmarker:
            comment_type = token.COMMENT  # simple trailing comment
        else:
            comment_type = STANDALONE_COMMENT
        comment = make_comment(line, mode=mode)
        result.append(
            ProtoComment(
                type=comment_type,
                value=comment,
                newlines=nlines,
                consumed=consumed,
                form_feed=form_feed,
                leading_whitespace=whitespace,
            )
        )
        form_feed = False
        nlines = 0
    return result


def normalize_trailing_prefix(leaf: LN, total_consumed: int) -> None:
    """Normalize the prefix that's left over after generating comments.

    Note: don't use backslashes for formatting or you'll lose your voting rights.
    """
    remainder = leaf.prefix[total_consumed:]
    if "\\" not in remainder:
        nl_count = remainder.count("\n")
        form_feed = "\f" in remainder and remainder.endswith("\n")
        leaf.prefix = make_simple_prefix(nl_count, form_feed)
        return

    leaf.prefix = ""


def make_comment(content: str, mode: Mode) -> str:
    """Return a consistently formatted comment from the given `content` string.

    All comments (except for "##", "#!", "#:", '#'") should have a single
    space between the hash sign and the content.

    If `content` didn't start with a hash sign, one is provided.

    Comments containing fmt directives are preserved exactly as-is to respect
    user intent (e.g., `#no space # fmt: skip` stays as-is).
    """
    content = content.rstrip()
    if not content:
        return "#"

    # Preserve comments with fmt directives exactly as-is
    if content.startswith("#") and contains_fmt_directive(content):
        return content

    if content[0] == "#":
        content = content[1:]
    if (
        content
        and content[0] == "\N{NO-BREAK SPACE}"
        and not is_type_comment_string("# " + content.lstrip(), mode=mode)
    ):
        content = " " + content[1:]  # Replace NBSP by a simple space
    if (
        Preview.standardize_type_comments in mode
        and content
        and "\N{NO-BREAK SPACE}" not in content
        and is_type_comment_string("#" + content, mode=mode)
    ):
        type_part, value_part = content.split(":", 1)
        content = type_part.strip() + ": " + value_part.strip()

    if content and content[0] not in COMMENT_EXCEPTIONS:
        content = " " + content
    return "#" + content


def normalize_fmt_off(
    node: Node, mode: Mode, lines: Collection[tuple[int, int]]
) -> None:
    """Convert content between `# fmt: off`/`# fmt: on` into standalone comments."""
    try_again = True
    while try_again:
        try_again = convert_one_fmt_off_pair(node, mode, lines)


def _should_process_fmt_comment(
    comment: ProtoComment, leaf: Leaf
) -> tuple[bool, bool, bool]:
    """Check if comment should be processed for fmt handling.

    Returns (should_process, is_fmt_off, is_fmt_skip).
    """
    is_fmt_off = contains_fmt_directive(comment.value, FMT_OFF)
    is_fmt_skip = contains_fmt_directive(comment.value, FMT_SKIP)

    if not is_fmt_off and not is_fmt_skip:
        return False, False, False

    # Invalid use when `# fmt: off` is applied before a closing bracket
    if is_fmt_off and leaf.type in CLOSING_BRACKETS:
        return False, False, False

    return True, is_fmt_off, is_fmt_skip


def _is_valid_standalone_fmt_comment(
    comment: ProtoComment, leaf: Leaf, is_fmt_off: bool, is_fmt_skip: bool
) -> bool:
    """Check if comment is a valid standalone fmt directive.

    We only want standalone comments. If there's no previous leaf or if
    the previous leaf is indentation, it's a standalone comment in disguise.
    """
    if comment.type == STANDALONE_COMMENT:
        return True

    prev = preceding_leaf(leaf)
    if not prev:
        return True

    # Treat STANDALONE_COMMENT nodes as whitespace for check
    if is_fmt_off and prev.type not in WHITESPACE and prev.type != STANDALONE_COMMENT:
        return False
    if is_fmt_skip and prev.type in WHITESPACE:
        return False

    return True


def _handle_comment_only_fmt_block(
    leaf: Leaf,
    comment: ProtoComment,
    previous_consumed: int,
    mode: Mode,
) -> bool:
    """Handle fmt:off/on blocks that contain only comments.

    Returns True if a block was converted, False otherwise.
    """
    all_comments = list_comments(leaf.prefix, is_endmarker=False, mode=mode)

    # Find the first fmt:off and its matching fmt:on
    fmt_off_idx = None
    fmt_on_idx = None
    for idx, c in enumerate(all_comments):
        if fmt_off_idx is None and contains_fmt_directive(c.value, FMT_OFF):
            fmt_off_idx = idx
        if (
            fmt_off_idx is not None
            and idx > fmt_off_idx
            and contains_fmt_directive(c.value, FMT_ON)
        ):
            fmt_on_idx = idx
            break

    # Only proceed if we found both directives
    if fmt_on_idx is None or fmt_off_idx is None:
        return False

    comment = all_comments[fmt_off_idx]
    fmt_on_comment = all_comments[fmt_on_idx]
    original_prefix = leaf.prefix

    # Build the hidden value
    start_pos = comment.consumed
    end_pos = fmt_on_comment.consumed
    content_between_and_fmt_on = original_prefix[start_pos:end_pos]
    hidden_value = comment.value + "\n" + content_between_and_fmt_on

    if hidden_value.endswith("\n"):
        hidden_value = hidden_value[:-1]

    # Build the standalone comment prefix - preserve all content before fmt:off
    # including any comments that precede it
    if fmt_off_idx == 0:
        # No comments before fmt:off, use previous_consumed
        pre_fmt_off_consumed = previous_consumed
    else:
        # Use the consumed position of the last comment before fmt:off
        # This preserves all comments and content before the fmt:off directive
        pre_fmt_off_consumed = all_comments[fmt_off_idx - 1].consumed

    standalone_comment_prefix = (
        original_prefix[:pre_fmt_off_consumed] + "\n" * comment.newlines
    )

    fmt_off_prefix = original_prefix.split(comment.value)[0]
    if "\n" in fmt_off_prefix:
        fmt_off_prefix = fmt_off_prefix.split("\n")[-1]
    standalone_comment_prefix += fmt_off_prefix

    # Update leaf prefix
    leaf.prefix = original_prefix[fmt_on_comment.consumed :]

    # Insert the STANDALONE_COMMENT
    parent = leaf.parent
    assert parent is not None, "INTERNAL ERROR: fmt: on/off handling (prefix only)"

    leaf_idx = None
    for idx, child in enumerate(parent.children):
        if child is leaf:
            leaf_idx = idx
            break

    assert leaf_idx is not None, "INTERNAL ERROR: fmt: on/off handling (leaf index)"

    parent.insert_child(
        leaf_idx,
        Leaf(
            STANDALONE_COMMENT,
            hidden_value,
            prefix=standalone_comment_prefix,
            fmt_pass_converted_first_leaf=None,
        ),
    )
    return True


def convert_one_fmt_off_pair(
    node: Node, mode: Mode, lines: Collection[tuple[int, int]]
) -> bool:
    """Convert content of a single `# fmt: off`/`# fmt: on` into a standalone comment.

    Returns True if a pair was converted.
    """
    for leaf in node.leaves():
        # Skip STANDALONE_COMMENT nodes that were created by fmt:off/on/skip processing
        # to avoid reprocessing them in subsequent iterations
        if leaf.type == STANDALONE_COMMENT and hasattr(
            leaf, "fmt_pass_converted_first_leaf"
        ):
            continue

        previous_consumed = 0
        for comment in list_comments(leaf.prefix, is_endmarker=False, mode=mode):
            should_process, is_fmt_off, is_fmt_skip = _should_process_fmt_comment(
                comment, leaf
            )
            if not should_process:
                previous_consumed = comment.consumed
                continue

            if not _is_valid_standalone_fmt_comment(
                comment, leaf, is_fmt_off, is_fmt_skip
            ):
                previous_consumed = comment.consumed
                continue

            ignored_nodes = list(generate_ignored_nodes(leaf, comment, mode))

            # Handle comment-only blocks
            if not ignored_nodes and is_fmt_off:
                if _handle_comment_only_fmt_block(
                    leaf, comment, previous_consumed, mode
                ):
                    return True
                continue

            # Need actual nodes to process
            if not ignored_nodes:
                continue

            # Handle regular fmt blocks

            _handle_regular_fmt_block(
                ignored_nodes,
                comment,
                previous_consumed,
                is_fmt_skip,
                lines,
                leaf,
            )
            return True

    return False


def _handle_regular_fmt_block(
    ignored_nodes: list[LN],
    comment: ProtoComment,
    previous_consumed: int,
    is_fmt_skip: bool,
    lines: Collection[tuple[int, int]],
    leaf: Leaf,
) -> None:
    """Handle fmt blocks with actual AST nodes."""
    first = ignored_nodes[0]  # Can be a container node with the `leaf`.
    parent = first.parent
    prefix = first.prefix

    if contains_fmt_directive(comment.value, FMT_OFF):
        first.prefix = prefix[comment.consumed :]
    if is_fmt_skip:
        first.prefix = ""
        standalone_comment_prefix = prefix
    else:
        standalone_comment_prefix = prefix[:previous_consumed] + "\n" * comment.newlines

    # Ensure STANDALONE_COMMENT nodes have trailing newlines when stringified
    # This prevents multiple fmt: skip comments from being concatenated on one line
    parts = []
    for node in ignored_nodes:
        if isinstance(node, Leaf) and node.type == STANDALONE_COMMENT:
            # Add newline after STANDALONE_COMMENT Leaf
            node_str = str(node)
            if not node_str.endswith("\n"):
                node_str += "\n"
            parts.append(node_str)
        elif isinstance(node, Node):
            # For nodes that might contain STANDALONE_COMMENT leaves,
            # we need custom stringify
            has_standalone = any(
                leaf.type == STANDALONE_COMMENT for leaf in node.leaves()
            )
            if has_standalone:
                # Stringify node with STANDALONE_COMMENT leaves having trailing newlines
                def stringify_node(n: LN) -> str:
                    if isinstance(n, Leaf):
                        if n.type == STANDALONE_COMMENT:
                            result = n.prefix + n.value
                            if not result.endswith("\n"):
                                result += "\n"
                            return result
                        return str(n)
                    else:
                        # For nested nodes, recursively process children
                        return "".join(stringify_node(child) for child in n.children)

                parts.append(stringify_node(node))
            else:
                parts.append(str(node))
        else:
            parts.append(str(node))

    hidden_value = "".join(parts)
    comment_lineno = leaf.lineno - comment.newlines

    if contains_fmt_directive(comment.value, FMT_OFF):
        fmt_off_prefix = ""
        if len(lines) > 0 and not any(
            line[0] <= comment_lineno <= line[1] for line in lines
        ):
            # keeping indentation of comment by preserving original whitespaces.
            fmt_off_prefix = prefix.split(comment.value)[0]
            if "\n" in fmt_off_prefix:
                fmt_off_prefix = fmt_off_prefix.split("\n")[-1]
        standalone_comment_prefix += fmt_off_prefix
        hidden_value = comment.value + "\n" + hidden_value

    if is_fmt_skip:
        hidden_value += comment.leading_whitespace + comment.value

    if hidden_value.endswith("\n"):
        # That happens when one of the `ignored_nodes` ended with a NEWLINE
        # leaf (possibly followed by a DEDENT).
        hidden_value = hidden_value[:-1]

    first_idx: int | None = None
    for ignored in ignored_nodes:
        index = ignored.remove()
        if first_idx is None:
            first_idx = index

    assert parent is not None, "INTERNAL ERROR: fmt: on/off handling (1)"
    assert first_idx is not None, "INTERNAL ERROR: fmt: on/off handling (2)"

    parent.insert_child(
        first_idx,
        Leaf(
            STANDALONE_COMMENT,
            hidden_value,
            prefix=standalone_comment_prefix,
            fmt_pass_converted_first_leaf=first_leaf_of(first),
        ),
    )


def generate_ignored_nodes(
    leaf: Leaf, comment: ProtoComment, mode: Mode
) -> Iterator[LN]:
    """Starting from the container of `leaf`, generate all leaves until `# fmt: on`.

    If comment is skip, returns leaf only.
    Stops at the end of the block.
    """
    if contains_fmt_directive(comment.value, FMT_SKIP):
        yield from _generate_ignored_nodes_from_fmt_skip(leaf, comment, mode)
        return
    container: LN | None = container_of(leaf)
    while container is not None and container.type != token.ENDMARKER:
        if is_fmt_on(container, mode=mode):
            return

        # fix for fmt: on in children
        if children_contains_fmt_on(container, mode=mode):
            for index, child in enumerate(container.children):
                if isinstance(child, Leaf) and is_fmt_on(child, mode=mode):
                    if child.type in CLOSING_BRACKETS:
                        # This means `# fmt: on` is placed at a different bracket level
                        # than `# fmt: off`. This is an invalid use, but as a courtesy,
                        # we include this closing bracket in the ignored nodes.
                        # The alternative is to fail the formatting.
                        yield child
                    return
                if (
                    child.type == token.INDENT
                    and index < len(container.children) - 1
                    and children_contains_fmt_on(
                        container.children[index + 1], mode=mode
                    )
                ):
                    # This means `# fmt: on` is placed right after an indentation
                    # level, and we shouldn't swallow the previous INDENT token.
                    return
                if children_contains_fmt_on(child, mode=mode):
                    return
                yield child
        else:
            if container.type == token.DEDENT and container.next_sibling is None:
                # This can happen when there is no matching `# fmt: on` comment at the
                # same level as `# fmt: on`. We need to keep this DEDENT.
                return
            yield container
            container = container.next_sibling


def _find_compound_statement_context(parent: Node) -> Node | None:
    """Return the body node of a compound statement if we should respect fmt: skip.

    This handles one-line compound statements like:
        if condition: body  # fmt: skip

    When Black expands such statements, they temporarily look like:
        if condition:
            body  # fmt: skip

    In both cases, we want to return the body node (either the simple_stmt directly
    or the suite containing it).
    """
    if parent.type != syms.simple_stmt:
        return None

    if not isinstance(parent.parent, Node):
        return None

    # Case 1: Expanded form after Black's initial formatting pass.
    # The one-liner has been split across multiple lines:
    #     if True:
    #         print("a"); print("b")  # fmt: skip
    # Structure: compound_stmt -> suite -> simple_stmt
    if (
        parent.parent.type == syms.suite
        and isinstance(parent.parent.parent, Node)
        and parent.parent.parent.type in _COMPOUND_STATEMENTS
    ):
        return parent.parent

    # Case 2: Original one-line form from the input source.
    # The statement is still on a single line:
    #     if True: print("a"); print("b")  # fmt: skip
    # Structure: compound_stmt -> simple_stmt
    if parent.parent.type in _COMPOUND_STATEMENTS:
        return parent

    return None


def _should_keep_compound_statement_inline(
    body_node: Node, simple_stmt_parent: Node
) -> bool:
    """Check if a compound statement should be kept on one line.

    Returns True only for compound statements with semicolon-separated bodies,
    like: if True: print("a"); print("b")  # fmt: skip
    """
    # Check if there are semicolons in the body
    for leaf in body_node.leaves():
        if leaf.type == token.SEMI:
            # Verify it's a single-line body (one simple_stmt)
            if body_node.type == syms.suite:
                # After formatting: check suite has one simple_stmt child
                simple_stmts = [
                    child
                    for child in body_node.children
                    if child.type == syms.simple_stmt
                ]
                return len(simple_stmts) == 1 and simple_stmts[0] is simple_stmt_parent
            else:
                # Original form: body_node IS the simple_stmt
                return body_node is simple_stmt_parent
    return False


def _get_compound_statement_header(
    body_node: Node, simple_stmt_parent: Node
) -> list[LN]:
    """Get header nodes for a compound statement that should be preserved inline."""
    if not _should_keep_compound_statement_inline(body_node, simple_stmt_parent):
        return []

    # Get the compound statement (parent of body)
    compound_stmt = body_node.parent
    if compound_stmt is None or compound_stmt.type not in _COMPOUND_STATEMENTS:
        return []

    # Collect all header leaves before the body
    header_leaves: list[LN] = []
    for child in compound_stmt.children:
        if child is body_node:
            break
        if isinstance(child, Leaf):
            if child.type not in (token.NEWLINE, token.INDENT):
                header_leaves.append(child)
        else:
            header_leaves.extend(child.leaves())
    return header_leaves


def _generate_ignored_nodes_from_fmt_skip(
    leaf: Leaf, comment: ProtoComment, mode: Mode
) -> Iterator[LN]:
    """Generate all leaves that should be ignored by the `# fmt: skip` from `leaf`."""
    prev_sibling = leaf.prev_sibling
    parent = leaf.parent
    ignored_nodes: list[LN] = []
    # Need to properly format the leaf prefix to compare it to comment.value,
    # which is also formatted
    comments = list_comments(leaf.prefix, is_endmarker=False, mode=mode)
    if not comments or comment.value != comments[0].value:
        return

    if Preview.fix_fmt_skip_in_one_liners in mode and not prev_sibling and parent:
        prev_sibling = parent.prev_sibling

    if prev_sibling is not None:
        leaf.prefix = leaf.prefix[comment.consumed :]

        if Preview.fix_fmt_skip_in_one_liners not in mode:
            siblings = [prev_sibling]
            while (
                "\n" not in prev_sibling.prefix
                and prev_sibling.prev_sibling is not None
            ):
                prev_sibling = prev_sibling.prev_sibling
                siblings.insert(0, prev_sibling)
            yield from siblings
            return

        # Generates the nodes to be ignored by `fmt: skip`.

        # Nodes to ignore are the ones on the same line as the
        # `# fmt: skip` comment, excluding the `# fmt: skip`
        # node itself.

        # Traversal process (starting at the `# fmt: skip` node):
        # 1. Move to the `prev_sibling` of the current node.
        # 2. If `prev_sibling` has children, go to its rightmost leaf.
        # 3. If there's no `prev_sibling`, move up to the parent
        # node and repeat.
        # 4. Continue until:
        #    a. You encounter an `INDENT` or `NEWLINE` node (indicates
        #       start of the line).
        #    b. You reach the root node.

        # Include all visited LEAVES in the ignored list, except INDENT
        # or NEWLINE leaves.

        current_node = prev_sibling
        ignored_nodes = [current_node]
        if current_node.prev_sibling is None and current_node.parent is not None:
            current_node = current_node.parent

        # Track seen nodes to detect cycles that can occur after tree modifications
        seen_nodes = {id(current_node)}

        while "\n" not in current_node.prefix and current_node.prev_sibling is not None:
            leaf_nodes = list(current_node.prev_sibling.leaves())
            next_node = leaf_nodes[-1] if leaf_nodes else current_node

            # Detect infinite loop - if we've seen this node before, stop
            # This can happen when STANDALONE_COMMENT nodes are inserted
            # during processing
            if id(next_node) in seen_nodes:
                break

            current_node = next_node
            seen_nodes.add(id(current_node))

            # Stop if we encounter a STANDALONE_COMMENT created by fmt processing
            if (
                isinstance(current_node, Leaf)
                and current_node.type == STANDALONE_COMMENT
                and hasattr(current_node, "fmt_pass_converted_first_leaf")
            ):
                break

            if (
                current_node.type in CLOSING_BRACKETS
                and current_node.parent
                and current_node.parent.type == syms.atom
            ):
                current_node = current_node.parent

            if current_node.type in (token.NEWLINE, token.INDENT):
                current_node.prefix = ""
                break

            if current_node.type == token.DEDENT:
                break

            # Special case for with expressions
            # Without this, we can stuck inside the asexpr_test's children's children
            if (
                current_node.parent
                and current_node.parent.type == syms.asexpr_test
                and current_node.parent.parent
                and current_node.parent.parent.type == syms.with_stmt
            ):
                current_node = current_node.parent

            ignored_nodes.insert(0, current_node)

            if current_node.prev_sibling is None and current_node.parent is not None:
                current_node = current_node.parent

        # Special handling for compound statements with semicolon-separated bodies
        if Preview.fix_fmt_skip_in_one_liners in mode and isinstance(parent, Node):
            body_node = _find_compound_statement_context(parent)
            if body_node is not None:
                header_nodes = _get_compound_statement_header(body_node, parent)
                if header_nodes:
                    ignored_nodes = header_nodes + ignored_nodes

        yield from ignored_nodes
    elif (
        parent is not None and parent.type == syms.suite and leaf.type == token.NEWLINE
    ):
        # The `# fmt: skip` is on the colon line of the if/while/def/class/...
        # statements. The ignored nodes should be previous siblings of the
        # parent suite node.
        leaf.prefix = ""
        parent_sibling = parent.prev_sibling
        while parent_sibling is not None and parent_sibling.type != syms.suite:
            ignored_nodes.insert(0, parent_sibling)
            parent_sibling = parent_sibling.prev_sibling
        # Special case for `async_stmt` where the ASYNC token is on the
        # grandparent node.
        grandparent = parent.parent
        if (
            grandparent is not None
            and grandparent.prev_sibling is not None
            and grandparent.prev_sibling.type == token.ASYNC
        ):
            ignored_nodes.insert(0, grandparent.prev_sibling)
        yield from iter(ignored_nodes)


def is_fmt_on(container: LN, mode: Mode) -> bool:
    """Determine whether formatting is switched on within a container.
    Determined by whether the last `# fmt:` comment is `on` or `off`.
    """
    fmt_on = False
    for comment in list_comments(container.prefix, is_endmarker=False, mode=mode):
        if contains_fmt_directive(comment.value, FMT_ON):
            fmt_on = True
        elif contains_fmt_directive(comment.value, FMT_OFF):
            fmt_on = False
    return fmt_on


def children_contains_fmt_on(container: LN, mode: Mode) -> bool:
    """Determine if children have formatting switched on."""
    for child in container.children:
        leaf = first_leaf_of(child)
        if leaf is not None and is_fmt_on(leaf, mode=mode):
            return True

    return False


def contains_pragma_comment(comment_list: list[Leaf]) -> bool:
    """
    Returns:
        True iff one of the comments in @comment_list is a pragma used by one
        of the more common static analysis tools for python (e.g. mypy, flake8,
        pylint).
    """
    for comment in comment_list:
        if comment.value.startswith(("# type:", "# noqa", "# pylint:")):
            return True

    return False


def contains_fmt_directive(
    comment_line: str, directives: set[str] = FMT_OFF | FMT_ON | FMT_SKIP
) -> bool:
    """
    Checks if the given comment contains format directives, alone or paired with
    other comments.

    Defaults to checking all directives (skip, off, on, yapf), but can be
    narrowed to specific ones.

    Matching styles:
      # foobar                    <-- single comment
      # foobar # foobar # foobar  <-- multiple comments
      # foobar; foobar            <-- list of comments (; separated)
    """
    semantic_comment_blocks = [
        comment_line,
        *[
            _COMMENT_PREFIX + comment.strip()
            for comment in comment_line.split(_COMMENT_PREFIX)[1:]
        ],
        *[
            _COMMENT_PREFIX + comment.strip()
            for comment in comment_line.strip(_COMMENT_PREFIX).split(
                _COMMENT_LIST_SEPARATOR
            )
        ],
    ]

    return any(comment in directives for comment in semantic_comment_blocks)
