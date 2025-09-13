import re
from enum import Enum
from dataclasses import dataclass
from typing import List


class Confidence(Enum):
    LOW = "low"
    HIGH = "high"


class Location(Enum):
    TITLE = "title"
    BODY = "body"


@dataclass
class PatternMatch:
    """Stores information about a matched pattern"""

    pattern: str
    matched_text: str
    location: Location
    context: str
    confidence: Confidence


class PatternAnalyzer:
    """Analyzes PR titles and bodies for tutorial patterns"""

    # Tutorial patterns with confidence levels
    TUTORIAL_PATTERNS = {
        r"99999": Confidence.HIGH,
        r"toast": Confidence.HIGH,
        r"learning": Confidence.LOW,
        r"tutorial": Confidence.LOW,
        r"getting started": Confidence.LOW,
        r"\btest\b": Confidence.LOW,
    }

    @classmethod
    def analyze_pr(cls, title: str, body: str = "") -> List[PatternMatch]:
        """Analyze PR title and body for tutorial patterns"""
        matches = []

        for pattern, confidence in cls.TUTORIAL_PATTERNS.items():
            # Check title - always check all patterns in title
            title_match = re.search(pattern, title, re.I)
            if title_match:
                matches.append(
                    PatternMatch(
                        pattern=pattern,
                        matched_text=title_match.group(),
                        location=Location.TITLE,
                        context=title,
                        confidence=confidence,
                    )
                )

            # Check body - only for high-confidence patterns
            if confidence == Confidence.HIGH and body:
                for match in re.finditer(pattern, body, re.I):
                    matches.append(
                        PatternMatch(
                            pattern=pattern,
                            matched_text=match.group(),
                            location=Location.BODY,
                            context=cls._get_context(body, match.start(), match.end()),
                            confidence=confidence,
                        )
                    )

        return matches

    @classmethod
    def should_auto_close(cls, matches: List[PatternMatch]) -> bool:
        """Determine if PR should be auto-closed based on matches"""
        if not matches:
            return False

        # Auto-close if multiple matches
        if len(matches) > 1:
            return True

        # Auto-close if single match is high-confidence pattern
        single_match = matches[0]
        return single_match.confidence == Confidence.HIGH

    @staticmethod
    def _get_context(
        text: str, match_start: int, match_end: int, context_chars: int = 40
    ) -> str:
        """Get surrounding context for a match"""
        start = max(0, match_start - context_chars)
        end = min(len(text), match_end + context_chars)
        return text[start:end].strip()


# CLI interface for use in GitHub Actions
if __name__ == "__main__":
    import json
    import sys

    if len(sys.argv) < 2:
        print("Usage: python pattern_analyzer.py <command> [args...]")
        sys.exit(1)

    command = sys.argv[1]

    if command == "analyze":
        # Usage: python pattern_analyzer.py analyze "title" "body"
        title = sys.argv[2] if len(sys.argv) > 2 else ""
        body = sys.argv[3] if len(sys.argv) > 3 else ""

        matches = PatternAnalyzer.analyze_pr(title, body)

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

        print(json.dumps(result))

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
