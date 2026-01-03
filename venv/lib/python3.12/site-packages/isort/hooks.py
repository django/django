"""Defines a git hook to allow pre-commit warnings and errors about import order.

usage:
    exit_code = git_hook(strict=True|False, modify=True|False)
"""

import os
import subprocess  # nosec
from pathlib import Path

from isort import Config, api, exceptions


def get_output(command: list[str]) -> str:
    """Run a command and return raw output

    :param str command: the command to run
    :returns: the stdout output of the command
    """
    result = subprocess.run(command, stdout=subprocess.PIPE, check=True)  # nosec
    return result.stdout.decode()


def get_lines(command: list[str]) -> list[str]:
    """Run a command and return lines of output

    :param str command: the command to run
    :returns: list of whitespace-stripped lines output by command
    """
    stdout = get_output(command)
    return [line.strip() for line in stdout.splitlines()]


def git_hook(
    strict: bool = False,
    modify: bool = False,
    lazy: bool = False,
    settings_file: str = "",
    directories: list[str] | None = None,
) -> int:
    """Git pre-commit hook to check staged files for isort errors

    :param bool strict - if True, return number of errors on exit,
        causing the hook to fail. If False, return zero so it will
        just act as a warning.
    :param bool modify - if True, fix the sources if they are not
        sorted properly. If False, only report result without
        modifying anything.
    :param bool lazy - if True, also check/fix unstaged files.
        This is useful if you frequently use ``git commit -a`` for example.
        If False, only check/fix the staged files for isort errors.
    :param str settings_file - A path to a file to be used as
                               the configuration file for this run.
        When settings_file is the empty string, the configuration file
        will be searched starting at the directory containing the first
        staged file, if any, and going upward in the directory structure.
    :param list[str] directories - A list of directories to restrict the hook to.

    :return number of errors if in strict mode, 0 otherwise.
    """
    # Get list of files modified and staged
    diff_cmd = ["git", "diff-index", "--cached", "--name-only", "--diff-filter=ACMRTUXB", "HEAD"]
    if lazy:
        diff_cmd.remove("--cached")
    if directories:
        diff_cmd.extend(directories)

    files_modified = get_lines(diff_cmd)
    if not files_modified:
        return 0

    errors = 0
    config = Config(
        settings_file=settings_file,
        settings_path=os.path.dirname(os.path.abspath(files_modified[0])),
    )
    for filename in files_modified:
        if filename.endswith(".py"):
            # Get the staged contents of the file
            staged_cmd = ["git", "show", f":{filename}"]
            staged_contents = get_output(staged_cmd)

            try:
                if not api.check_code_string(
                    staged_contents, file_path=Path(filename), config=config
                ):
                    errors += 1
                    if modify:
                        api.sort_file(filename, config=config)
            except exceptions.FileSkipped:  # pragma: no cover
                pass

    return errors if strict else 0
