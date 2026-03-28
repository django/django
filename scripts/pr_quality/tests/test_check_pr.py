"""Tests for the PR quality checks in check_pr.py."""

import json
import logging
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

from pr_quality import check_pr
from pr_quality.errors import LEVEL_ERROR, LEVEL_WARNING, MISSING_TRAC_TICKET, Message

logger = logging.getLogger("pr_quality.check_pr")

UNSET = object()
ERROR_ICON, ERROR_LABEL = LEVEL_ERROR
WARNING_ICON, WARNING_LABEL = LEVEL_WARNING


def make_pr_body(
    ticket="ticket-36991",
    description=(
        "Fix regression in template rendering where nested blocks were"
        " incorrectly evaluated."
    ),
    no_ai_checked=True,
    ai_used_checked=False,
    ai_description="",
    checked_items=5,
):
    no_ai_box = "[x]" if no_ai_checked else "[ ]"
    ai_used_box = "[x]" if ai_used_checked else "[ ]"
    ai_extra = f"\n{ai_description}" if ai_description else ""

    checklist_items = [
        "This PR follows the [contribution guidelines]"
        "(https://docs.djangoproject.com/en/stable/internals/contributing/"
        "writing-code/submitting-patches/).",
        "This PR **does not** disclose a security vulnerability"
        " (see [vulnerability reporting]"
        "(https://docs.djangoproject.com/en/stable/internals/security/)).",
        "This PR targets the `main` branch."
        " <!-- Backports will be evaluated and done by mergers, when necessary. -->",
        "The commit message is written in past tense, mentions the ticket"
        " number, and ends with a period (see [guidelines]"
        "(https://docs.djangoproject.com/en/dev/internals/contributing/"
        "committing-code/#committing-guidelines)).",
        "I have not requested, and will not request, an automated AI review"
        " for this PR."
        " <!-- You are welcome to do so in your own fork. -->",
        'I have checked the "Has patch" ticket flag in the Trac system.',
        "I have added or updated relevant tests.",
        "I have added or updated relevant docs, including release notes if"
        " applicable.",
        "I have attached screenshots in both light and dark modes for any UI"
        " changes.",
    ]
    checklist_lines = "\n".join(
        f"- [x] {item}" if i < checked_items else f"- [ ] {item}"
        for i, item in enumerate(checklist_items)
    )

    # GitHub PR bodies are plain markdown with no leading spaces.
    return (
        f"#### Trac ticket number\n"
        f"<!-- Replace XXXXX with the corresponding Trac ticket number. -->\n"
        f'<!-- Or delete the line and write "N/A - typo" for typo fixes. -->\n'
        f"\n"
        f"{ticket}\n"
        f"\n"
        f"#### Branch description\n"
        f"{description}\n"
        f"\n"
        f"#### AI Assistance Disclosure (REQUIRED)\n"
        f"<!-- Please select exactly ONE of the following: -->\n"
        f"- {no_ai_box} **No AI tools were used** in preparing this PR.\n"
        f"- {ai_used_box} **If AI tools were used**, I have disclosed which"
        f" ones, and fully reviewed and verified their output.{ai_extra}\n"
        f"\n"
        f"#### Checklist\n"
        f"{checklist_lines}\n"
    )


VALID_PR_BODY = make_pr_body()
VALID_PR_TITLE = "Fixed #36991 -- Fix template rendering regression."


def make_trac_json(
    ticket_id="36991",
    stage="Accepted",
    status="assigned",
    resolution="",
    has_patch="0",
    needs_docs="0",
    needs_tests="0",
    needs_better_patch="0",
):
    return {
        "id": int(ticket_id),
        "summary": "Some summary",
        "status": status,
        "resolution": resolution,
        "custom": {
            "stage": stage,
            "has_patch": has_patch,
            "needs_docs": needs_docs,
            "needs_tests": needs_tests,
            "needs_better_patch": needs_better_patch,
        },
    }


def patch_urlopen(json_responses=(), status_code=200):
    side_effects = []
    if status_code == 200:
        for data in json_responses:
            mock_response = mock.MagicMock()
            mock_response.read.return_value = json.dumps(data).encode()
            mock_cm = mock.MagicMock()
            mock_cm.__enter__.return_value = mock_response
            side_effects.append(mock_cm)
    else:
        error = urllib.error.HTTPError(
            url="https://example.com",
            code=status_code,
            msg="Error",
            hdrs=None,
            fp=None,
        )
        side_effects.append(error)
    return mock.patch("urllib.request.urlopen", side_effect=side_effects)


class BaseTestCase(unittest.TestCase):
    def setUp(self):
        null_handler = logging.NullHandler()
        logger.addHandler(null_handler)
        self.addCleanup(logger.removeHandler, null_handler)

    def call_main(
        self,
        repo="test/repo",
        token="test-token",
        pr_author="trusted",
        pr_body="",
        pr_title="",
        pr_created_at=None,
        pr_number="10",
        total_changes=check_pr.LARGE_PR_THRESHOLD,
        commit_count=0,
        autoclose=True,
        trac_data=UNSET,
    ):
        if trac_data is UNSET:
            trac_data = make_trac_json(stage="Accepted", has_patch="1")
        with (
            mock.patch.object(
                check_pr, "get_pr_total_changes", return_value=total_changes
            ),
            mock.patch.object(
                check_pr, "get_recent_commit_count", return_value=commit_count
            ),
            mock.patch.object(check_pr, "write_job_summary") as mock_summary,
            mock.patch.object(check_pr, "github_request", mock.MagicMock()) as mock_gh,
            mock.patch.object(check_pr, "fetch_trac_ticket", return_value=trac_data),
        ):
            result = check_pr.main(
                repo=repo,
                token=token,
                pr_author=pr_author,
                pr_body=pr_body,
                pr_title=pr_title,
                pr_number=pr_number,
                pr_created_at=pr_created_at,
                autoclose=autoclose,
                gha_formatter=False,
            )
        return result, mock_summary, mock_gh


class TestExtractTicketId(BaseTestCase):
    def test_valid_ticket_returns_id(self):
        self.assertEqual(check_pr.extract_ticket_id("ticket-36991"), "36991")

    def test_ticket_in_sentence_returns_id(self):
        self.assertEqual(
            check_pr.extract_ticket_id("See ticket-12345 for details."), "12345"
        )

    def test_case_insensitive(self):
        self.assertEqual(check_pr.extract_ticket_id("TICKET-99"), "99")

    def test_no_ticket_returns_none(self):
        self.assertIsNone(check_pr.extract_ticket_id("No ticket here."))

    def test_na_returns_none(self):
        self.assertIsNone(check_pr.extract_ticket_id("N/A - typo fix"))

    def test_ticket_placeholder_returns_none(self):
        self.assertIsNone(check_pr.extract_ticket_id("ticket-XXXXX"))

    def test_returns_first_ticket_id(self):
        self.assertEqual(check_pr.extract_ticket_id("ticket-111 and ticket-222"), "111")


class TestFetchTracTicket(BaseTestCase):
    def test_success_returns_dict(self):
        data = make_trac_json(stage="Accepted", has_patch="1")
        with patch_urlopen([data]):
            result = check_pr.fetch_trac_ticket("36991")
        self.assertEqual(result["custom"]["stage"], "Accepted")
        self.assertEqual(result["custom"]["has_patch"], "1")

    def test_http_404_returns_ticket_not_found(self):
        with patch_urlopen(status_code=404):
            result = check_pr.fetch_trac_ticket("99999")
        self.assertIs(result, check_pr.TICKET_NOT_FOUND)

    def test_http_500_returns_none(self):
        with patch_urlopen(status_code=500):
            result = check_pr.fetch_trac_ticket("36991")
        self.assertIsNone(result)

    def test_network_error_returns_none(self):
        with mock.patch(
            "urllib.request.urlopen", side_effect=OSError("Connection refused")
        ):
            result = check_pr.fetch_trac_ticket("36991")
        self.assertIsNone(result)

    def test_uses_trac_api_url(self):
        data = make_trac_json()
        with patch_urlopen([data]) as mock_urlopen:
            check_pr.fetch_trac_ticket("36991")
        url_called = mock_urlopen.call_args.args[0]
        self.assertIn("djangoproject.com/trac/api/tickets/36991", url_called)


class TestCheckTracTicket(BaseTestCase):
    def test_valid_ticket_small_pr_passes(self):
        self.assertIsNone(
            check_pr.check_trac_ticket(VALID_PR_BODY, check_pr.LARGE_PR_THRESHOLD - 1)
        )

    def test_valid_ticket_large_pr_passes(self):
        self.assertIsNone(
            check_pr.check_trac_ticket(VALID_PR_BODY, check_pr.LARGE_PR_THRESHOLD)
        )

    def test_placeholder_fails(self):
        body = make_pr_body(ticket="ticket-XXXXX")
        self.assertIsNotNone(
            check_pr.check_trac_ticket(body, check_pr.LARGE_PR_THRESHOLD - 1)
        )

    def test_missing_small_pr_fails(self):
        body = make_pr_body(ticket="")
        self.assertIsNotNone(
            check_pr.check_trac_ticket(body, check_pr.LARGE_PR_THRESHOLD - 1)
        )

    def test_missing_large_pr_fails(self):
        body = make_pr_body(ticket="")
        self.assertIsNotNone(
            check_pr.check_trac_ticket(body, check_pr.LARGE_PR_THRESHOLD)
        )

    def test_na_small_pr_passes(self):
        body = make_pr_body(ticket="N/A - typo")
        self.assertIsNone(
            check_pr.check_trac_ticket(body, check_pr.LARGE_PR_THRESHOLD - 1)
        )

    def test_na_bare_small_pr_passes(self):
        body = make_pr_body(ticket="N/A")
        self.assertIsNone(
            check_pr.check_trac_ticket(body, check_pr.LARGE_PR_THRESHOLD - 1)
        )

    def test_na_large_pr_fails(self):
        body = make_pr_body(ticket="N/A - typo")
        self.assertIsNotNone(
            check_pr.check_trac_ticket(body, check_pr.LARGE_PR_THRESHOLD)
        )

    def test_na_at_threshold_fails(self):
        body = make_pr_body(ticket="N/A")
        self.assertIsNotNone(
            check_pr.check_trac_ticket(body, check_pr.LARGE_PR_THRESHOLD)
        )

    def test_na_just_below_threshold_passes(self):
        body = make_pr_body(ticket="N/A")
        self.assertIsNone(
            check_pr.check_trac_ticket(body, check_pr.LARGE_PR_THRESHOLD - 1)
        )

    def test_ticket_na_format_fails(self):
        body = make_pr_body(ticket="ticket-N/A")
        self.assertIsNotNone(
            check_pr.check_trac_ticket(body, check_pr.LARGE_PR_THRESHOLD - 1)
        )

    def test_various_ticket_lengths_pass(self):
        for ticket in ["ticket-1", "ticket-123", "ticket-999999"]:
            with self.subTest(ticket=ticket):
                body = make_pr_body(ticket=ticket)
                self.assertIsNone(
                    check_pr.check_trac_ticket(body, check_pr.LARGE_PR_THRESHOLD)
                )


class TestCheckTracStatus(BaseTestCase):
    def test_accepted_assigned_unresolved_passes(self):
        # The Trac API returns null (None) for open tickets.
        data = make_trac_json(stage="Accepted", status="assigned", resolution=None)
        self.assertIsNone(check_pr.check_trac_status("36991", data))

    def test_non_accepted_stage_fails(self):
        for stage in ["Unreviewed", "Ready for Checkin", "Someday/Maybe"]:
            with self.subTest(stage=stage):
                data = make_trac_json(stage=stage)
                self.assertIsNotNone(check_pr.check_trac_status("36991", data))

    def test_resolved_ticket_fails(self):
        for resolution in [
            "fixed",
            "wontfix",
            "duplicate",
            "invalid",
            "worksforme",
            "needsinfo",
            "needsnewfeatureprocess",
        ]:
            with self.subTest(resolution=resolution):
                data = make_trac_json(
                    stage="Accepted", status="assigned", resolution=resolution
                )
                self.assertIsNotNone(check_pr.check_trac_status("36991", data))

    def test_unassigned_ticket_fails(self):
        for status in ["new", "closed", ""]:
            with self.subTest(status=status):
                data = make_trac_json(stage="Accepted", status=status, resolution="")
                self.assertIsNotNone(check_pr.check_trac_status("36991", data))

    def test_failure_message_contains_ticket_id(self):
        data = make_trac_json(stage="Unreviewed")
        result = check_pr.check_trac_status("12345", data)
        self.assertIsInstance(result, Message)
        self.assertEqual(result.kwargs["ticket_id"], "12345")

    def test_failure_message_contains_current_state(self):
        data = make_trac_json(stage="Unreviewed", status="new", resolution="duplicate")
        result = check_pr.check_trac_status("36991", data)
        self.assertIsInstance(result, Message)
        self.assertIn("stage='Unreviewed'", result.kwargs["current_state"])
        self.assertIn("resolution='duplicate'", result.kwargs["current_state"])
        self.assertIn("status='new'", result.kwargs["current_state"])

    def test_ticket_not_found_current_state(self):
        result = check_pr.check_trac_status("99999", check_pr.TICKET_NOT_FOUND)
        self.assertIsInstance(result, Message)
        self.assertIn("not found", result.kwargs["current_state"])

    def test_none_data_skips_check(self):
        self.assertIsNone(check_pr.check_trac_status("36991", None))


class TestCheckTracHasPatch(BaseTestCase):
    def test_already_set_passes(self):
        data = make_trac_json(has_patch="1")
        self.assertIsNone(check_pr.check_trac_has_patch("36991", data))

    def test_not_set_times_out_fails(self):
        data = make_trac_json(has_patch="0")
        result = check_pr.check_trac_has_patch(
            "36991", data, poll_timeout=0, poll_interval=0
        )
        self.assertIsNotNone(result)

    def test_failure_message_contains_ticket_id(self):
        data = make_trac_json(ticket_id="36991", has_patch="0")
        result = check_pr.check_trac_has_patch(
            "36991", data, poll_timeout=0, poll_interval=0
        )
        self.assertIsInstance(result, Message)
        self.assertEqual(result.kwargs["ticket_id"], "36991")

    def test_set_on_second_poll_passes(self):
        initial = make_trac_json(has_patch="0")
        second = make_trac_json(has_patch="1")
        with (
            mock.patch.object(check_pr, "fetch_trac_ticket", return_value=second),
            mock.patch("time.sleep"),
        ):
            self.assertIsNone(
                check_pr.check_trac_has_patch(
                    "36991", initial, poll_timeout=60, poll_interval=0
                )
            )

    def test_none_data_skips_check(self):
        self.assertIsNone(check_pr.check_trac_has_patch("36991", None))

    def test_ticket_not_found_skips_check(self):
        # Ticket not found -- already reported by check_trac_status.
        self.assertIsNone(
            check_pr.check_trac_has_patch("36991", check_pr.TICKET_NOT_FOUND)
        )

    def test_fetch_error_during_poll_skips_check(self):
        initial = make_trac_json(has_patch="0")
        with (
            mock.patch.object(check_pr, "fetch_trac_ticket", return_value=None),
            mock.patch("time.sleep"),
        ):
            self.assertIsNone(
                check_pr.check_trac_has_patch(
                    "36991", initial, poll_timeout=60, poll_interval=0
                )
            )


class TestCheckPrTitleHasTicket(BaseTestCase):
    def test_ticket_in_title_passes(self):
        self.assertIsNone(
            check_pr.check_pr_title_has_ticket("Fixed #36991 -- Fix bug.", "36991")
        )

    def test_refs_format_passes(self):
        self.assertIsNone(
            check_pr.check_pr_title_has_ticket("Refs #36991 -- Add tests.", "36991")
        )

    def test_ticket_missing_from_title_fails(self):
        self.assertIsNotNone(
            check_pr.check_pr_title_has_ticket("Fix template rendering bug.", "36991")
        )

    def test_empty_title_fails(self):
        self.assertIsNotNone(check_pr.check_pr_title_has_ticket("", "36991"))

    def test_wrong_ticket_number_fails(self):
        self.assertIsNotNone(
            check_pr.check_pr_title_has_ticket("Fixed #11111 -- Fix bug.", "36991")
        )

    def test_failure_message_contains_ticket_id(self):
        result = check_pr.check_pr_title_has_ticket("Fix something.", "36991")
        self.assertIsInstance(result, Message)
        self.assertEqual(result.kwargs["ticket_id"], "36991")


class TestCheckBranchDescription(BaseTestCase):
    def test_valid_passes(self):
        self.assertIsNone(check_pr.check_branch_description(VALID_PR_BODY))

    def test_placeholder_fails(self):
        body = make_pr_body(
            description=(
                "Provide a concise overview of the issue or rationale behind"
                " the proposed changes."
            )
        )
        self.assertIsNotNone(check_pr.check_branch_description(body))

    def test_placeholder_with_appended_text_fails(self):
        body = make_pr_body(
            description=(
                "Provide a concise overview of the issue or rationale behind"
                " the proposed changes. Yes."
            )
        )
        self.assertIsNotNone(check_pr.check_branch_description(body))

    def test_empty_fails(self):
        body = make_pr_body(description="")
        self.assertIsNotNone(check_pr.check_branch_description(body))

    def test_too_short_fails(self):
        body = make_pr_body(description="Fix bug.")
        self.assertIsNotNone(check_pr.check_branch_description(body))

    def test_exactly_five_words_passes(self):
        body = make_pr_body(description="Fix the template rendering bug.")
        self.assertIsNone(check_pr.check_branch_description(body))

    def test_html_comment_only_fails(self):
        body = make_pr_body(
            description="<!-- Provide a concise overview of the issue -->"
        )
        self.assertIsNotNone(check_pr.check_branch_description(body))

    def test_html_comment_words_not_counted(self):
        body = make_pr_body(description="<!-- this has five words --> fix")
        self.assertIsNotNone(check_pr.check_branch_description(body))

    def test_missing_section_header_fails(self):
        body = VALID_PR_BODY.replace("#### Branch description\n", "")
        self.assertIsNotNone(check_pr.check_branch_description(body))

    def test_multiline_passes(self):
        body = make_pr_body(
            description=(
                "This PR fixes a bug in the ORM.\n"
                "The issue affects queries with multiple joins."
            )
        )
        self.assertIsNone(check_pr.check_branch_description(body))

    def test_crlf_line_endings_pass(self):
        body = make_pr_body().replace("\n", "\r\n")
        self.assertIsNone(check_pr.check_branch_description(body))


class TestCheckAIDisclosure(BaseTestCase):
    def test_no_ai_checked_passes(self):
        self.assertIsNone(check_pr.check_ai_disclosure(VALID_PR_BODY))

    def test_ai_used_with_description_passes(self):
        body = make_pr_body(
            no_ai_checked=False,
            ai_used_checked=True,
            ai_description=(
                "Used GitHub Copilot for autocomplete, all output manually reviewed."
            ),
        )
        self.assertIsNone(check_pr.check_ai_disclosure(body))

    def test_neither_option_checked_fails(self):
        body = make_pr_body(no_ai_checked=False, ai_used_checked=False)
        self.assertIsNotNone(check_pr.check_ai_disclosure(body))

    def test_both_options_checked_fails(self):
        body = make_pr_body(no_ai_checked=True, ai_used_checked=True)
        self.assertIsNotNone(check_pr.check_ai_disclosure(body))

    def test_ai_used_no_description_fails(self):
        body = make_pr_body(
            no_ai_checked=False, ai_used_checked=True, ai_description=""
        )
        self.assertIsNotNone(check_pr.check_ai_disclosure(body))

    def test_ai_used_short_description_fails(self):
        body = make_pr_body(
            no_ai_checked=False, ai_used_checked=True, ai_description="Used Copilot."
        )
        self.assertIsNotNone(check_pr.check_ai_disclosure(body))

    def test_ai_used_exactly_five_word_description_passes(self):
        body = make_pr_body(
            no_ai_checked=False,
            ai_used_checked=True,
            ai_description="Used Claude for code review.",
        )
        self.assertIsNone(check_pr.check_ai_disclosure(body))

    def test_missing_section_fails(self):
        body = VALID_PR_BODY.replace("#### AI Assistance Disclosure (REQUIRED)\n", "")
        self.assertIsNotNone(check_pr.check_ai_disclosure(body))

    def test_uppercase_x_in_checkbox_passes(self):
        body = VALID_PR_BODY.replace(
            "- [x] **No AI tools were used**", "- [X] **No AI tools were used**"
        )
        self.assertIsNone(check_pr.check_ai_disclosure(body))

    def test_commented_out_checkbox_not_counted(self):
        body = make_pr_body(no_ai_checked=False, ai_used_checked=False)
        body = body.replace(
            "- [ ] **No AI tools were used**",
            "<!-- - [x] No AI tools were used -->\n- [ ] **No AI tools were used**",
        )
        self.assertIsNotNone(check_pr.check_ai_disclosure(body))


class TestStripHtmlComments(BaseTestCase):
    def test_removes_single_line_comment(self):
        self.assertEqual(
            check_pr.strip_html_comments("hello <!-- comment --> world"), "hello  world"
        )

    def test_removes_multiline_comment(self):
        self.assertEqual(
            check_pr.strip_html_comments("before\n<!-- line one\nline two\n-->\nafter"),
            "before\n\nafter",
        )

    def test_no_comment_unchanged(self):
        self.assertEqual(
            check_pr.strip_html_comments("no comments here"), "no comments here"
        )

    def test_empty_string(self):
        self.assertEqual(check_pr.strip_html_comments(""), "")

    def test_removes_multiple_comments(self):
        self.assertEqual(
            check_pr.strip_html_comments("a <!-- x --> b <!-- y --> c"),
            "a  b  c",
        )


class TestCheckChecklist(BaseTestCase):
    def test_first_five_checked_passes(self):
        self.assertIsNone(check_pr.check_checklist(VALID_PR_BODY))

    def test_all_nine_checked_passes(self):
        body = make_pr_body(checked_items=9)
        self.assertIsNone(check_pr.check_checklist(body))

    def test_none_checked_fails(self):
        body = make_pr_body(checked_items=0)
        self.assertIsNotNone(check_pr.check_checklist(body))

    def test_four_of_five_checked_fails(self):
        body = make_pr_body(checked_items=4)
        self.assertIsNotNone(check_pr.check_checklist(body))

    def test_three_of_five_checked_fails(self):
        body = make_pr_body(checked_items=3)
        self.assertIsNotNone(check_pr.check_checklist(body))

    def test_missing_section_fails(self):
        body = VALID_PR_BODY.replace("#### Checklist\n", "")
        self.assertIsNotNone(check_pr.check_checklist(body))

    def test_uppercase_x_passes(self):
        body = VALID_PR_BODY.replace("- [x]", "- [X]")
        self.assertIsNone(check_pr.check_checklist(body))

    def test_crlf_line_endings_pass(self):
        body = make_pr_body().replace("\n", "\r\n")
        self.assertIsNone(check_pr.check_checklist(body))


class TestIntegration(BaseTestCase):
    def test_fully_valid_pr_passes_all_checks(self):
        data = make_trac_json(stage="Accepted", has_patch="1")
        for label, body in [
            ("LF line endings", VALID_PR_BODY),
            ("CRLF line endings", VALID_PR_BODY.replace("\n", "\r\n")),
        ]:
            with self.subTest(label=label):
                ticket_id = check_pr.extract_ticket_id(body)
                results = [
                    check_pr.check_trac_ticket(body, check_pr.LARGE_PR_THRESHOLD),
                    check_pr.check_trac_status(ticket_id, data),
                    check_pr.check_trac_has_patch(ticket_id, data),
                    check_pr.check_pr_title_has_ticket(VALID_PR_TITLE, ticket_id),
                    check_pr.check_branch_description(body),
                    check_pr.check_ai_disclosure(body),
                    check_pr.check_checklist(body),
                ]
                failures = [r for r in results if r is not None]
                self.assertEqual(
                    failures,
                    [],
                    f"Expected no failures ({label}), got: {failures!r}",
                )

    def test_blank_body_fails_non_status_checks(self):
        results = [
            check_pr.check_trac_ticket("", check_pr.LARGE_PR_THRESHOLD),
            check_pr.check_branch_description(""),
            check_pr.check_ai_disclosure(""),
            check_pr.check_checklist(""),
        ]
        for i, result in enumerate(results, 1):
            self.assertIsNotNone(result, f"Check {i} should have failed on empty body")

    def test_make_pr_body_matches_template(self):
        template_path = (
            Path(__file__).parents[3] / ".github" / "pull_request_template.md"
        )
        with open(template_path) as f:
            raw_template = f.read()
        blank_body = make_pr_body(
            ticket="ticket-XXXXX",
            description=(
                "Provide a concise overview of the issue or rationale behind"
                " the proposed changes."
            ),
            no_ai_checked=False,
            ai_used_checked=False,
            checked_items=0,
        )
        self.assertEqual(blank_body, raw_template)

    def test_unedited_template_fails_all_checks(self):
        template_path = (
            Path(__file__).parents[3] / ".github" / "pull_request_template.md"
        )
        with open(template_path) as f:
            raw_template = f.read()
        results = [
            check_pr.check_trac_ticket(raw_template, check_pr.LARGE_PR_THRESHOLD),
            check_pr.check_branch_description(raw_template),
            check_pr.check_ai_disclosure(raw_template),
            check_pr.check_checklist(raw_template),
        ]
        for i, result in enumerate(results, 1):
            self.assertIsNotNone(
                result, f"Check {i} should have failed on raw template"
            )

    def test_pr_before_template_date_skips_all_checks(self):
        with self.assertLogs(logger, level="INFO") as logs:
            result, _, mock_gh = self.call_main(
                pr_body=make_pr_body(ticket="", checked_items=0),
                pr_created_at="2024-01-01T00:00:00Z",
            )
        self.assertIsNone(result)
        mock_gh.assert_not_called()
        self.assertIn("older than PR template", "\n".join(logs.output))

    def test_pr_before_ai_disclosure_date_skips_ai_check(self):
        body = make_pr_body(no_ai_checked=False, ai_used_checked=False)
        with self.assertLogs(logger, level="INFO") as logs:
            _, mock_summary, _ = self.call_main(
                pr_body=body,
                pr_title=VALID_PR_TITLE,
                pr_created_at="2025-01-01T00:00:00Z",
            )
        _, results, _ = mock_summary.call_args.args
        result_map = {name: result for name, result, _ in results}
        self.assertIs(result_map["AI disclosure completed"], check_pr.SKIPPED)
        self.assertIn("older than AI Disclosure", "\n".join(logs.output))

    def test_no_ticket_skips_trac_status_and_has_patch(self):
        with self.assertLogs(logger, level="INFO") as logs:
            self.call_main(pr_body="")
        self.assertIn(
            "No Trac ticket -- skipping status and has_patch checks.",
            "\n".join(logs.output),
        )

    def test_no_ticket_results_include_skipped_sentinels(self):
        body = make_pr_body(ticket="")
        _, mock_summary, _ = self.call_main(pr_body=body)
        _, results, _ = mock_summary.call_args.args
        result_map = {name: result for name, result, _ in results}
        self.assertIs(result_map["Trac ticket status is Accepted"], check_pr.SKIPPED)
        self.assertIs(result_map["Trac ticket has_patch flag set"], check_pr.SKIPPED)
        self.assertIs(result_map["PR title includes ticket number"], check_pr.SKIPPED)

    def test_non_accepted_ticket_skips_has_patch(self):
        data = make_trac_json(stage="Unreviewed")
        _, mock_summary, _ = self.call_main(
            pr_body=VALID_PR_BODY, pr_title=VALID_PR_TITLE, trac_data=data
        )
        _, results, _ = mock_summary.call_args.args
        result_map = {name: result for name, result, _ in results}
        self.assertIsNotNone(result_map["Trac ticket status is Accepted"])
        self.assertIs(result_map["Trac ticket has_patch flag set"], check_pr.SKIPPED)

    def test_established_author_skips_all_checks(self):
        body = make_pr_body(ticket="", checked_items=0)
        result, _, mock_gh = self.call_main(pr_body=body, commit_count=5)
        self.assertIsNone(result)
        mock_gh.assert_not_called()

    def test_fully_valid_pr_no_comment_posted(self):
        result, _, mock_gh = self.call_main(
            pr_body=VALID_PR_BODY, pr_title=VALID_PR_TITLE
        )
        self.assertIsNone(result)
        mock_gh.assert_not_called()

    def test_trusted_author_failures_no_close(self):
        body = make_pr_body(ticket="", checked_items=0)
        result, _, mock_gh = self.call_main(pr_body=body, commit_count=1)
        self.assertEqual(result, 1)
        mock_gh.assert_called_once_with(
            "POST", "/issues/10/comments", "test-token", "test/repo", mock.ANY
        )

    def test_untrusted_author_failures_posts_comment_and_closes(self):
        body = make_pr_body(ticket="", checked_items=0)
        result, _, mock_gh = self.call_main(pr_body=body)
        self.assertEqual(result, 1)
        self.assertEqual(
            mock_gh.mock_calls,
            [
                mock.call(
                    "POST", "/issues/10/comments", "test-token", "test/repo", mock.ANY
                ),
                mock.call(
                    "PATCH", "/pulls/10", "test-token", "test/repo", {"state": "closed"}
                ),
            ],
        )

    def test_missing_pr_author_treated_as_untrusted(self):
        body = make_pr_body(ticket="", checked_items=0)
        result, _, mock_gh = self.call_main(pr_body=body, pr_author="")
        self.assertEqual(result, 1)
        self.assertEqual(
            mock_gh.mock_calls,
            [
                mock.call(
                    "POST", "/issues/10/comments", "test-token", "test/repo", mock.ANY
                ),
                mock.call(
                    "PATCH", "/pulls/10", "test-token", "test/repo", {"state": "closed"}
                ),
            ],
        )

    def test_autoclose_false_posts_comment_does_not_close(self):
        body = make_pr_body(ticket="", checked_items=0)
        result, _, mock_gh = self.call_main(pr_body=body, autoclose=False)
        self.assertEqual(result, 1)
        mock_gh.assert_called_once_with(
            "POST", "/issues/10/comments", "test-token", "test/repo", mock.ANY
        )

    def test_warnings_only_posts_comment_does_not_close(self):
        trac_data = make_trac_json(stage="Accepted", has_patch="0")
        # pr_title="" triggers title warning.
        # has_patch="0" triggers has_patch warning.
        result, _, mock_gh = self.call_main(
            pr_body=VALID_PR_BODY, pr_title="", trac_data=trac_data
        )
        self.assertIsNone(result)
        mock_gh.assert_called_once_with(
            "POST", "/issues/10/comments", "test-token", "test/repo", mock.ANY
        )

    def test_warnings_alongside_failures_still_closes(self):
        trac_data = make_trac_json(stage="Accepted", has_patch="0")
        # Empty body: fatal ticket failure + incorrect title warning.
        body = make_pr_body(ticket="", checked_items=0)
        result, _, mock_gh = self.call_main(pr_body=body, trac_data=trac_data)
        self.assertEqual(result, 1)
        self.assertEqual(
            mock_gh.mock_calls,
            [
                mock.call(
                    "POST", "/issues/10/comments", "test-token", "test/repo", mock.ANY
                ),
                mock.call(
                    "PATCH", "/pulls/10", "test-token", "test/repo", {"state": "closed"}
                ),
            ],
        )


class TestWriteJobSummary(BaseTestCase):
    def test_no_summary_file_does_nothing(self):
        check_pr.write_job_summary(
            "99",
            [
                ("Some check", None, LEVEL_ERROR),
                ("Other check", "failure", LEVEL_ERROR),
            ],
        )

    def test_all_passed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            summary = Path(tmpdir) / "summary.md"
            results = [
                ("Trac ticket referenced", None, LEVEL_ERROR),
                ("Branch description provided", None, LEVEL_ERROR),
            ]
            check_pr.write_job_summary("7", results, str(summary))
            content = summary.read_text()
        self.assertIn("## PR #7 Quality Check Results", content)
        self.assertIn("✅", content)
        self.assertNotIn(ERROR_ICON, content)
        self.assertIn("Trac ticket referenced", content)
        self.assertIn("Branch description provided", content)

    def test_with_failures(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            summary = Path(tmpdir) / "summary.md"
            results = [
                ("Trac ticket referenced", None, LEVEL_ERROR),
                ("Branch description provided", "Missing description", LEVEL_ERROR),
                ("Checklist completed", "Incomplete checklist", LEVEL_ERROR),
            ]
            check_pr.write_job_summary("12", results, str(summary))
            content = summary.read_text()
        self.assertIn("## PR #12 Quality Check Results", content)
        self.assertEqual(content.count("✅"), 1)
        self.assertEqual(content.count(ERROR_ICON), 2)
        self.assertIn("Passed", content)
        self.assertIn(ERROR_LABEL, content)

    def test_with_warning(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            summary = Path(tmpdir) / "summary.md"
            results = [
                ("Trac ticket referenced", None, LEVEL_ERROR),
                ("Trac ticket has_patch flag set", "No patch", LEVEL_WARNING),
            ]
            check_pr.write_job_summary("8", results, str(summary))
            content = summary.read_text()
        self.assertIn("✅", content)
        self.assertIn(WARNING_ICON, content)
        self.assertIn(WARNING_LABEL, content)
        self.assertNotIn(ERROR_ICON, content)

    def test_appends_to_existing_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            summary = Path(tmpdir) / "summary.md"
            summary.write_text("## Previous step\n\nSome content.\n")
            check_pr.write_job_summary(
                "5", [("Checklist completed", None, LEVEL_ERROR)], str(summary)
            )
            content = summary.read_text()
        self.assertIn("## Previous step", content)
        self.assertIn("## PR #5 Quality Check Results", content)

    def test_skipped_checks(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            summary = Path(tmpdir) / "summary.md"
            results = [
                (
                    "Trac ticket referenced",
                    Message(*MISSING_TRAC_TICKET, threshold=80),
                    LEVEL_ERROR,
                ),
                ("Trac ticket status is Accepted", check_pr.SKIPPED, LEVEL_ERROR),
                ("Trac ticket has_patch flag set", check_pr.SKIPPED, LEVEL_WARNING),
            ]
            check_pr.write_job_summary("3", results, str(summary))
            content = summary.read_text()
        self.assertEqual(content.count("⏭️"), 2)
        self.assertEqual(content.count("Skipped"), 2)
        self.assertIn(ERROR_ICON, content)


class TestGetRecentCommitCount(BaseTestCase):
    def _make_github_request_mock(self, commits):
        return mock.patch.object(check_pr, "github_request", return_value=commits)

    def test_returns_number_of_commits(self):
        commits = [{"sha": "abc"}, {"sha": "def"}, {"sha": "ghi"}]
        with self._make_github_request_mock(commits):
            self.assertEqual(
                check_pr.get_recent_commit_count(
                    "someuser", "django/django", "token", since_days=365, max_count=5
                ),
                3,
            )

    def test_no_commits_returns_zero(self):
        with self._make_github_request_mock([]):
            self.assertEqual(
                check_pr.get_recent_commit_count(
                    "newuser", "django/django", "token", since_days=365, max_count=5
                ),
                0,
            )

    def test_api_path_includes_author_since_and_max_count(self):
        with mock.patch.object(check_pr, "github_request", return_value=[]) as mock_gh:
            check_pr.get_recent_commit_count(
                "someuser", "django/django", "token", since_days=365, max_count=5
            )
        params = mock_gh.call_args.kwargs["params"]
        self.assertEqual(params["author"], "someuser")
        self.assertIn("since", params)
        self.assertEqual(params["per_page"], 5)
