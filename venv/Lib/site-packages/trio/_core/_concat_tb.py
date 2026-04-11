from __future__ import annotations

from types import TracebackType


# this is used for collapsing single-exception ExceptionGroups when using
# `strict_exception_groups=False`. Once that is retired this function can
# be removed as well.
def concat_tb(
    head: TracebackType | None,
    tail: TracebackType | None,
) -> TracebackType | None:
    # We have to use an iterative algorithm here, because in the worst case
    # this might be a RecursionError stack that is by definition too deep to
    # process by recursion!
    head_tbs = []
    pointer = head
    while pointer is not None:
        head_tbs.append(pointer)
        pointer = pointer.tb_next
    current_head = tail
    for head_tb in reversed(head_tbs):
        current_head = TracebackType(
            current_head, head_tb.tb_frame, head_tb.tb_lasti, head_tb.tb_lineno
        )
    return current_head
