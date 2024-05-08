import pytest

from trio import run
from trio.lowlevel import RunVar, RunVarToken

from ... import _core


# scary runvar tests
def test_runvar_smoketest() -> None:
    t1 = RunVar[str]("test1")
    t2 = RunVar[str]("test2", default="catfish")

    assert repr(t1) == "<RunVar name='test1'>"

    async def first_check() -> None:
        with pytest.raises(LookupError):
            t1.get()

        t1.set("swordfish")
        assert t1.get() == "swordfish"
        assert t2.get() == "catfish"
        assert t2.get(default="eel") == "eel"

        t2.set("goldfish")
        assert t2.get() == "goldfish"
        assert t2.get(default="tuna") == "goldfish"

    async def second_check() -> None:
        with pytest.raises(LookupError):
            t1.get()

        assert t2.get() == "catfish"

    run(first_check)
    run(second_check)


def test_runvar_resetting() -> None:
    t1 = RunVar[str]("test1")
    t2 = RunVar[str]("test2", default="dogfish")
    t3 = RunVar[str]("test3")

    async def reset_check() -> None:
        token = t1.set("moonfish")
        assert t1.get() == "moonfish"
        t1.reset(token)

        with pytest.raises(TypeError):
            t1.reset(None)  # type: ignore[arg-type]

        with pytest.raises(LookupError):
            t1.get()

        token2 = t2.set("catdogfish")
        assert t2.get() == "catdogfish"
        t2.reset(token2)
        assert t2.get() == "dogfish"

        with pytest.raises(ValueError, match="^token has already been used$"):
            t2.reset(token2)

        token3 = t3.set("basculin")
        assert t3.get() == "basculin"

        with pytest.raises(ValueError, match="^token is not for us$"):
            t1.reset(token3)

    run(reset_check)


def test_runvar_sync() -> None:
    t1 = RunVar[str]("test1")

    async def sync_check() -> None:
        async def task1() -> None:
            t1.set("plaice")
            assert t1.get() == "plaice"

        async def task2(tok: RunVarToken[str]) -> None:
            t1.reset(tok)

            with pytest.raises(LookupError):
                t1.get()

            t1.set("haddock")

        async with _core.open_nursery() as n:
            token = t1.set("cod")
            assert t1.get() == "cod"

            n.start_soon(task1)
            await _core.wait_all_tasks_blocked()
            assert t1.get() == "plaice"

            n.start_soon(task2, token)
            await _core.wait_all_tasks_blocked()
            assert t1.get() == "haddock"

    run(sync_check)


def test_accessing_runvar_outside_run_call_fails() -> None:
    t1 = RunVar[str]("test1")

    with pytest.raises(RuntimeError):
        t1.set("asdf")

    with pytest.raises(RuntimeError):
        t1.get()

    async def get_token() -> RunVarToken[str]:
        return t1.set("ok")

    token = run(get_token)

    with pytest.raises(RuntimeError):
        t1.reset(token)
