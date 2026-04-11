from __future__ import annotations

import io
import sys
from typing import TYPE_CHECKING

import pytest

from trio._tools.mypy_annotate import Result, export, main, process_line

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize(
    ("src", "expected"),
    [
        ("", None),
        ("a regular line\n", None),
        (
            "package\\filename.py:42:8: note: Some info\n",
            Result(
                kind="notice",
                filename="package\\filename.py",
                start_line=42,
                start_col=8,
                end_line=None,
                end_col=None,
                message=" Some info",
            ),
        ),
        (
            "package/filename.py:42:1:46:3: error: Type error here [code]\n",
            Result(
                kind="error",
                filename="package/filename.py",
                start_line=42,
                start_col=1,
                end_line=46,
                end_col=3,
                message=" Type error here [code]",
            ),
        ),
        (
            "package/module.py:87: warn: Bad code\n",
            Result(
                kind="warning",
                filename="package/module.py",
                start_line=87,
                message=" Bad code",
            ),
        ),
    ],
    ids=["blank", "normal", "note-wcol", "error-wend", "warn-lineonly"],
)
def test_processing(src: str, expected: Result | None) -> None:
    result = process_line(src)
    assert result == expected


def test_export(capsys: pytest.CaptureFixture[str]) -> None:
    results = {
        Result(
            kind="notice",
            filename="package\\filename.py",
            start_line=42,
            start_col=8,
            end_line=None,
            end_col=None,
            message=" Some info",
        ): ["Windows", "Mac"],
        Result(
            kind="error",
            filename="package/filename.py",
            start_line=42,
            start_col=1,
            end_line=46,
            end_col=3,
            message=" Type error here [code]",
        ): ["Linux", "Mac"],
        Result(
            kind="warning",
            filename="package/module.py",
            start_line=87,
            message=" Bad code",
        ): ["Linux"],
    }
    export(results)
    std = capsys.readouterr()
    assert std.err == ""
    assert std.out == (
        "::notice file=package\\filename.py,line=42,col=8,"
        "title=Mypy-Windows+Mac::package\\filename.py:(42:8): Some info"
        "\n"
        "::error file=package/filename.py,line=42,col=1,endLine=46,endColumn=3,"
        "title=Mypy-Linux+Mac::package/filename.py:(42:1 - 46:3): Type error here [code]"
        "\n"
        "::warning file=package/module.py,line=87,"
        "title=Mypy-Linux::package/module.py:87: Bad code\n"
    )


def test_endtoend(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import trio._tools.mypy_annotate as mypy_annotate

    inp_text = """\
Mypy begun
trio/core.py:15: error: Bad types here [misc]
trio/package/module.py:48:4:56:18: warn: Missing annotations  [no-untyped-def]
Found 3 errors in 29 files
"""
    result_file = tmp_path / "dump.dat"
    assert not result_file.exists()
    with monkeypatch.context():
        monkeypatch.setattr(sys, "stdin", io.StringIO(inp_text))

        mypy_annotate.main(
            ["--dumpfile", str(result_file), "--platform", "SomePlatform"],
        )

    std = capsys.readouterr()
    assert std.err == ""
    assert std.out == inp_text  # Echos the original.

    assert result_file.exists()

    main(["--dumpfile", str(result_file)])

    std = capsys.readouterr()
    assert std.err == ""
    assert std.out == (
        "::error file=trio/core.py,line=15,title=Mypy-SomePlatform::trio/core.py:15: Bad types here [misc]\n"
        "::warning file=trio/package/module.py,line=48,col=4,endLine=56,endColumn=18,"
        "title=Mypy-SomePlatform::trio/package/module.py:(48:4 - 56:18): Missing "
        "annotations  [no-untyped-def]\n"
    )
