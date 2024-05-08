#!/usr/bin/env python3
"""This is a file that wraps calls to `pyright --verifytypes`, achieving two things:
1. give an error if docstrings are missing.
    pyright will give a number of missing docstrings, and error messages, but not exit with a non-zero value.
2. filter out specific errors we don't care about.
    this is largely due to 1, but also because Trio does some very complex stuff and --verifytypes has few to no ways of ignoring specific errors.

If this check is giving you false alarms, you can ignore them by adding logic to `has_docstring_at_runtime`, in the main loop in `check_type`, or by updating the json file.
"""
from __future__ import annotations

# this file is not run as part of the tests, instead it's run standalone from check.sh
import argparse
import json
import subprocess
import sys
from pathlib import Path

import trio
import trio.testing

# not needed if everything is working, but if somebody does something to generate
# tons of errors, we can be nice and stop them from getting 3*tons of output
printed_diagnostics: set[str] = set()


# TODO: consider checking manually without `--ignoreexternal`, and/or
# removing it from the below call later on.
def run_pyright(platform: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [
            "pyright",
            # Specify a platform and version to keep imported modules consistent.
            f"--pythonplatform={platform}",
            "--pythonversion=3.8",
            "--verifytypes=trio",
            "--outputjson",
            "--ignoreexternal",
        ],
        capture_output=True,
    )


def has_docstring_at_runtime(name: str) -> bool:
    """Pyright gives us an object identifier of xx.yy.zz
    This function tries to decompose that into its constituent parts, such that we
    can resolve it, in order to check whether it has a `__doc__` at runtime and
    verifytypes misses it because we're doing overly fancy stuff.
    """
    # This assert is solely for stopping isort from removing our imports of trio & trio.testing
    # It could also be done with isort:skip, but that'd also disable import sorting and the like.
    assert trio.testing

    # figure out what part of the name is the module, so we can "import" it
    name_parts = name.split(".")
    assert name_parts[0] == "trio"
    if name_parts[1] == "tests":
        return True

    # traverse down the remaining identifiers with getattr
    obj = trio
    try:
        for obj_name in name_parts[1:]:
            obj = getattr(obj, obj_name)
    except AttributeError as exc:
        # asynciowrapper does funky getattr stuff
        if "AsyncIOWrapper" in str(exc) or name in (
            # Symbols not existing on all platforms, so we can't dynamically inspect them.
            # Manually confirmed to have docstrings but pyright doesn't see them due to
            # export shenanigans. TODO: actually manually confirm that.
            # In theory we could verify these at runtime, probably by running the script separately
            # on separate platforms. It might also be a decent idea to work the other way around,
            # a la test_static_tool_sees_class_members
            # darwin
            "trio.lowlevel.current_kqueue",
            "trio.lowlevel.monitor_kevent",
            "trio.lowlevel.wait_kevent",
            "trio._core._io_kqueue._KqueueStatistics",
            # windows
            "trio._socket.SocketType.share",
            "trio._core._io_windows._WindowsStatistics",
            "trio._core._windows_cffi.Handle",
            "trio.lowlevel.current_iocp",
            "trio.lowlevel.monitor_completion_key",
            "trio.lowlevel.readinto_overlapped",
            "trio.lowlevel.register_with_iocp",
            "trio.lowlevel.wait_overlapped",
            "trio.lowlevel.write_overlapped",
            "trio.lowlevel.WaitForSingleObject",
            "trio.socket.fromshare",
            # linux
            # this test will fail on linux, but I don't develop on linux. So the next
            # person to do so is very welcome to open a pull request and populate with
            # objects
            # TODO: these are erroring on all platforms, why?
            "trio._highlevel_generic.StapledStream.send_stream",
            "trio._highlevel_generic.StapledStream.receive_stream",
            "trio._ssl.SSLStream.transport_stream",
            "trio._file_io._HasFileNo",
            "trio._file_io._HasFileNo.fileno",
        ):
            return True

        else:
            print(
                f"Pyright sees {name} at runtime, but unable to getattr({obj.__name__}, {obj_name}).",
                file=sys.stderr,
            )
            return False
    return bool(obj.__doc__)


def check_type(
    platform: str, full_diagnostics_file: Path | None, expected_errors: list[object]
) -> list[object]:
    # convince isort we use the trio import
    assert trio

    # run pyright, load output into json
    res = run_pyright(platform)
    current_result = json.loads(res.stdout)

    if res.stderr:
        print(res.stderr, file=sys.stderr)

    if full_diagnostics_file:
        with open(full_diagnostics_file, "a") as f:
            json.dump(current_result, f, sort_keys=True, indent=4)

    errors = []

    for symbol in current_result["typeCompleteness"]["symbols"]:
        diagnostics = symbol["diagnostics"]
        name = symbol["name"]
        for diagnostic in diagnostics:
            message = diagnostic["message"]
            if name in (
                "trio._path.PosixPath",
                "trio._path.WindowsPath",
            ) and message.startswith("Type of base class "):
                continue

            if name.startswith("trio._path.Path"):
                if message.startswith("No docstring found for"):
                    continue
                if message.startswith(
                    "Type is missing type annotation and could be inferred differently by type checkers"
                ):
                    continue

            # ignore errors about missing docstrings if they're available at runtime
            if message.startswith("No docstring found for"):
                if has_docstring_at_runtime(symbol["name"]):
                    continue
            else:
                # Missing docstring messages include the name of the object.
                # Other errors don't, so we add it.
                message = f"{name}: {message}"
            if message not in expected_errors and message not in printed_diagnostics:
                print(f"new error: {message}", file=sys.stderr)
            errors.append(message)
            printed_diagnostics.add(message)

        continue

    return errors


def main(args: argparse.Namespace) -> int:
    if args.full_diagnostics_file:
        full_diagnostics_file = Path(args.full_diagnostics_file)
        full_diagnostics_file.write_text("")
    else:
        full_diagnostics_file = None

    errors_by_platform_file = Path(__file__).parent / "_check_type_completeness.json"
    if errors_by_platform_file.exists():
        with open(errors_by_platform_file) as f:
            errors_by_platform = json.load(f)
    else:
        errors_by_platform = {"Linux": [], "Windows": [], "Darwin": [], "all": []}

    changed = False
    for platform in "Linux", "Windows", "Darwin":
        platform_errors = errors_by_platform[platform] + errors_by_platform["all"]
        print("*" * 20, f"\nChecking {platform}...")
        errors = check_type(platform, full_diagnostics_file, platform_errors)

        new_errors = [e for e in errors if e not in platform_errors]
        missing_errors = [e for e in platform_errors if e not in errors]

        if new_errors:
            print(
                f"New errors introduced in `pyright --verifytypes`. Fix them, or ignore them by modifying {errors_by_platform_file}, either manually or with '--overwrite-file'.",
                file=sys.stderr,
            )
            changed = True
        if missing_errors:
            print(
                f"Congratulations, you have resolved existing errors! Please remove them from {errors_by_platform_file}, either manually or with '--overwrite-file'.",
                file=sys.stderr,
            )
            changed = True
            print(missing_errors, file=sys.stderr)

        errors_by_platform[platform] = errors
    print("*" * 20)

    # cut down the size of the json file by a lot, and make it easier to parse for
    # humans, by moving errors that appear on all platforms to a separate category
    errors_by_platform["all"] = []
    for e in errors_by_platform["Linux"].copy():
        if e in errors_by_platform["Darwin"] and e in errors_by_platform["Windows"]:
            for platform in "Linux", "Windows", "Darwin":
                errors_by_platform[platform].remove(e)
            errors_by_platform["all"].append(e)

    if changed and args.overwrite_file:
        with open(errors_by_platform_file, "w") as f:
            json.dump(errors_by_platform, f, indent=4, sort_keys=True)
            # newline at end of file
            f.write("\n")

    # True -> 1 -> non-zero exit value -> error
    return changed


parser = argparse.ArgumentParser()
parser.add_argument(
    "--overwrite-file",
    action="store_true",
    default=False,
    help="Use this flag to overwrite the current stored results. Either in CI together with a diff check, or to avoid having to manually correct it.",
)
parser.add_argument(
    "--full-diagnostics-file",
    type=Path,
    default=None,
    help="Use this for debugging, it will dump the output of all three pyright runs by platform into this file.",
)
args = parser.parse_args()

assert __name__ == "__main__", "This script should be run standalone"
sys.exit(main(args))
