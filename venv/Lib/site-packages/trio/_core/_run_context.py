from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from ._run import Runner, Task


class RunContext(threading.local):
    runner: Runner
    task: Task


GLOBAL_RUN_CONTEXT: Final = RunContext()
