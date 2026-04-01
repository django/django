#! /usr/bin/env python

"""
Tests for scripts utilities.

Run from within the scripts/ folder with:

$ python -m unittest tests.py

Or from the repo root with:

$ PYTHONPATH=scripts/ python -m unittest scripts/tests.py
"""

import unittest

from prepare_commit_msg import process_commit_message


class ProcessCommitMessageTests(unittest.TestCase):
    def test_non_stable_branch_no_prefix_added(self):
        lines = ["Fixed #123 -- Added a feature.\n"]
        result = process_commit_message(lines, "main")
        self.assertNotIn("[", result[0].split("--")[0])

    def test_non_stable_branch_period_added(self):
        lines = ["Fixed #123 -- Added a feature\n"]
        result = process_commit_message(lines, "main")
        self.assertIs(result[0].rstrip("\n").endswith("."), True)

    def test_non_stable_branch_with_period_unchanged(self):
        lines = ["Fixed #123 -- Added a feature.\n"]
        result = process_commit_message(lines, "main")
        self.assertEqual(result, lines)

    def test_empty_body_unchanged(self):
        lines = ["# This is a comment.\n"]
        result = process_commit_message(lines, "stable/5.2.x")
        self.assertEqual(result, lines)

    def test_only_blank_lines_unchanged(self):
        lines = ["\n", "\n"]
        result = process_commit_message(lines, "stable/5.2.x")
        self.assertEqual(result, lines)

    def test_adds_stable_prefix(self):
        lines = ["Fixed #123 -- Added a feature.\n"]
        result = process_commit_message(lines, "stable/5.2.x")
        self.assertEqual(result[0], "[5.2.x] Fixed #123 -- Added a feature.\n")

    def test_does_not_double_add_prefix(self):
        lines = ["[5.2.x] Fixed #123 -- Added a feature.\n"]
        result = process_commit_message(lines, "stable/5.2.x")
        self.assertEqual(result[0], "[5.2.x] Fixed #123 -- Added a feature.\n")

    def test_summary_leading_whitespace_no_double_space_before_prefix(self):
        lines = ["  fixed #123 -- Added a feature.\n"]
        result = process_commit_message(lines, "stable/5.2.x")
        self.assertEqual(result[0], "[5.2.x] Fixed #123 -- Added a feature.\n")

    def test_capitalizes_first_letter(self):
        lines = ["fixed #123 -- Added a feature.\n"]
        result = process_commit_message(lines, "main")
        self.assertEqual(result[0], "Fixed #123 -- Added a feature.\n")

    def test_capitalizes_first_letter_after_existing_prefix(self):
        lines = ["[5.2.x] fixed #123 -- Added a feature.\n"]
        result = process_commit_message(lines, "stable/5.2.x")
        self.assertTrue(result[0].startswith("[5.2.x] Fixed"))

    def test_adds_trailing_period(self):
        lines = ["Fixed #123 -- Added a feature\n"]
        result = process_commit_message(lines, "stable/5.2.x")
        self.assertIs(result[0].rstrip("\n").endswith("."), True)

    def test_does_not_double_add_trailing_period(self):
        lines = ["Fixed #123 -- Added a feature.\n"]
        result = process_commit_message(lines, "stable/5.2.x")
        self.assertIs(result[0].rstrip("\n").endswith(".."), False)

    def test_adds_backport_note(self):
        sha = "abc123def456"
        lines = ["Fixed #123 -- Added a feature.\n"]
        result = process_commit_message(lines, "stable/5.2.x", cherry_sha=sha)
        self.assertIn(f"Backport of {sha} from main.\n", result)

    def test_does_not_double_add_backport_note(self):
        sha = "abc123def456"
        lines = [
            "Fixed #123 -- Added a feature.\n",
            "\n",
            f"Backport of {sha} from main.\n",
        ]
        result = process_commit_message(lines, "stable/5.2.x", cherry_sha=sha)
        self.assertEqual(len([line for line in result if "Backport" in line]), 1)

    def test_backport_note_separated_by_blank_line(self):
        sha = "abc123def456"
        lines = ["Fixed #123 -- Added a feature.\n"]
        result = process_commit_message(lines, "stable/5.2.x", cherry_sha=sha)
        note_idx = next(i for i, l in enumerate(result) if f"Backport of {sha}" in l)
        self.assertEqual(result[note_idx - 1], "\n")

    def test_git_comments_preserved_at_end(self):
        sha = "abc123def456"
        lines = [
            "Fixed #123 -- Added a feature.\n",
            "# Please enter the commit message.\n",
            "# Changes to be committed:\n",
        ]
        result = process_commit_message(lines, "stable/5.2.x", cherry_sha=sha)
        self.assertEqual(result[-2], "# Please enter the commit message.\n")
        self.assertEqual(result[-1], "# Changes to be committed:\n")

    def test_prefix_and_period_and_backport_combined(self):
        sha = "abc123def456"
        lines = ["Fixed #123 -- Added a feature\n"]
        result = process_commit_message(lines, "stable/5.2.x", cherry_sha=sha)
        self.assertEqual(result[0], "[5.2.x] Fixed #123 -- Added a feature.\n")
        self.assertIn(f"Backport of {sha} from main.\n", result)

    def test_no_cherry_sha_no_backport_note(self):
        lines = ["Fixed #123 -- Added a feature.\n"]
        result = process_commit_message(lines, "stable/5.2.x", cherry_sha=None)
        self.assertNotIn("Backport of", "".join(result))

    def test_leading_blank_lines_stripped(self):
        lines = ["\n", "Fixed #123 -- Added a feature.\n"]
        result = process_commit_message(lines, "stable/5.2.x")
        self.assertEqual(result[0], "[5.2.x] Fixed #123 -- Added a feature.\n")
