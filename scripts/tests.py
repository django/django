#! /usr/bin/env python

"""
Tests for scripts utilities.

Run from within the scripts/ folder with:

$ python -m unittest tests.py

Or from the repo root with:

$ PYTHONPATH=scripts/ python -m unittest scripts/tests.py
"""

import hashlib
import os
import tempfile
import unittest

from do_django_release import (
    create_checksum_file,
    find_release_artifacts,
    parse_major_version,
)
from prepare_commit_msg import process_commit_message


class ParseMajorVersionTests(unittest.TestCase):
    def test_final_patch_release(self):
        self.assertEqual(parse_major_version("5.2.4"), "5.2")

    def test_final_dot_zero_release(self):
        self.assertEqual(parse_major_version("6.0"), "6.0")

    def test_alpha(self):
        self.assertEqual(parse_major_version("6.0a1"), "6.0")

    def test_beta(self):
        self.assertEqual(parse_major_version("6.0b1"), "6.0")

    def test_release_candidate(self):
        self.assertEqual(parse_major_version("6.0rc1"), "6.0")

    def test_two_digit_minor(self):
        self.assertEqual(parse_major_version("5.10a1"), "5.10")


class CreateChecksumFileTests(unittest.TestCase):
    WHEEL_CONTENT = b"fake wheel content"
    TARBALL_CONTENT = b"fake tarball content"

    def generate_checksum_file(self, **overrides):
        with tempfile.TemporaryDirectory() as tmp:
            dist_path = os.path.join(tmp, "dist")
            os.mkdir(dist_path)
            with open(
                os.path.join(dist_path, "Django-5.2.4-py3-none-any.whl"), "wb"
            ) as f:
                f.write(self.WHEEL_CONTENT)
            with open(os.path.join(dist_path, "django-5.2.4.tar.gz"), "wb") as f:
                f.write(self.TARBALL_CONTENT)
            artifacts_path = os.path.join(tmp, "artifacts")
            os.mkdir(artifacts_path)
            checksum_file_path = os.path.join(
                artifacts_path, "Django-5.2.4.checksum.txt"
            )
            kwargs = dict(
                django_version="5.2.4",
                release_date="May 7, 2025",
                checksum_file_path=checksum_file_path,
                wheel_name="Django-5.2.4-py3-none-any.whl",
                tarball_name="django-5.2.4.tar.gz",
                commit_hash="abc123def456abc123def456abc123def456abc1",
                dist_path=dist_path,
                pgp_key_id="ABCD1234ABCD1234",
                pgp_key_url="https://github.com/releaser.gpg",
            )
            kwargs.update(overrides)
            create_checksum_file(**kwargs)
            with open(checksum_file_path) as f:
                return f.read()

    def test_release_metadata(self):
        result = self.generate_checksum_file()
        self.assertIn("Django 5.2.4", result)
        self.assertIn("May 7, 2025", result)
        self.assertIn("ABCD1234ABCD1234", result)
        self.assertIn("https://github.com/releaser.gpg", result)
        self.assertIn("Django-5.2.4.checksum.txt", result)
        self.assertIn(
            "The 5.2.4 tag points to commit "
            "abc123def456abc123def456abc123def456abc1.",
            result,
        )

    def test_artifact_checksums(self):
        result = self.generate_checksum_file()
        for algo in (hashlib.md5, hashlib.sha1, hashlib.sha256):
            expected_tarball = algo(self.TARBALL_CONTENT).hexdigest()
            expected_wheel = algo(self.WHEEL_CONTENT).hexdigest()
            self.assertIn(f"{expected_tarball}  django-5.2.4.tar.gz", result)
            self.assertIn(f"{expected_wheel}  Django-5.2.4-py3-none-any.whl", result)


class FindReleaseArtifactsTests(unittest.TestCase):
    def test_finds_wheel_and_tarball(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "Django-5.2.4-py3-none-any.whl"), "w"):
                pass
            with open(os.path.join(d, "django-5.2.4.tar.gz"), "w"):
                pass
            wheel, tarball = find_release_artifacts(d)
        self.assertEqual(wheel, "Django-5.2.4-py3-none-any.whl")
        self.assertEqual(tarball, "django-5.2.4.tar.gz")

    def test_empty_directory_returns_none(self):
        with tempfile.TemporaryDirectory() as d:
            wheel, tarball = find_release_artifacts(d)
        self.assertIsNone(wheel)
        self.assertIsNone(tarball)


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
