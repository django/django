import unittest

from pattern_analyzer import (
    PatternAnalyzer,
    PatternMatch,
    Location,
    Confidence,
)


class TestPatternAnalyzer(unittest.TestCase):
    """Test the PatternAnalyzer class"""

    def test_analyze_pr_no_patterns(self):
        matches = PatternAnalyzer.analyze_pr("Fixed bug #12345", "This is a real fix")
        self.assertEqual(len(matches), 0)

    def test_analyze_pr_tutorial_in_title(self):
        matches = PatternAnalyzer.analyze_pr("My learning experience", "")
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].pattern, "learning")
        self.assertEqual(matches[0].location, Location.TITLE)
        self.assertEqual(matches[0].confidence, Confidence.LOW)
        self.assertEqual(matches[0].matched_text, "learning")

    def test_analyze_pr_high_confidence_in_body(self):
        matches = PatternAnalyzer.analyze_pr("Fix bug", "This is a toast example")
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].pattern, "toast")
        self.assertEqual(matches[0].location, Location.BODY)
        self.assertEqual(matches[0].confidence, Confidence.HIGH)

    def test_analyze_pr_low_confidence_not_in_body(self):
        # Low confidence patterns should only be checked in title, not body
        matches = PatternAnalyzer.analyze_pr(
            "Add test", "This is a comprehensive test suite"
        )
        self.assertEqual(len(matches), 1)  # Only title match
        self.assertEqual(matches[0].location, Location.TITLE)
        self.assertEqual(matches[0].pattern, r"\btest\b")
        self.assertEqual(matches[0].confidence, Confidence.LOW)

    def test_analyze_pr_multiple_patterns_in_title(self):
        matches = PatternAnalyzer.analyze_pr(
            "My tutorial about learning Django test", ""
        )
        self.assertEqual(len(matches), 3)

        patterns_found = [match.pattern for match in matches]
        self.assertIn("tutorial", patterns_found)
        self.assertIn("learning", patterns_found)
        self.assertIn(r"\btest\b", patterns_found)

        # Check that all matches are in title
        for match in matches:
            self.assertEqual(match.location, Location.TITLE)

    def test_analyze_pr_99999_pattern_high_confidence(self):
        matches = PatternAnalyzer.analyze_pr("Test PR #99999", "This includes 99999")
        self.assertEqual(len(matches), 3)  # "test" in title, "99999" in title and body

        patterns_found = [match.pattern for match in matches]
        self.assertIn("99999", patterns_found)
        self.assertIn(r"\btest\b", patterns_found)

        # Check that 99999 appears in both title and body
        title_99999 = [
            m for m in matches if m.pattern == "99999" and m.location == Location.TITLE
        ]
        body_99999 = [
            m for m in matches if m.pattern == "99999" and m.location == Location.BODY
        ]
        self.assertEqual(len(title_99999), 1)
        self.assertEqual(len(body_99999), 1)

    def test_analyze_pr_getting_started_pattern(self):
        matches = PatternAnalyzer.analyze_pr("Getting started with Django", "")
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].pattern, "getting started")
        self.assertEqual(matches[0].location, Location.TITLE)
        self.assertEqual(matches[0].confidence, Confidence.LOW)

    def test_case_insensitive_matching(self):
        matches = PatternAnalyzer.analyze_pr("My LEARNING experience", "")
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].matched_text, "LEARNING")
        self.assertEqual(matches[0].pattern, "learning")

    def test_pattern_context_extraction(self):
        matches = PatternAnalyzer.analyze_pr("", "This is a toast notification example")
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].pattern, "toast")
        self.assertIn("toast", matches[0].context)
        # Context should include surrounding text
        self.assertTrue(len(matches[0].context) > len("toast"))

    def test_should_auto_close_multiple_matches(self):
        matches = [
            PatternMatch(
                "tutorial", "tutorial", Location.TITLE, "tutorial", Confidence.LOW
            ),
            PatternMatch(
                "learning", "learning", Location.TITLE, "learning", Confidence.LOW
            ),
        ]
        self.assertTrue(PatternAnalyzer.should_auto_close(matches))

    def test_should_auto_close_high_confidence_single(self):
        matches = [
            PatternMatch("99999", "99999", Location.TITLE, "99999", Confidence.HIGH)
        ]
        self.assertTrue(PatternAnalyzer.should_auto_close(matches))

        matches = [
            PatternMatch("toast", "toast", Location.BODY, "toast", Confidence.HIGH)
        ]
        self.assertTrue(PatternAnalyzer.should_auto_close(matches))

    def test_should_not_auto_close_low_confidence_single(self):
        matches = [
            PatternMatch(r"\btest\b", "test", Location.TITLE, "test", Confidence.LOW)
        ]
        self.assertFalse(PatternAnalyzer.should_auto_close(matches))

    def test_should_not_auto_close_no_matches(self):
        self.assertFalse(PatternAnalyzer.should_auto_close([]))

    def test_get_context_function(self):
        # Test the context extraction
        text = "This is a test string for context extraction"
        context = PatternAnalyzer._get_context(text, 10, 14, 5)
        self.assertEqual(context, "is a test stri")

    def test_get_context_at_start(self):
        text = "test string"
        context = PatternAnalyzer._get_context(text, 0, 4, 5)
        self.assertEqual(context, "test stri")

    def test_get_context_at_end(self):
        text = "string test"
        context = PatternAnalyzer._get_context(text, 7, 11, 5)
        self.assertEqual(context, "ring test")

    def test_get_context_short_text(self):
        text = "test"
        context = PatternAnalyzer._get_context(text, 0, 4, 10)
        self.assertEqual(context, "test")


class TestPatternAnalyzerEdgeCases(unittest.TestCase):
    """Test edge cases and error conditions"""

    def test_empty_title_and_body(self):
        matches = PatternAnalyzer.analyze_pr("", "")
        self.assertEqual(len(matches), 0)

    def test_none_body(self):
        # Should handle None body gracefully
        matches = PatternAnalyzer.analyze_pr("learning", None)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].pattern, "learning")

    def test_special_characters_in_text(self):
        # Test with special regex characters
        matches = PatternAnalyzer.analyze_pr("My learning + tutorial & test", "")
        self.assertEqual(len(matches), 3)

    def test_overlapping_patterns(self):
        # Test when patterns might overlap
        matches = PatternAnalyzer.analyze_pr("learning tutorial", "")
        self.assertEqual(len(matches), 2)
        patterns = [m.pattern for m in matches]
        self.assertIn("learning", patterns)
        self.assertIn("tutorial", patterns)

    def test_pattern_at_word_boundaries(self):
        # Test word boundary pattern (\btest\b)
        matches = PatternAnalyzer.analyze_pr("testing contest", "")
        # Should not match "test" in "testing" or "contest"
        test_matches = [m for m in matches if m.pattern == r"\btest\b"]
        self.assertEqual(len(test_matches), 0)

        matches = PatternAnalyzer.analyze_pr("test case", "")
        # Should match "test" as a separate word
        test_matches = [m for m in matches if m.pattern == r"\btest\b"]
        self.assertEqual(len(test_matches), 1)


class TestPatternAnalyzerCLI(unittest.TestCase):
    """Test the command line interface of PatternAnalyzer"""

    def test_cli_analyze_with_matches(self):
        """Test the analyze command with matches that should auto-close"""
        matches = PatternAnalyzer.analyze_pr("Learning Django tutorial", "")

        result = {
            "has_matches": bool(matches),
            "should_auto_close": PatternAnalyzer.should_auto_close(matches),
            "matches": [
                {
                    "pattern": m.pattern,
                    "matched_text": m.matched_text,
                    "location": m.location.value,
                    "confidence": m.confidence.value,
                }
                for m in matches
            ],
        }

        self.assertTrue(result["has_matches"])
        self.assertTrue(result["should_auto_close"])
        self.assertEqual(len(result["matches"]), 2)

    def test_cli_analyze_with_matches_no_autoclose(self):
        """Test the analyze command with single low-confidence match"""
        # Single low confidence should label but not auto-close
        matches = PatternAnalyzer.analyze_pr("Learning Django", "This is a tutorial")

        result = {
            "has_matches": bool(matches),
            "should_auto_close": PatternAnalyzer.should_auto_close(matches),
            "matches": [
                {
                    "pattern": m.pattern,
                    "matched_text": m.matched_text,
                    "location": m.location.value,
                    "confidence": m.confidence.value,
                }
                for m in matches
            ],
        }

        self.assertTrue(result["has_matches"])
        self.assertFalse(result["should_auto_close"])
        self.assertEqual(len(result["matches"]), 1)

    def test_cli_analyze_high_confidence_autoclose(self):
        """Test the analyze command with high-confidence pattern"""
        matches = PatternAnalyzer.analyze_pr("Fix #99999", "")

        result = {
            "has_matches": bool(matches),
            "should_auto_close": PatternAnalyzer.should_auto_close(matches),
            "matches": [
                {
                    "pattern": m.pattern,
                    "matched_text": m.matched_text,
                    "location": m.location.value,
                    "confidence": m.confidence.value,
                }
                for m in matches
            ],
        }

        self.assertTrue(result["has_matches"])
        self.assertTrue(result["should_auto_close"])
        self.assertEqual(len(result["matches"]), 1)

    def test_cli_analyze_no_matches(self):
        """Test the analyze command with no matches"""
        matches = PatternAnalyzer.analyze_pr("Fixed bug #12345", "Real fix")

        result = {
            "has_matches": bool(matches),
            "should_auto_close": PatternAnalyzer.should_auto_close(matches),
            "matches": [
                {
                    "pattern": m.pattern,
                    "matched_text": m.matched_text,
                    "location": m.location.value,
                    "confidence": m.confidence.value,
                }
                for m in matches
            ],
        }

        self.assertFalse(result["has_matches"])
        self.assertFalse(result["should_auto_close"])
        self.assertEqual(len(result["matches"]), 0)


class TestPatternAnalyzerIntegration(unittest.TestCase):
    """Integration tests simulating real GitHub Actions usage"""

    def test_tutorial_pr_detection(self):
        """Test detection of typical tutorial PRs"""
        test_cases = [
            # High confidence cases that should auto-close
            ("Fixed #99999 -- Added toast functionality", "", True, True),
            ("My first contribution #99999", "I'm following the tutorial", True, True),
            ("Learning Django tutorial test", "", True, True),
            # Low confidence cases that should label but not auto-close
            ("My learning experience", "", True, False),
            ("Django tutorial walkthrough", "", True, False),
            ("Getting started with Django", "", True, False),
            # Low confidence cases that should label but not auto-close
            ("Add test for models", "", True, False),
            # Valid PRs that should not be labeled
            (
                "Fixed #12345 - Add pagination to admin",
                "Real implementation",
                False,
                False,
            ),
            (
                "Refactor authentication module",
                "Performance improvements",
                False,
                False,
            ),
        ]

        for title, body, should_label, should_auto_close in test_cases:
            with self.subTest(title=title):
                matches = PatternAnalyzer.analyze_pr(title, body)
                actual_should_label = bool(matches)
                actual_should_auto_close = PatternAnalyzer.should_auto_close(matches)

                self.assertEqual(
                    actual_should_label, should_label, f"Labeling mismatch for: {title}"
                )
                self.assertEqual(
                    actual_should_auto_close,
                    should_auto_close,
                    f"Auto-close mismatch for: {title}",
                )

    def test_confidence_levels(self):
        """Test that confidence levels work as expected"""
        # High confidence patterns
        high_matches = PatternAnalyzer.analyze_pr("Test #99999", "This is a toast")
        high_confidence_matches = [
            m for m in high_matches if m.confidence == Confidence.HIGH
        ]
        self.assertGreater(len(high_confidence_matches), 0)

        # Low confidence patterns
        low_matches = PatternAnalyzer.analyze_pr("Add test file", "")
        low_confidence_matches = [
            m for m in low_matches if m.confidence == Confidence.LOW
        ]
        self.assertGreater(len(low_confidence_matches), 0)

    def test_body_filtering_by_confidence(self):
        """Test that only high-confidence patterns are checked in body"""
        # High confidence pattern should be found in body
        matches = PatternAnalyzer.analyze_pr("Fix bug", "This includes toast and 99999")
        body_matches = [m for m in matches if m.location == Location.BODY]
        self.assertEqual(len(body_matches), 2)  # toast and 99999

        # Low confidence pattern should NOT be found in body
        matches = PatternAnalyzer.analyze_pr(
            "Fix bug", "This includes comprehensive test coverage"
        )
        body_matches = [m for m in matches if m.location == Location.BODY]
        self.assertEqual(len(body_matches), 0)  # test is low confidence


if __name__ == "__main__":
    unittest.main(verbosity=2)
