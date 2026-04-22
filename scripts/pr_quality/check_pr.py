#!/usr/bin/env python3
"""
PR quality checks for Django pull requests.

Each check is an independent function that returns None on success, or an
error message on failure. Independent checks are all run so that all issues
are reported in a single pass. Trac status and has_patch checks are skipped
when no ticket is found, since they require a ticket ID to be meaningful.

Required environment variables:
    GITHUB_TOKEN  GitHub API token
    PR_NUMBER     Pull request number
    PR_REPO       Repository in "owner/repo" format

Optional environment variables:
    AUTOCLOSE     Set to "true" to close failing PRs (default: false)
    PR_AUTHOR     PR author's GitHub login
    PR_BODY       Pull request body text
    PR_CREATED_AT PR creation timestamp (ISO 8601)
    PR_TITLE      Pull request title
"""

import json
import logging
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone

from pr_quality.errors import (
    CHECKS_FOOTER,
    CHECKS_HEADER,
    INCOMPLETE_CHECKLIST,
    INVALID_TRAC_STATUS,
    LEVEL_ERROR,
    LEVEL_WARNING,
    MISSING_AI_DESCRIPTION,
    MISSING_AI_DISCLOSURE,
    MISSING_DESCRIPTION,
    MISSING_HAS_PATCH_FLAG,
    MISSING_TICKET_IN_PR_TITLE,
    MISSING_TRAC_TICKET,
    Message,
)

GITHUB_PER_PAGE = 100
LARGE_PR_THRESHOLD = 80  # additions + deletions
MIN_WORDS = 5
SKIPPED = object()  # Sentinel: check was not applicable and was skipped.
TICKET_NOT_FOUND = object()  # Sentinel: Trac returned HTTP 404 for the ticket.
URLOPEN_TIMEOUT_SECONDS = 15
# PRs opened before these dates predate PR template additions.
PR_TEMPLATE_DATE = date(2024, 3, 4)  # 3fcef50 -- PR template introduced
AI_DISCLOSURE_DATE = date(2026, 1, 8)  # 4f580c4 -- AI disclosure added

ALLOWED_STAGES = ("Accepted", "Ready for checkin")

logger = logging.getLogger(__name__)


def setup_logging(logger, gha_formatter=True):
    logger.setLevel(logging.DEBUG)

    if not logger.handlers and gha_formatter:

        class GHAFormatter(logging.Formatter):
            _PREFIXES = {
                logging.DEBUG: "::debug::",
                logging.INFO: "::notice::",
                logging.WARNING: "::warning::",
                logging.ERROR: "::error::",
            }

            def format(self, record):
                msg = super().format(record)
                prefix = self._PREFIXES.get(record.levelno, "")
                return f"{prefix}{msg}"

        handler = logging.StreamHandler()
        handler.setFormatter(GHAFormatter())
        logger.addHandler(handler)


def github_request(method, path, token, repo, data=None, params=None):
    """Make an authenticated GitHub API request."""
    url = f"https://api.github.com/repos/{repo}{path}"
    if params:
        encoded_params = urllib.parse.urlencode(params)
        url = f"{url}?{encoded_params}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    body = None
    if data is not None:
        body = json.dumps(data).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=URLOPEN_TIMEOUT_SECONDS) as response:
        return json.loads(response.read())


def get_recent_commit_count(pr_author, repo, token, since_days, max_count):
    """Return the number of recent commits by the author, up to max_count."""
    if not pr_author:
        return 0

    since = (datetime.now(timezone.utc) - timedelta(days=since_days)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    results = github_request(
        "GET",
        "/commits",
        token,
        repo,
        params={"author": pr_author, "since": since, "per_page": max_count},
    )
    return len(results)


def get_pr_total_changes(pr_number, repo, token):
    """Return total lines changed in the PR (additions + deletions)."""
    total_changes = 0
    page = 1
    while True:
        results = github_request(
            "GET",
            f"/pulls/{pr_number}/files",
            token,
            repo,
            params={"per_page": GITHUB_PER_PAGE, "page": page},
        )
        if not results:
            break
        total_changes += sum(f["changes"] for f in results)
        if len(results) < GITHUB_PER_PAGE:
            break
        page += 1
    return total_changes


def strip_html_comments(text):
    """Return text with all HTML comments removed."""
    return re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)


def extract_ticket_id(pr_body):
    """Return the Trac ticket ID string from the PR body, or None."""
    match = re.search(r"\bticket-(\d+)\b", pr_body, re.IGNORECASE)
    return match.group(1) if match else None


def fetch_trac_ticket(ticket_id):
    """Fetch ticket data from the Trac JSON API.

    Returns a dict with ticket data on success, TICKET_NOT_FOUND if the
    ticket does not exist (HTTP 404), or None on a non-fatal network error
    (the caller should skip the check).
    """
    url = f"https://www.djangoproject.com/trac/api/tickets/{ticket_id}"
    try:
        with urllib.request.urlopen(url, timeout=URLOPEN_TIMEOUT_SECONDS) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as exc:
        code = exc.code
        exc.close()
        if code == 404:
            return TICKET_NOT_FOUND
        logger.warning(
            "HTTP %s fetching ticket %s -- skipping Trac check.",
            code,
            ticket_id,
        )
        return None
    except Exception as exc:
        logger.warning(
            "Could not fetch ticket %s: %s -- skipping Trac check.",
            ticket_id,
            exc,
        )
        return None


def check_trac_ticket(pr_body, total_changes, threshold=LARGE_PR_THRESHOLD):
    """A Trac ticket must be referenced in the ticket section.

    For PRs with fewer than threshold lines changed, "N/A" is also accepted
    (e.g. for typo fixes). Larger PRs must reference a ticket.
    """
    # Look for the ticket reference inside the Trac ticket number section.
    section_match = re.search(
        r"#### Trac ticket number[^\n]*\n(.*?)(?=\r?\n####|\Z)",
        pr_body,
        re.DOTALL,
    )
    section = section_match.group(1) if section_match else pr_body

    # Strip HTML comments before checking -- the template itself contains "N/A"
    # inside a comment, which would otherwise trigger the N/A exemption below.
    section = strip_html_comments(section)

    if re.search(r"\bticket-\d+\b", section, re.IGNORECASE):  # valid ticket found
        return None

    # N/A is accepted for trivial PRs that don't warrant a ticket.
    if total_changes < threshold and re.search(
        r"(?:^|\s)N/A\b", section, re.IGNORECASE | re.MULTILINE
    ):
        return None

    return Message(*MISSING_TRAC_TICKET, threshold=threshold)


def check_trac_status(ticket_id, ticket_data):
    """The referenced Trac ticket must be Accepted or Ready for checkin,
    unresolved, and assigned.

    ticket_data is the dict returned by fetch_trac_ticket(). Passing None
    skips the check (non-fatal fetch error). Passing TICKET_NOT_FOUND fails
    with a generic not-ready message.
    """
    if ticket_data is None:
        return None  # Non-fatal fetch error; skip.
    if ticket_data is TICKET_NOT_FOUND:
        return Message(
            *INVALID_TRAC_STATUS,
            ticket_id=ticket_id,
            current_state="ticket not found in Trac",
        )
    stage = ticket_data.get("custom", {}).get("stage", "").strip()
    resolution = (ticket_data.get("resolution") or "").strip()
    status = ticket_data.get("status", "").strip()
    if stage in ALLOWED_STAGES and not resolution and status == "assigned":
        return None
    current_state = [
        f"{stage=}" if stage not in ALLOWED_STAGES else "",
        f"{resolution=}" if resolution else "",
        f"{status=}" if status != "assigned" else "",
    ]
    return Message(
        *INVALID_TRAC_STATUS,
        ticket_id=ticket_id,
        current_state=", ".join(s for s in current_state if s),
    )


def check_trac_has_patch(ticket_id, initial_data, poll_interval=1, poll_timeout=10):
    """The referenced Trac ticket must have has_patch=1.

    Uses initial_data (the dict returned by fetch_trac_ticket()) on the first
    check, then polls via fetch_trac_ticket() every poll_interval seconds for
    up to poll_timeout seconds. Set poll_timeout=0 for a single check with no
    retries. Passing None for initial_data skips the check entirely.
    """
    deadline = time.monotonic() + poll_timeout
    elapsed = 0
    ticket_data = initial_data

    while True:
        logger.info(
            "Checking has_patch flag for ticket-%s (elapsed: %ss) ...",
            ticket_id,
            elapsed,
        )
        if ticket_data is None:
            return None  # Non-fatal fetch error; skip.
        if ticket_data is TICKET_NOT_FOUND:
            # Ticket not found -- already reported by check_trac_status.
            return None
        has_patch = ticket_data.get("custom", {}).get("has_patch", "0").strip()
        if has_patch == "1":
            logger.info("ticket-%s has_patch flag is set.", ticket_id)
            return None
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        logger.info(
            "  has_patch not yet set -- will retry in %ss.",
            poll_interval,
        )
        sleep_time = min(poll_interval, remaining)
        time.sleep(sleep_time)
        elapsed += int(sleep_time)
        ticket_data = fetch_trac_ticket(ticket_id)

    logger.warning(
        "ticket-%s has_patch flag was not set after %ss.",
        ticket_id,
        poll_timeout,
    )
    return Message(*MISSING_HAS_PATCH_FLAG, ticket_id=ticket_id)


def check_pr_title_has_ticket(pr_title, ticket_id):
    """The PR title must include the ticket number (e.g. #36991).

    This enables Trac's auto-link feature, which associates the PR with the
    ticket when the title follows the commit message format.
    """
    if re.search(rf"#{ticket_id}\b", pr_title):
        return None
    return Message(*MISSING_TICKET_IN_PR_TITLE, ticket_id=ticket_id)


def check_branch_description(pr_body):
    """The branch description must be present.

    The description should not contain the placeholder, and should be at least
    5 words long.
    """
    placeholder = (
        "Provide a concise overview of the issue or rationale behind the"
        " proposed changes."
    )

    description_match = re.search(
        r"#### Branch description[ \t]*\r?\n(.*?)(?=\r?\n####|\Z)",
        pr_body,
        re.DOTALL,
    )
    if not description_match:
        return Message(*MISSING_DESCRIPTION)

    # Strip HTML comments before evaluating content.
    cleaned = strip_html_comments(description_match.group(1)).strip()

    if not cleaned or placeholder in cleaned or len(cleaned.split()) < MIN_WORDS:
        return Message(*MISSING_DESCRIPTION)

    return None


def check_ai_disclosure(pr_body):
    """Exactly one AI disclosure checkbox must be selected.

    If the "AI tools were used" option is checked, at least 5 words of
    additional description must be present in that section.
    """
    ai_match = re.search(
        r"#### AI Assistance Disclosure[^\n]*\n(.*?)(?=\r?\n####|\Z)",
        pr_body,
        re.DOTALL,
    )
    if not ai_match:
        return Message(*MISSING_AI_DISCLOSURE)

    section = strip_html_comments(ai_match.group(1))
    no_ai_checked = bool(
        re.search(r"-\s*\[x\].*?No AI tools were used", section, re.IGNORECASE)
    )
    ai_used_checked = bool(
        re.search(r"-\s*\[x\].*?If AI tools were used", section, re.IGNORECASE)
    )

    # Must check exactly one option.
    if no_ai_checked == ai_used_checked:
        return Message(*MISSING_AI_DISCLOSURE)

    if ai_used_checked:
        # Collect non-checkbox lines for word count.
        extra_lines = [
            line.strip()
            for line in section.splitlines()
            if line.strip() and not line.strip().startswith("- [")
        ]
        # Ensure PR author includes at least 5 words about their AI use.
        if len(" ".join(extra_lines).split()) < MIN_WORDS:
            return Message(*MISSING_AI_DESCRIPTION)

    return None


def check_checklist(pr_body):
    """The first five items in the Checklist section must be checked."""
    checklist_match = re.search(
        r"#### Checklist[ \t]*\r?\n(.*?)(?=\r?\n####|\Z)", pr_body, re.DOTALL
    )
    if not checklist_match:
        return Message(*INCOMPLETE_CHECKLIST)

    checkboxes = re.findall(r"-\s*\[(.)\]", checklist_match.group(1))

    if len(checkboxes) < 5 or not all(c.lower() == "x" for c in checkboxes[:5]):
        return Message(*INCOMPLETE_CHECKLIST)

    return None


def write_job_summary(pr_number, results, summary_file=None):
    """Write a Markdown job summary to the given file path (if provided)."""
    if not summary_file:
        return

    lines = [
        f"## PR #{pr_number} Quality Check Results\n",
        "| | Check | Result |",
        "| --- | --- | --- |",
    ]
    for name, result, level in results:
        if result is SKIPPED:
            icon, status = "⏭️", "Skipped"
        elif result is None:
            icon, status = "✅", "Passed"
        else:
            icon, status = level
        lines.append(f"| {icon} | {name} | {status} |")

    with open(summary_file, "a") as f:
        f.write("\n".join(lines) + "\n")


def main(
    repo,
    token,
    pr_author,
    pr_body,
    pr_number,
    pr_title="",
    pr_created_at=None,
    autoclose=True,
    summary_file=None,
    gha_formatter=False,
):
    setup_logging(logger, gha_formatter)

    created_date = (
        datetime.fromisoformat(pr_created_at).date() if pr_created_at else None
    )
    if created_date is not None and created_date <= PR_TEMPLATE_DATE:
        logger.info(
            "PR #%s is older than PR template (%s) -- skipping all checks.",
            pr_number,
            PR_TEMPLATE_DATE,
        )
        return

    commit_count = get_recent_commit_count(
        pr_author, repo, token, since_days=365 * 3, max_count=5
    )
    if commit_count >= 5:
        logger.info(
            "PR #%s author is an established contributor -- skipping all checks.",
            pr_number,
        )
        return

    pr_title_result = SKIPPED
    total_changes = get_pr_total_changes(pr_number, repo, token)
    ticket_result = check_trac_ticket(pr_body, total_changes)
    ticket_status_result = SKIPPED
    ticket_has_patch_result = SKIPPED
    ticket_id = extract_ticket_id(pr_body) if ticket_result is None else None
    if ticket_id:
        pr_title_result = check_pr_title_has_ticket(pr_title, ticket_id)
        ticket_data = fetch_trac_ticket(ticket_id)
        ticket_status_result = check_trac_status(ticket_id, ticket_data)
        if ticket_status_result is None:
            # Polling is disabled (poll_timeout=0): has_patch is a non-fatal
            # warning, and contributors often update Trac after reviewing their
            # PR, making any fixed polling window unreliable.
            ticket_has_patch_result = check_trac_has_patch(
                ticket_id, ticket_data, poll_timeout=0
            )
        else:
            logger.info("Trac ticket is not Accepted -- skipping has_patch check.")
    else:
        logger.info("No Trac ticket -- skipping status and has_patch checks.")

    if created_date is not None and created_date <= AI_DISCLOSURE_DATE:
        ai_disclosure_result = SKIPPED
        logger.info(
            "PR #%s is older than AI Disclosure section (%s) -- skipping AI checks.",
            pr_number,
            AI_DISCLOSURE_DATE,
        )
    else:
        ai_disclosure_result = check_ai_disclosure(pr_body)

    results = [
        ("Trac ticket referenced", ticket_result, LEVEL_ERROR),
        ("Trac ticket is ready for work", ticket_status_result, LEVEL_ERROR),
        ("Trac ticket has_patch flag set", ticket_has_patch_result, LEVEL_WARNING),
        ("PR title includes ticket number", pr_title_result, LEVEL_WARNING),
        ("Branch description provided", check_branch_description(pr_body), LEVEL_ERROR),
        ("AI disclosure completed", ai_disclosure_result, LEVEL_ERROR),
        ("Checklist completed", check_checklist(pr_body), LEVEL_ERROR),
    ]
    write_job_summary(pr_number, results, summary_file)

    failures = [
        msg.as_details(level=level)
        for _, msg, level in results
        if msg is not None and msg is not SKIPPED and level == LEVEL_ERROR
    ]
    warning_msgs = [
        msg.as_details(level=level)
        for _, msg, level in results
        if msg is not None and msg is not SKIPPED and level == LEVEL_WARNING
    ]
    if not failures and not warning_msgs:
        logger.info("PR #%s passed all quality checks.", pr_number)
        return

    github_request(
        "POST",
        f"/issues/{pr_number}/comments",
        token,
        repo,
        {"body": "\n\n".join([CHECKS_HEADER, *failures, *warning_msgs, CHECKS_FOOTER])},
    )
    if not failures:
        logger.warning(
            "PR #%s has %s warning(s), adding informational comment.",
            pr_number,
            len(warning_msgs),
        )
        return

    msg = "PR #%s failed %s check(s), adding comment with details."
    if not autoclose or commit_count > 0:
        logger.warning(
            msg + " Not closing the PR given %s.",
            pr_number,
            len(failures),
            "warning-only mode" if not autoclose else "recent contributions",
        )
    else:
        logger.error(
            msg + " Closing the PR given lack of recent contributions.",
            pr_number,
            len(failures),
        )
        github_request("PATCH", f"/pulls/{pr_number}", token, repo, {"state": "closed"})
    return 1


if __name__ == "__main__":
    sys.exit(
        main(
            repo=os.environ["PR_REPO"],
            token=os.environ["GITHUB_TOKEN"],
            pr_author=os.environ.get("PR_AUTHOR", ""),
            pr_body=os.environ.get("PR_BODY", ""),
            pr_number=os.environ["PR_NUMBER"],
            pr_title=os.environ.get("PR_TITLE", ""),
            pr_created_at=os.environ.get("PR_CREATED_AT"),
            autoclose=os.environ.get("AUTOCLOSE", "").lower() == "true",
            summary_file=os.environ.get("GITHUB_STEP_SUMMARY"),
            gha_formatter=os.environ.get("GITHUB_ACTIONS"),
        )
    )
