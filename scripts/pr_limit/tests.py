"""Tests for the PR limit's exit paths and closure behaviour."""

import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import ANY, call, patch

from pr_limit import check_pr

REPO = "django/django"
TOKEN = "test-token"
PR_NUMBER = 20
NOW = datetime(2026, 10, 19, 12, tzinfo=timezone.utc)


def make_pr(number=PR_NUMBER, created_at=NOW, state="open"):
    return {
        "number": number,
        "state": state,
        "created_at": created_at.isoformat(),
        "user": {"login": "contributor"},
    }


class PRLimitTests(unittest.TestCase):
    def setUp(self):
        self.request = self.enterContext(
            patch.object(check_pr, "github_request", return_value=make_pr())
        )
        self.permissions = self.enterContext(
            patch.object(check_pr, "has_exempt_permissions", return_value=False)
        )
        self.commits = self.enterContext(
            patch.object(check_pr, "get_recent_commit_count", return_value=0)
        )
        self.prs = self.enterContext(
            patch.object(check_pr, "github_results", return_value=[make_pr(19)])
        )
        self.comment_exists = self.enterContext(
            patch.object(check_pr, "comment_exists", return_value=False)
        )

    def run_check(self, **kwargs):
        with self.assertLogs(check_pr.logger, level="INFO") as logs:
            result = check_pr.main(REPO, TOKEN, PR_NUMBER, now=NOW, **kwargs)
        self.assertEqual(result, 0)
        return [record.getMessage() for record in logs.records]

    def assert_no_changes(self):
        self.assertTrue(
            all(c.args[0] == "GET" for c in self.request.call_args_list),
            self.request.call_args_list,
        )

    def test_already_closed(self):
        self.request.return_value = make_pr(state="closed")
        self.assertEqual(
            self.run_check(autoclose=True),
            ["PR #20 is already closed -- skipping."],
        )
        self.assert_no_changes()

    def test_exempt_author(self):
        self.permissions.return_value = True
        self.assertEqual(
            self.run_check(autoclose=True),
            ["PR #20 author has exempt repository permissions."],
        )
        self.assert_no_changes()

    def test_commit_threshold(self):
        for count in (check_pr.MIN_COMMITS - 1, check_pr.MIN_COMMITS):
            with self.subTest(count=count):
                self.commits.return_value = count
                if count < check_pr.MIN_COMMITS:
                    expected = [
                        "PR #20 exceeds the limit; other recent open PRs: #19.",
                        "AUTOCLOSE is disabled -- would comment and close PR #20.",
                    ]
                else:
                    expected = ["PR #20 author meets the commit threshold."]
                self.assertEqual(self.run_check(), expected)
                self.assert_no_changes()

    def test_no_other_prs(self):
        for prs in ([], [make_pr()]):
            with self.subTest(prs=prs):
                self.prs.return_value = prs
                self.assertEqual(
                    self.run_check(autoclose=True),
                    ["PR #20 author has no other recent open PRs."],
                )
                self.assert_no_changes()

    def test_pr_age_boundary(self):
        cutoff = NOW - timedelta(days=check_pr.LOOKBACK_DAYS)
        for seconds in (-1, 0, 1):
            with self.subTest(seconds_from_cutoff=seconds):
                self.prs.return_value = [
                    make_pr(19, cutoff + timedelta(seconds=seconds))
                ]
                if seconds < 0:
                    expected = ["PR #20 author has no other recent open PRs."]
                else:
                    expected = [
                        "PR #20 exceeds the limit; other recent open PRs: #19.",
                        "AUTOCLOSE is disabled -- would comment and close PR #20.",
                    ]
                self.assertEqual(self.run_check(), expected)
                self.assert_no_changes()

    def test_autoclose_disabled_by_default(self):
        self.assertEqual(
            self.run_check(),
            [
                "PR #20 exceeds the limit; other recent open PRs: #19.",
                "AUTOCLOSE is disabled -- would comment and close PR #20.",
            ],
        )
        self.comment_exists.assert_not_called()
        self.assert_no_changes()

    def test_target_closed_during_checks(self):
        self.request.side_effect = [make_pr(), make_pr(state="closed")]
        self.assertEqual(
            self.run_check(autoclose=True),
            ["PR #20 exceeds the limit; other recent open PRs: #19."],
        )
        self.assert_no_changes()
        self.comment_exists.assert_not_called()

    def test_closes_pr(self):
        for existing_comment in (False, True):
            with self.subTest(existing_comment=existing_comment):
                self.request.reset_mock()
                self.comment_exists.return_value = existing_comment
                self.assertEqual(
                    self.run_check(autoclose=True),
                    [
                        "PR #20 exceeds the limit; other recent open PRs: #19.",
                        "Closed PR #20 because its author has reached the limit.",
                    ],
                )
                expected = [
                    call("GET", "/pulls/20", TOKEN, REPO),
                    call("GET", "/pulls/20", TOKEN, REPO),
                ]
                if not existing_comment:
                    expected.append(
                        call("POST", "/issues/20/comments", TOKEN, REPO, ANY)
                    )
                expected.append(
                    call("PATCH", "/pulls/20", TOKEN, REPO, {"state": "closed"})
                )
                self.assertEqual(self.request.call_args_list, expected)
                if not existing_comment:
                    body = self.request.call_args_list[2].args[4]["body"]
                    self.assertIn(check_pr.COMMENT_MARKER, body)
                    self.assertIn("#19", body)
