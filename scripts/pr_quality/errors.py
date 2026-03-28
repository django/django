"""Error and notification messages for PR quality checks.

Message constants are plain 2-tuples of (title, body). Body strings use
str.format() placeholders; kwargs are supplied at Message() construction time.

"""

LEVEL_ERROR = ("🛑", "Error")
LEVEL_WARNING = ("⚠️", "Warning")


class Message:
    """A PR quality check message bound to its runtime formatting kwargs."""

    def __init__(self, title, body, **kwargs):
        self.title = title
        self.body = body
        self.kwargs = kwargs

    def as_details(self, level=LEVEL_ERROR):
        body = self.body.format(**self.kwargs) if self.kwargs else self.body
        symbol, label = level
        return (
            f"<details>\n<summary><strong>{symbol} {label}: {self.title}"
            f"</strong></summary>\n\n{body}\n\n</details>"
        )


CONTRIBUTING_URL = "https://docs.djangoproject.com/en/dev/internals/contributing/"
SUBMITTING_URL = f"{CONTRIBUTING_URL}writing-code/submitting-patches/"
TRIAGING_URL = f"{CONTRIBUTING_URL}triaging-tickets/"
FORUM_URL = "https://forum.djangoproject.com"
TRAC_URL = "https://code.djangoproject.com"


CHECKS_HEADER = (
    "Thank you for your contribution to Django! This pull request has one or more "
    "items that need attention before it can be accepted for review."
)

CHECKS_FOOTER = (
    "If you have questions about these requirements, please review the "
    f"[contributing guidelines]({SUBMITTING_URL}) or ask for help on the "
    f"[Django Forum]({FORUM_URL}/c/internals/mentorship/10)."
)

INCOMPLETE_CHECKLIST = (
    "Incomplete Checklist",
    "The items in the **Checklist** section must be all understood and checked "
    "accordingly before this PR can be accepted. These items confirm that you have "
    f"read and followed the [Django contributing guidelines]({SUBMITTING_URL}).\n\n"
    "**What to do:**\n\n"
    "- Review each item and change `[ ]` to `[x]` once you have completed it.",
)

INVALID_TRAC_STATUS = (
    "Trac Ticket Not Ready for a Pull Request",
    "The referenced ticket **ticket-{ticket_id}** is not ready for a pull request. "
    "A ticket must be in the *Accepted* stage, *assigned* status, and have no "
    "resolution.\n\n"
    "**Current state:** {current_state}\n\n"
    "**What to do:**\n\n"
    f"1. Check the ticket at {TRAC_URL}/ticket/{{ticket_id}}.\n"
    "2. If *Unreviewed*, wait for a community member to accept it. "
    "A ticket cannot be accepted by its reporter.\n"
    "3. If *Ready for Checkin*, there is already a solution for it.\n"
    "4. If *Someday/Maybe*, discuss on the "
    f"[Django Forum]({FORUM_URL}/c/internals/5) before proceeding.\n"
    "5. If resolved or closed, it is not eligible for a PR.\n"
    "6. If not *assigned*, claim it by setting yourself as the owner.\n\n"
    f"For more information on the Django triage process see {TRIAGING_URL}.",
)

MISSING_AI_DESCRIPTION = (
    "AI Tool Usage Not Described",
    "You indicated that AI tools were used in preparing this PR, but you have not "
    "provided a description of which tools you used or how you used them. At least "
    "5 words of description are required.\n\n"
    "**What to do:**\n\n"
    "Add a brief description below the checked AI disclosure checkbox in your PR "
    "description. For example:\n\n"
    "```\n"
    "- [x] **If AI tools were used**, I have disclosed which ones, and fully reviewed "
    "and verified their output.\n\n"
    "Used GitHub Copilot for initial code generation. All output was manually "
    "reviewed, tested, and verified for correctness.\n"
    "```\n\n"
    "Your description should cover:\n\n"
    "- Which AI tool(s) and versions you used (e.g. GitHub Copilot, ChatGPT, Claude)\n"
    "- How you used them (e.g. code generation, writing tests, drafting commit "
    "messages)\n"
    "- How you reviewed the generated result\n\n"
    "Please note that you are fully responsible for the correctness and quality of all "
    "content in this PR, regardless of how it was generated.",
)

MISSING_AI_DISCLOSURE = (
    "AI Tool Usage Not Disclosed",
    "You must select exactly one checkbox in the AI Assistance Disclosure section of "
    "your PR description.\n\n"
    "**What to do:**\n\n"
    "Change `[ ]` to `[x]` for either:\n\n"
    '1. "**No AI tools were used** in preparing this PR."\n\n'
    "OR\n\n"
    '2. "**If AI tools were used**, I have disclosed which ones, and fully reviewed '
    'and verified their output."\n\n'
    "**Key Requirements:**\n\n"
    "- Select only one option\n"
    "- Do not check both boxes\n"
    "- Do not leave both unchecked\n"
    "- If selecting the second option, provide details of which AI tools were used.",
)

MISSING_DESCRIPTION = (
    "Missing PR Description",
    "Your PR description must be substantive and meaningful. The placeholder text "
    '"*Provide a concise overview of the issue or rationale behind the proposed '
    'changes.*" is not acceptable.\n\n'
    "**What to do:**\n\n"
    "Write a description that contains at least 5 words and addresses:\n\n"
    "- What problem does this PR solve?\n"
    "- Why is this change necessary?\n"
    "- What approach did you take?\n\n"
    "A meaningful description helps reviewers understand the intent of your change "
    "quickly and increases the likelihood that your PR will be reviewed promptly.",
)

MISSING_HAS_PATCH_FLAG = (
    "Incorrect Trac Ticket Flag",
    "The referenced ticket **ticket-{ticket_id}** does not have the *Has patch* "
    "flag set in Trac. This flag must be checked before a pull request can be "
    "reviewed.\n\n"
    "**What to do:**\n\n"
    f"1. Open the ticket at {TRAC_URL}/ticket/{{ticket_id}}.\n"
    "2. Scroll down and check the *Has patch* checkbox on the ticket.\n"
    "3. Save the ticket.\n\n"
    f"For more information see {TRIAGING_URL}#has-patch.",
)

MISSING_TICKET_IN_PR_TITLE = (
    "Ticket Number Missing from PR Title",
    "The PR title does not include the ticket number **#{ticket_id}**. Including "
    "it allows Trac to automatically link this pull request to the ticket.\n\n"
    "**What to do:**\n\n"
    "Edit the PR title to follow the commit message format, for example:\n\n"
    "`Fixed #{ticket_id} -- <description>.`",
)

MISSING_TRAC_TICKET = (
    "Missing Trac Ticket",
    "This PR does not include a valid Trac ticket reference.\n\n"
    "**What to do:**\n\n"
    f"1. Visit {TRAC_URL} and find or file the appropriate ticket for your change.\n"
    "2. Wait for the ticket to be triaged and accepted before submitting a PR. "
    "Patches submitted against unreviewed tickets are unlikely to be merged.\n"
    "3. Edit the **Trac ticket number** section of your PR description to include "
    "the ticket in the format `ticket-NNNNN` (e.g. `ticket-36991`).\n\n"
    "For PRs with fewer than {threshold} lines changed (additions + deletions), you "
    "may write `N/A` in the ticket field instead (e.g. `N/A - typo fix`).",
)
