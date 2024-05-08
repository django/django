from typing import Any, Dict


class AlreadyUsedError(RuntimeError):
    """An Outcome can only be unwrapped once."""
    pass


def fixup_module_metadata(
        module_name: str,
        namespace: Dict[str, object],
) -> None:
    def fix_one(obj: object) -> None:
        mod = getattr(obj, "__module__", None)
        if mod is not None and mod.startswith("outcome."):
            obj.__module__ = module_name
            if isinstance(obj, type):
                for attr_value in obj.__dict__.values():
                    fix_one(attr_value)

    all_list = namespace["__all__"]
    assert isinstance(all_list, (tuple, list)), repr(all_list)
    for objname in all_list:
        obj = namespace[objname]
        fix_one(obj)


def remove_tb_frames(exc: BaseException, n: int) -> BaseException:
    tb = exc.__traceback__
    for _ in range(n):
        assert tb is not None
        tb = tb.tb_next
    return exc.with_traceback(tb)
