#!/usr/bin/env python
#
# Rename EMAIL_PROVIDERS to MAILERS (and related renaming) in all commits on
# the current branch.
#
# (With assistance from GPT-5.5.)
#
# Strategy: apply the renaming within patch files, which limits the
# substitutions to the specific lines related to these changes.
#   1. Export patch files for all commits on the branch
#   2. Edit the patch files to reflect the renaming
#      (in both modified/added and context lines)
#   3. Switch to a new branch, rewound to the start of this one
#   4. Apply the modified patches in sequence to recreate
#      the original commits with the new naming
#
# Black, flake8, and other linters are deliberately *not* applied in step 4,
# to avoid conflicts with the unapplied patches. Correcting formatting issues
# is left as an exercise for the reader.
#
# This strategy should be effective for code, including docstrings and
# comments. Documentation will likely require significant additional editing.

import argparse
import re
import subprocess
import sys
from pathlib import Path
from textwrap import dedent

replacements: list[tuple[re.Pattern, str]] = [
    # Case-preserving substitutions, most to least specific.
    # This takes advantage of the fact that plural forms will already have
    # the "S" in the correct case, so we can just replace the singular portion.
    (re.compile(r"EMAIL_PROVIDER"), "MAILER"),
    (re.compile(r"EmailProvider"), "Mailer"),
    (re.compile(r"Email\s+provider"), "Mailer"),
    (re.compile(r"email\s+provider"), "mailer"),
    (re.compile(r"email-provider"), "mailer"),
    (re.compile(r"email_provider"), "mailer"),
    (re.compile(r"Provider"), "Mailer"),
    (re.compile(r"provider"), "mailer"),
]


def rewrite_text(text: str) -> str:
    for pattern, replacement in replacements:
        text = pattern.sub(replacement, text)
    return text


def rewrite_patch(patch_path: Path) -> bool:
    old = patch_path.read_text(encoding="utf-8")
    lines = old.splitlines(keepends=True)

    new_lines = []
    in_headers = True
    in_trailers = False
    in_docs_diff = False
    for line in lines:
        new_line = line
        if line.startswith("diff --git "):
            in_headers = False
            in_docs_diff = line.startswith("diff --git a/docs/")
        if not in_headers and line == "-- \n":
            in_trailers = True
        if in_headers:
            # The commit message and other metadata, formatted as an email
            # message. Rewrite Subject and body text, but not other metadata.
            if not line.startswith(("From ", "From:", "Date:")):
                new_line = rewrite_text(line)
        if not (in_headers or in_trailers):
            # Inside the body of the patch. In general, we want to rewrite all
            # diffs lines _including_ '-' lines (that were likely rewritten in
            # earlier patches that created them). The exception is in the docs,
            # where "provider" is often in the previous text, and rewriting '-'
            # lines causes "patch does not apply, did you edit it by hand?"
            if (
                line.startswith(("+", "-", " "))
                and not line.startswith(("+++ ", "--- "))
                and not (in_docs_diff and line.startswith("-"))
            ):
                new_line = line[0] + rewrite_text(line[1:])
        new_lines.append(new_line)

    new = "".join(new_lines)
    if new == old:
        return False

    patch_path.write_text(new, encoding="utf-8")
    return True


def get_merge_base(old_branch: str) -> str:
    return (
        subprocess.check_output(["git", "merge-base", "main", old_branch])
        .decode()
        .strip()
    )


def generate_patches(*, patch_dir: Path, old_branch: str, merge_base: str):
    commit_range = f"{merge_base}..{old_branch}"
    run(["git", "format-patch", "--no-stat", commit_range, "-o", patch_dir])
    for patch_path in patch_dir.glob("*.patch"):
        rewrite_patch(patch_path)


def switch_to_new_branch(*, new_branch: str, merge_base: str):
    # This will error if new_branch already exists.
    run(["git", "switch", "-c", new_branch, merge_base])


def apply_patches(*, patch_dir: Path):
    patch_paths = sorted(patch_dir.glob("*.patch"))
    print(dedent("""\
        =====
        Recreating commits with renaming applied.

        If `git am` stops, resolve any conflicts and then:
            git add path/to/resolved/files
            git am --continue

        These commands may be helpful:
            git am --show-current-patch=diff
            git status

        For "patch does not apply" errors, edit the patch file and fix
        diff context and "-" lines to match the current content, then:
            git am --continue

        Or to quit so you can start over:
            git am --abort
        =====
        """))
    run(["git", "am", "--3way", *patch_paths], check=False)


def run(args: list[str | Path], **kwargs):
    print(" ".join(str(arg) for arg in args), flush=True)
    kwargs.setdefault("check", True)
    subprocess.run(args, **kwargs)


def exit_with_error(message: str):
    print(message, file=sys.stderr)
    sys.exit(1)


parser = argparse.ArgumentParser()
parser.add_argument("--patch-dir", default="patches", type=Path)
parser.add_argument("--old-branch", default="email-providers")
parser.add_argument("--new-branch", default="email-providers-rename")
parser.add_argument("--dry-run", "-n", action="store_true")

if __name__ == "__main__":
    options = parser.parse_args()

    if options.patch_dir.exists() and any(options.patch_dir.iterdir()):
        exit_with_error(
            f"Will not overwrite existing patch-dir '{options.patch_dir}'."
            " Remove it first."
        )
    # Staged changes break `git am`.
    # (Untracked changes, like a patch dir, are OK.)
    if subprocess.check_output(["git", "diff"]).decode().strip():
        exit_with_error(
            "Working directory is not clean. Commit or stash changes before running."
        )

    base = get_merge_base(options.old_branch)
    generate_patches(
        patch_dir=options.patch_dir, old_branch=options.old_branch, merge_base=base
    )
    if options.dry_run:
        print("Patches generated. To continue, run:")
        print(f"  git switch -c {options.new_branch} {base}")
        print(f"  git am --3way {options.patch_dir}/*.patch")
    else:
        switch_to_new_branch(new_branch=options.new_branch, merge_base=base)
        apply_patches(patch_dir=Path(options.patch_dir))
