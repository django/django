"""
This namespace represents special functions that can call back into Trio from
an external thread by means of a Trio Token present in Thread Local Storage
"""


from ._threads import (
    from_thread_check_cancelled as check_cancelled,
    from_thread_run as run,
    from_thread_run_sync as run_sync,
)

# need to use __all__ for pyright --verifytypes to see re-exports when renaming them
__all__ = ["check_cancelled", "run", "run_sync"]
