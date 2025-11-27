#! /usr/bin/env python3
import argparse
import os
import subprocess
import sys


def run(cmd, *, cwd=None, env=None, dry_run=True):
    """Run a command with optional dry-run behavior."""
    environ = os.environ.copy()
    if env:
        environ.update(env)
    if dry_run:
        print("[DRY RUN]", " ".join(cmd))
    else:
        print("[EXECUTE]", " ".join(cmd))
        try:
            result = subprocess.check_output(
                cmd, cwd=cwd, env=environ, stderr=subprocess.STDOUT
            )
        except subprocess.CalledProcessError as e:
            result = e.output
            print("    [ERROR]", result)
            raise
        else:
            print("    [RESULT]", result)
        return result.decode().strip()


def validate_env(checkout_dir):
    if not checkout_dir:
        sys.exit("Error: checkout directory not provided (--checkout-dir).")
    if not os.path.exists(checkout_dir):
        sys.exit(f"Error: checkout directory '{checkout_dir}' does not exist.")
    if not os.path.isdir(checkout_dir):
        sys.exit(f"Error: '{checkout_dir}' is not a directory.")


def get_remote_branches(checkout_dir, include_fn):
    """Return list of remote branches filtered by include_fn."""
    result = run(
        ["git", "branch", "--list", "-r"],
        cwd=checkout_dir,
        dry_run=False,
    )
    branches = [b.strip() for b in result.split("\n") if b.strip()]
    return [b for b in branches if include_fn(b)]


def get_branch_info(checkout_dir, branch):
    """Return (commit_hash, last_update_date) for a given branch."""
    commit_hash = run(["git", "rev-parse", branch], cwd=checkout_dir, dry_run=False)
    last_update = run(
        ["git", "show", branch, "--format=format:%ai", "-s"],
        cwd=checkout_dir,
        dry_run=False,
    )
    return commit_hash, last_update


def create_tag(checkout_dir, branch, commit_hash, last_update, *, dry_run=True):
    """Create a tag locally for a given branch at its last update."""
    tag_name = branch.replace("origin/", "", 1)
    msg = f'"Tagged {tag_name} for EOL stable branch removal."'
    run(
        ["git", "tag", "--sign", "--message", msg, tag_name, commit_hash],
        cwd=checkout_dir,
        env={"GIT_COMMITTER_DATE": last_update},
        dry_run=dry_run,
    )
    return tag_name


def delete_remote_and_local_branch(checkout_dir, branch, *, dry_run=True):
    """Delete a remote branch from origin and the maching local branch."""
    try:
        run(
            ["git", "branch", "-D", branch],
            cwd=checkout_dir,
            dry_run=dry_run,
        )
    except subprocess.CalledProcessError:
        print(f"[ERROR] Local branch {branch} can not be deleted.")

    run(
        ["git", "push", "origin", "--delete", branch.replace("origin/", "", 1)],
        cwd=checkout_dir,
        dry_run=dry_run,
    )


def main():
    parser = argparse.ArgumentParser(
        description="Archive Django branches into tags and optionally delete them."
    )
    parser.add_argument(
        "--checkout-dir", required=True, help="Path to Django git checkout"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print commands instead of executing them",
    )
    parser.add_argument(
        "--branches", nargs="*", help="Specific remote branches to include (optional)"
    )
    args = parser.parse_args()

    validate_env(args.checkout_dir)
    dry_run = args.dry_run
    checkout_dir = args.checkout_dir

    if args.branches:
        wanted = set(f"origin/{b}" for b in args.branches)
    else:
        wanted = set()

    branches = get_remote_branches(checkout_dir, include_fn=lambda b: b in wanted)
    if not branches:
        print("No branches matched inclusion criteria.")
        return

    print("\nMatched branches:")
    print("\n".join(branches))
    print()

    branch_updates = {b: get_branch_info(checkout_dir, b) for b in branches}
    print("\nLast updates:")
    for b, (h, d) in branch_updates.items():
        print(f"{b}\t{h}\t{d}")

    if (
        input("\nDelete remote branches and create tags? [y/N]: ").strip().lower()
        == "y"
    ):
        for b, (commit_hash, last_update_date) in branch_updates.items():
            print(f"Creating tag for {b} at {commit_hash=} with {last_update_date=}")
            create_tag(checkout_dir, b, commit_hash, last_update_date, dry_run=dry_run)
            print(f"Deleting remote branch {b}")
            delete_remote_and_local_branch(checkout_dir, b, dry_run=dry_run)
        run(
            ["git", "push", "--tags"],
            cwd=checkout_dir,
            dry_run=dry_run,
        )

    print("Done.")


if __name__ == "__main__":
    main()
