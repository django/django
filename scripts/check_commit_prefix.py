#! /usr/bin/env python

# Install this prepare-commit-msg hook with
# pre-commit install --hook-type prepare-commit-msg

import subprocess
import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
    first_line = f.readline()

commit_msg_text = subprocess.run(
    ["git", "branch", "--show-current"],
    capture_output=True,
).stdout.decode(encoding="utf-8")

stripped_branch_name = commit_msg_text.strip("stable/").strip()
if stripped_branch_name and stripped_branch_name[0].isnumeric():
    expected_prefix = f"[{stripped_branch_name}] "
    assert first_line.startswith(
        expected_prefix
    ), f"Expected {first_line!r} to start with {expected_prefix!r}"
