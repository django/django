#! /usr/bin/env python

"""
prepare-commit-msg hook for Django's repository.

Adjusts commit messages on any branch:
- Ensures the summary line ends with a period.

Additionally, on stable branches:
- Adds the [A.B.x] branch prefix if missing.
- Adds "Backport of <sha> from main." when cherry-picking.

To install:
  1. Ensure the folder `.git/hooks` exists.
  2. Create an executable file `.git/hooks/prepare-commit-msg` with content:

#!/bin/sh
exec python scripts/prepare_commit_msg.py "$@"

"""

import os
import subprocess
import sys


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True).stdout.strip()


def process_commit_message(lines, branch, cherry_sha=None):
    """Adjust commit message lines for a potential backport.

    - Separates body lines from trailing git comment lines.
    - Ensure all lines ends with a period.
    - On stable branches, adds the [A.B.x] prefix to the first line if missing.
    - If cherry_sha is provided, appends "Backport of <sha> from main." to
      the body if not already present.

    Returns the modified lines (body + comments).

    """
    # Separate body lines from trailing git comment lines.
    comment_start = len(lines)
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].startswith("#"):
            comment_start = i
        elif lines[i].strip():
            break

    body_lines = lines[:comment_start]
    comment_lines = lines[comment_start:]

    # Strip leading and trailing blank lines from the body.
    while body_lines and not body_lines[0].strip():
        body_lines.pop(0)
    while body_lines and not body_lines[-1].strip():
        body_lines.pop()

    # Nothing to do if the body is empty.
    if not body_lines:
        return lines

    summary = body_lines[0].strip()

    # Ensure summary ends with a period.
    if not summary.endswith("."):
        summary += "."

    # On stable branches, add the [A.B.x] prefix if missing.
    prefix = None
    if branch.startswith("stable/"):
        version = branch[len("stable/") :]
        prefix = f"[{version}] "
        if not summary.startswith(prefix):
            summary = prefix + summary

    # Capitalize the first character of the summary text (after any prefix).
    offset = len(prefix) if prefix else 0
    summary = summary[:offset] + summary[offset].upper() + summary[offset + 1 :]

    body_lines[0] = summary + "\n"

    # Add "Backport of <sha> from main." if cherry-picking and not present.
    if cherry_sha:
        backport_note = f"Backport of {cherry_sha} from main."
        if backport_note not in "".join(body_lines):
            # Strip trailing blank lines, then append note with separator.
            while body_lines and not body_lines[-1].strip():
                body_lines.pop()
            body_lines.append("\n")
            body_lines.append(backport_note + "\n")

    return body_lines + comment_lines


if __name__ == "__main__":
    msg_path = sys.argv[1]

    with open(msg_path, encoding="utf-8") as f:
        lines = f.readlines()

    branch = run(["git", "branch", "--show-current"])

    cherry_sha = None
    git_dir = run(["git", "rev-parse", "--git-dir"])
    cherry_pick_head_path = os.path.join(git_dir, "CHERRY_PICK_HEAD")
    if os.path.exists(cherry_pick_head_path):
        with open(cherry_pick_head_path, encoding="utf-8") as f:
            cherry_sha = f.read().strip()

    result = process_commit_message(lines, branch, cherry_sha)

    with open(msg_path, "w", encoding="utf-8") as f:
        f.writelines(result)
