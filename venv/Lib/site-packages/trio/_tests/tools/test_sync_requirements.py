from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from trio._tests.pytest_plugin import skip_if_optional_else_raise

# imports in gen_exports that are not in `install_requires` in requirements
try:
    import yaml  # noqa: F401
except ImportError as error:
    skip_if_optional_else_raise(error)

from trio._tools.sync_requirements import (
    update_requirements,
    yield_pre_commit_version_data,
)

if TYPE_CHECKING:
    from pathlib import Path


def test_yield_pre_commit_version_data() -> None:
    text = """
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.11.0
  - repo: https://github.com/psf/black-pre-commit-mirror
    rev: 25.1.0
  - bad: data
"""
    results = tuple(yield_pre_commit_version_data(text))
    assert results == (
        ("ruff-pre-commit", "0.11.0"),
        ("black-pre-commit-mirror", "25.1.0"),
    )


def test_update_requirements(
    tmp_path: Path,
) -> None:
    requirements_file = tmp_path / "requirements.txt"
    assert not requirements_file.exists()
    requirements_file.write_text(
        """# comment
  # also comment but spaces line start
waffles are delicious no equals
black==3.1.4 ; specific version thingy
mypy==1.15.0
ruff==1.2.5
# required by soupy cat""",
        encoding="utf-8",
    )
    assert update_requirements(requirements_file, {"black": "3.1.5", "ruff": "1.2.7"})
    assert requirements_file.read_text(encoding="utf-8") == """# comment
  # also comment but spaces line start
waffles are delicious no equals
black==3.1.5 ; specific version thingy
mypy==1.15.0
ruff==1.2.7
# required by soupy cat"""


def test_update_requirements_no_changes(
    tmp_path: Path,
) -> None:
    requirements_file = tmp_path / "requirements.txt"
    assert not requirements_file.exists()
    original = """# comment
  # also comment but spaces line start
waffles are delicious no equals
black==3.1.4 ; specific version thingy
mypy==1.15.0
ruff==1.2.5
# required by soupy cat"""
    requirements_file.write_text(original, encoding="utf-8")
    assert not update_requirements(
        requirements_file, {"black": "3.1.4", "ruff": "1.2.5"}
    )
    assert requirements_file.read_text(encoding="utf-8") == original
