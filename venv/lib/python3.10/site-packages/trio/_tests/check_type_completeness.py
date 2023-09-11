#!/usr/bin/env python3
# this file is not run as part of the tests, instead it's run standalone from check.sh
import argparse
import json
import subprocess
import sys
from pathlib import Path

# the result file is not marked in MANIFEST.in so it's not included in the package
RESULT_FILE = Path(__file__).parent / "verify_types.json"
failed = False


# TODO: consider checking manually without `--ignoreexternal`, and/or
# removing it from the below call later on.
def run_pyright():
    return subprocess.run(
        [
            "pyright",
            # Specify a platform and version to keep imported modules consistent.
            "--pythonplatform=Linux",
            "--pythonversion=3.8",
            "--verifytypes=trio",
            "--outputjson",
            "--ignoreexternal",
        ],
        capture_output=True,
    )


def check_less_than(key, current_dict, last_dict, /, invert=False):
    global failed
    current = current_dict[key]
    last = last_dict[key]
    assert isinstance(current, (float, int))
    assert isinstance(last, (float, int))
    if current == last:
        return
    if (current > last) ^ invert:
        failed = True
        print("ERROR: ", end="")
    if isinstance(current, float):
        strcurrent = f"{current:.4}"
        strlast = f"{last:.4}"
    else:
        strcurrent = str(current)
        strlast = str(last)
    print(
        f"{key} has gone {'down' if current<last else 'up'} from {strlast} to {strcurrent}"
    )


def check_zero(key, current_dict):
    global failed
    if current_dict[key] != 0:
        failed = True
        print(f"ERROR: {key} is {current_dict[key]}")


def main(args: argparse.Namespace) -> int:
    print("*" * 20, "\nChecking type completeness hasn't gone down...")

    res = run_pyright()
    current_result = json.loads(res.stdout)
    py_typed_file: Path | None = None

    # check if py.typed file was missing
    if (
        current_result["generalDiagnostics"]
        and current_result["generalDiagnostics"][0]["message"]
        == "No py.typed file found"
    ):
        print("creating py.typed")
        py_typed_file = (
            Path(current_result["typeCompleteness"]["packageRootDirectory"])
            / "py.typed"
        )
        py_typed_file.write_text("")

        res = run_pyright()
        current_result = json.loads(res.stdout)

    if res.stderr:
        print(res.stderr)

    if args.full_diagnostics_file is not None:
        with open(args.full_diagnostics_file, "w") as file:
            json.dump(
                [
                    sym
                    for sym in current_result["typeCompleteness"]["symbols"]
                    if sym["diagnostics"]
                ],
                file,
                sort_keys=True,
                indent=2,
            )

    last_result = json.loads(RESULT_FILE.read_text())

    for key in "errorCount", "warningCount", "informationCount":
        check_zero(key, current_result["summary"])

    for key, invert in (
        ("missingFunctionDocStringCount", False),
        ("missingClassDocStringCount", False),
        ("missingDefaultParamCount", False),
        ("completenessScore", True),
    ):
        check_less_than(
            key,
            current_result["typeCompleteness"],
            last_result["typeCompleteness"],
            invert=invert,
        )

    for key, invert in (
        ("withUnknownType", False),
        ("withAmbiguousType", False),
        ("withKnownType", True),
    ):
        check_less_than(
            key,
            current_result["typeCompleteness"]["exportedSymbolCounts"],
            last_result["typeCompleteness"]["exportedSymbolCounts"],
            invert=invert,
        )

    assert (
        res.returncode != 0
    ), "Fully type complete! Delete this script and instead directly run `pyright --verifytypes=trio` (consider `--ignoreexternal`) in CI and checking exit code."

    if args.overwrite_file:
        print("Overwriting file")

        # don't care about differences in time taken
        del current_result["time"]
        del current_result["summary"]["timeInSec"]

        # don't fail on version diff so pyright updates can be automerged
        del current_result["version"]

        for key in (
            # don't save path (because that varies between machines)
            "moduleRootDirectory",
            "packageRootDirectory",
            "pyTypedPath",
        ):
            del current_result["typeCompleteness"][key]

        # prune the symbols to only be the name of the symbols with
        # errors, instead of saving a huge file.
        new_symbols = []
        for symbol in current_result["typeCompleteness"]["symbols"]:
            if symbol["diagnostics"]:
                new_symbols.append(symbol["name"])
                continue

        # Ensure order of arrays does not affect result.
        new_symbols.sort()
        current_result["generalDiagnostics"].sort()
        current_result["typeCompleteness"]["modules"].sort(
            key=lambda module: module.get("name", "")
        )

        current_result["typeCompleteness"]["symbols"] = new_symbols

        with open(RESULT_FILE, "w") as file:
            json.dump(current_result, file, sort_keys=True, indent=2)
            # add newline at end of file so it's easier to manually modify
            file.write("\n")

    if py_typed_file is not None:
        print("deleting py.typed")
        py_typed_file.unlink()

    print("*" * 20)

    return int(failed)


parser = argparse.ArgumentParser()
parser.add_argument("--overwrite-file", action="store_true", default=False)
parser.add_argument("--full-diagnostics-file", type=Path, default=None)
args = parser.parse_args()

assert __name__ == "__main__", "This script should be run standalone"
sys.exit(main(args))
