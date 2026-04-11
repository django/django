import ast
import sys
from pathlib import Path

import pytest

from trio._tests.pytest_plugin import skip_if_optional_else_raise

# imports in gen_exports that are not in `install_requires` in setup.py
try:
    import astor  # noqa: F401
    import isort  # noqa: F401
except ImportError as error:
    skip_if_optional_else_raise(error)


from trio._tools.gen_exports import (
    File,
    create_passthrough_args,
    get_public_methods,
    process,
    run_linters,
    run_ruff,
)

from ..._core._tests.tutil import slow

SOURCE = '''from _run import _public
from collections import Counter

class Test:
    @_public
    def public_func(self):
        """With doc string"""

    @ignore_this
    @_public
    @another_decorator
    async def public_async_func(self) -> Counter:
        pass  # no doc string

    def not_public(self):
        pass

    async def not_public_async(self):
        pass
'''

IMPORT_1 = """\
from collections import Counter
"""

IMPORT_2 = """\
from collections import Counter
import os
"""

IMPORT_3 = """\
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from collections import Counter
"""


def test_get_public_methods() -> None:
    methods = list(get_public_methods(ast.parse(SOURCE)))
    assert {m.name for m in methods} == {"public_func", "public_async_func"}


def test_create_pass_through_args() -> None:
    testcases = [
        ("def f()", "()"),
        ("def f(one)", "(one)"),
        ("def f(one, two)", "(one, two)"),
        ("def f(one, *args)", "(one, *args)"),
        (
            "def f(one, *args, kw1, kw2=None, **kwargs)",
            "(one, *args, kw1=kw1, kw2=kw2, **kwargs)",
        ),
    ]

    for funcdef, expected in testcases:
        func_node = ast.parse(funcdef + ":\n  pass").body[0]
        assert isinstance(func_node, ast.FunctionDef)
        assert create_passthrough_args(func_node) == expected


skip_lints = pytest.mark.skipif(
    sys.implementation.name != "cpython",
    reason="gen_exports is internal, black/isort only runs on CPython",
)


@slow
@skip_lints
@pytest.mark.parametrize("imports", [IMPORT_1, IMPORT_2, IMPORT_3])
def test_process(
    tmp_path: Path,
    imports: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    try:
        import black  # noqa: F401
    # there's no dedicated CI run that has astor+isort, but lacks black.
    except ImportError as error:  # pragma: no cover
        skip_if_optional_else_raise(error)

    modpath = tmp_path / "_module.py"
    genpath = tmp_path / "_generated_module.py"
    modpath.write_text(SOURCE, encoding="utf-8")
    file = File(modpath, "runner", platform="linux", imports=imports)
    assert not genpath.exists()
    with pytest.raises(SystemExit) as excinfo:
        process([file], do_test=True)
    assert excinfo.value.code == 1
    captured = capsys.readouterr()
    assert "Generated sources are outdated. Please regenerate." in captured.out
    with pytest.raises(SystemExit) as excinfo:
        process([file], do_test=False)
    assert excinfo.value.code == 1
    captured = capsys.readouterr()
    assert "Regenerated sources successfully." in captured.out
    assert genpath.exists()
    process([file], do_test=True)
    # But if we change the lookup path it notices
    with pytest.raises(SystemExit) as excinfo:
        process(
            [File(modpath, "runner.io_manager", platform="linux", imports=imports)],
            do_test=True,
        )
    assert excinfo.value.code == 1
    # Also if the platform is changed.
    with pytest.raises(SystemExit) as excinfo:
        process([File(modpath, "runner", imports=imports)], do_test=True)
    assert excinfo.value.code == 1


@skip_lints
def test_run_ruff(tmp_path: Path) -> None:
    """Test that processing properly fails if ruff does."""
    try:
        import ruff  # noqa: F401
    except ImportError as error:  # pragma: no cover
        skip_if_optional_else_raise(error)

    file = File(tmp_path / "module.py", "module")

    success, _ = run_ruff(file, "class not valid code ><")
    assert not success

    test_function = '''def combine_and(data: list[str]) -> str:
    """Join values of text, and have 'and' with the last one properly."""
    if len(data) >= 2:
        data[-1] = 'and ' + data[-1]
    if len(data) > 2:
        return ', '.join(data)
    return ' '.join(data)'''

    success, response = run_ruff(file, test_function)
    assert success
    assert response == test_function


@skip_lints
def test_lint_failure(tmp_path: Path) -> None:
    """Test that processing properly fails if black or ruff does."""
    try:
        import black  # noqa: F401
        import ruff  # noqa: F401
    except ImportError as error:  # pragma: no cover
        skip_if_optional_else_raise(error)

    file = File(tmp_path / "module.py", "module")

    with pytest.raises(SystemExit):
        run_linters(file, "class not valid code ><")

    with pytest.raises(SystemExit):
        run_linters(file, "import waffle\n;import trio")
