#!/usr/bin/env python3
"""
Limit open pull requests from new Django contributors.

Close a PR if its author has fewer than five commits on main, has another
open PR created within the past 180 days, and does not have triage, write,
maintain, or admin permissions on the repository.

Required environment variables:
    GITHUB_TOKEN  GitHub API token
    PR_NUMBER     Pull request number
    PR_REPO       Repository in "owner/repo" format

Optional environment variables:
    AUTOCLOSE     Set to "true" to comment and close (default: false)
"""

import logging
import os
import sys
import urllib.error
from datetime import datetime, timedelta, timezone
from http import HTTPStatus

from github import (
    get_comment_ids_containing_marker,
    get_recent_commit_count,
    github_request,
    github_results,
)

GITHUB_PER_PAGE = 100
MIN_COMMITS = 5
LOOKBACK_DAYS = 180  # Approximately six months.
EXEMPT_ROLES = {"triage", "write", "maintain", "admin"}
COMMENT_MARKER = "<!-- django-pr-limit -->"

logger = logging.getLogger(__name__)


def has_exempt_permissions(pr_author, repo, token):
    """Return whether the author has an exempt repository role."""
    try:
        permissions = github_request(
            "GET", f"/collaborators/{pr_author}/permission", token, repo
        )
    except urllib.error.HTTPError as exc:
        code = exc.code
        exc.close()
        if code == HTTPStatus.NOT_FOUND:
            # GitHub may return 404 for a user who is not a collaborator.
            return False
        raise
    return permissions["role_name"] in EXEMPT_ROLES


def get_other_open_prs(pr_number, pr_author, repo, token, cutoff):
    """Return the author's other open PRs created on or after cutoff."""
    matches = []
    for pr in github_results(
        "/issues",
        repo,
        token,
        params={
            "creator": pr_author,
            "state": "open",
            "sort": "created",
            "direction": "desc",
        },
    ):
        if datetime.fromisoformat(pr["created_at"]) < cutoff:
            break
        if pr["number"] != pr_number:
            matches.append(pr["number"])
    return matches


def comment_exists(pr_number, repo, token):
    """Return whether this workflow has already explained the PR limit."""
    return bool(
        get_comment_ids_containing_marker(pr_number, repo, token, marker=COMMENT_MARKER)
    )


def get_closing_message(other_pr_numbers):
    """Build the explanation, including links to the author's existing PRs."""
    other_prs = ", ".join(f"#{number}" for number in sorted(other_pr_numbers))
    return (
        f"{COMMENT_MARKER}\n\n"
        "Thank you for contributing to Django!\n\n"
        f"Since you have fewer than {MIN_COMMITS} commits on Django's `main` "
        "branch and already have an open pull request created within the past "
        f"{LOOKBACK_DAYS} days ({other_prs}), please finish or close that "
        "pull request before opening another. We are closing this pull request "
        "because you have reached this limit.\n\n"
        "Please focus on your existing pull request and any outstanding review "
        "feedback. If you would prefer to work on this issue, you can close "
        "your existing pull request and unassign yourself from its associated "
        "ticket so someone else can take it on and leave a comment here asking "
        "for this pull request to be reopened."
    )


def main(repo, token, pr_number, autoclose=False, now=None):
    pr_number = int(pr_number)
    now = now if now is not None else datetime.now(timezone.utc)
    pr = github_request("GET", f"/pulls/{pr_number}", token, repo)
    if pr["state"] != "open":
        logger.info("PR #%s is already closed -- skipping.", pr_number)
        return 0

    author = pr["user"]["login"]
    if has_exempt_permissions(author, repo, token):
        logger.info("PR #%s author has exempt repository permissions.", pr_number)
        return 0

    commit_count = get_recent_commit_count(
        author, repo, token, since_days=None, max_count=MIN_COMMITS
    )
    if commit_count >= MIN_COMMITS:
        logger.info("PR #%s author meets the commit threshold.", pr_number)
        return 0

    cutoff = now - timedelta(days=LOOKBACK_DAYS)
    others = get_other_open_prs(pr_number, author, repo, token, cutoff)
    if not others:
        logger.info("PR #%s author has no other recent open PRs.", pr_number)
        return 0

    logger.info(
        "PR #%s exceeds the limit; other recent open PRs: %s.",
        pr_number,
        ", ".join(f"#{number}" for number in others),
    )
    if not autoclose:
        logger.info(
            "AUTOCLOSE is disabled -- would comment and close PR #%s.",
            pr_number,
        )
        return 0

    # Do not comment if the target PR was closed while checks were running.
    pr = github_request("GET", f"/pulls/{pr_number}", token, repo)
    if pr["state"] != "open":
        return 0

    # Post the explanation first. If commenting fails, leave the PR open.
    if not comment_exists(pr_number, repo, token):
        github_request(
            "POST",
            f"/issues/{pr_number}/comments",
            token,
            repo,
            {"body": get_closing_message(others)},
        )
    github_request("PATCH", f"/pulls/{pr_number}", token, repo, {"state": "closed"})
    logger.info("Closed PR #%s because its author has reached the limit.", pr_number)
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    sys.exit(
        main(
            repo=os.environ["PR_REPO"],
            token=os.environ["GITHUB_TOKEN"],
            pr_number=os.environ["PR_NUMBER"],
            autoclose=os.environ.get("AUTOCLOSE", "").lower() == "true",
        )
    )
