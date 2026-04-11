"""Check that started() can only be called for TaskStatus[None]."""

from trio import TaskStatus
from typing_extensions import assert_type


def check_status(
    none_status_explicit: TaskStatus[None],
    none_status_implicit: TaskStatus,
    int_status: TaskStatus[int],
) -> None:
    assert_type(none_status_explicit, TaskStatus[None])
    assert_type(none_status_implicit, TaskStatus[None])  # Default typevar
    assert_type(int_status, TaskStatus[int])

    # Omitting the parameter is only allowed for None.
    none_status_explicit.started()
    none_status_implicit.started()
    int_status.started()  # type: ignore

    # Explicit None is allowed.
    none_status_explicit.started(None)
    none_status_implicit.started(None)
    int_status.started(None)  # type: ignore

    none_status_explicit.started(42)  # type: ignore
    none_status_implicit.started(42)  # type: ignore
    int_status.started(42)
    int_status.started(True)
