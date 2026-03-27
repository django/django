"""Implementation of the StyleGuide used by Flake8."""
from __future__ import annotations

import argparse
import contextlib
import copy
import enum
import functools
import logging
from collections.abc import Generator
from collections.abc import Sequence

from flake8 import defaults
from flake8 import statistics
from flake8 import utils
from flake8.formatting import base as base_formatter
from flake8.violation import Violation

__all__ = ("StyleGuide",)

LOG = logging.getLogger(__name__)


class Selected(enum.Enum):
    """Enum representing an explicitly or implicitly selected code."""

    Explicitly = "explicitly selected"
    Implicitly = "implicitly selected"


class Ignored(enum.Enum):
    """Enum representing an explicitly or implicitly ignored code."""

    Explicitly = "explicitly ignored"
    Implicitly = "implicitly ignored"


class Decision(enum.Enum):
    """Enum representing whether a code should be ignored or selected."""

    Ignored = "ignored error"
    Selected = "selected error"


def _explicitly_chosen(
    *,
    option: list[str] | None,
    extend: list[str] | None,
) -> tuple[str, ...]:
    ret = [*(option or []), *(extend or [])]
    return tuple(sorted(ret, reverse=True))


def _select_ignore(
    *,
    option: list[str] | None,
    default: tuple[str, ...],
    extended_default: list[str],
    extend: list[str] | None,
) -> tuple[str, ...]:
    # option was explicitly set, ignore the default and extended default
    if option is not None:
        ret = [*option, *(extend or [])]
    else:
        ret = [*default, *extended_default, *(extend or [])]
    return tuple(sorted(ret, reverse=True))


class DecisionEngine:
    """A class for managing the decision process around violations.

    This contains the logic for whether a violation should be reported or
    ignored.
    """

    def __init__(self, options: argparse.Namespace) -> None:
        """Initialize the engine."""
        self.cache: dict[str, Decision] = {}

        self.selected_explicitly = _explicitly_chosen(
            option=options.select,
            extend=options.extend_select,
        )
        self.ignored_explicitly = _explicitly_chosen(
            option=options.ignore,
            extend=options.extend_ignore,
        )

        self.selected = _select_ignore(
            option=options.select,
            default=(),
            extended_default=options.extended_default_select,
            extend=options.extend_select,
        )
        self.ignored = _select_ignore(
            option=options.ignore,
            default=defaults.IGNORE,
            extended_default=options.extended_default_ignore,
            extend=options.extend_ignore,
        )

    def was_selected(self, code: str) -> Selected | Ignored:
        """Determine if the code has been selected by the user.

        :param code: The code for the check that has been run.
        :returns:
            Selected.Implicitly if the selected list is empty,
            Selected.Explicitly if the selected list is not empty and a match
            was found,
            Ignored.Implicitly if the selected list is not empty but no match
            was found.
        """
        if code.startswith(self.selected_explicitly):
            return Selected.Explicitly
        elif code.startswith(self.selected):
            return Selected.Implicitly
        else:
            return Ignored.Implicitly

    def was_ignored(self, code: str) -> Selected | Ignored:
        """Determine if the code has been ignored by the user.

        :param code:
            The code for the check that has been run.
        :returns:
            Selected.Implicitly if the ignored list is empty,
            Ignored.Explicitly if the ignored list is not empty and a match was
            found,
            Selected.Implicitly if the ignored list is not empty but no match
            was found.
        """
        if code.startswith(self.ignored_explicitly):
            return Ignored.Explicitly
        elif code.startswith(self.ignored):
            return Ignored.Implicitly
        else:
            return Selected.Implicitly

    def make_decision(self, code: str) -> Decision:
        """Decide if code should be ignored or selected."""
        selected = self.was_selected(code)
        ignored = self.was_ignored(code)
        LOG.debug(
            "The user configured %r to be %r, %r",
            code,
            selected,
            ignored,
        )

        if isinstance(selected, Selected) and isinstance(ignored, Selected):
            return Decision.Selected
        elif isinstance(selected, Ignored) and isinstance(ignored, Ignored):
            return Decision.Ignored
        elif (
            selected is Selected.Explicitly
            and ignored is not Ignored.Explicitly
        ):
            return Decision.Selected
        elif (
            selected is not Selected.Explicitly
            and ignored is Ignored.Explicitly
        ):
            return Decision.Ignored
        elif selected is Ignored.Implicitly and ignored is Selected.Implicitly:
            return Decision.Ignored
        elif (
            selected is Selected.Explicitly and ignored is Ignored.Explicitly
        ) or (
            selected is Selected.Implicitly and ignored is Ignored.Implicitly
        ):
            # we only get here if it was in both lists: longest prefix wins
            select = next(s for s in self.selected if code.startswith(s))
            ignore = next(s for s in self.ignored if code.startswith(s))
            if len(select) > len(ignore):
                return Decision.Selected
            else:
                return Decision.Ignored
        else:
            raise AssertionError(f"unreachable {code} {selected} {ignored}")

    def decision_for(self, code: str) -> Decision:
        """Return the decision for a specific code.

        This method caches the decisions for codes to avoid retracing the same
        logic over and over again. We only care about the select and ignore
        rules as specified by the user in their configuration files and
        command-line flags.

        This method does not look at whether the specific line is being
        ignored in the file itself.

        :param code: The code for the check that has been run.
        """
        decision = self.cache.get(code)
        if decision is None:
            decision = self.make_decision(code)
            self.cache[code] = decision
            LOG.debug('"%s" will be "%s"', code, decision)
        return decision


class StyleGuideManager:
    """Manage multiple style guides for a single run."""

    def __init__(
        self,
        options: argparse.Namespace,
        formatter: base_formatter.BaseFormatter,
        decider: DecisionEngine | None = None,
    ) -> None:
        """Initialize our StyleGuide.

        .. todo:: Add parameter documentation.
        """
        self.options = options
        self.formatter = formatter
        self.stats = statistics.Statistics()
        self.decider = decider or DecisionEngine(options)
        self.style_guides: list[StyleGuide] = []
        self.default_style_guide = StyleGuide(
            options, formatter, self.stats, decider=decider
        )
        self.style_guides = [
            self.default_style_guide,
            *self.populate_style_guides_with(options),
        ]

        self.style_guide_for = functools.cache(self._style_guide_for)

    def populate_style_guides_with(
        self, options: argparse.Namespace
    ) -> Generator[StyleGuide]:
        """Generate style guides from the per-file-ignores option.

        :param options:
            The original options parsed from the CLI and config file.
        :returns:
            A copy of the default style guide with overridden values.
        """
        per_file = utils.parse_files_to_codes_mapping(options.per_file_ignores)
        for filename, violations in per_file:
            yield self.default_style_guide.copy(
                filename=filename, extend_ignore_with=violations
            )

    def _style_guide_for(self, filename: str) -> StyleGuide:
        """Find the StyleGuide for the filename in particular."""
        return max(
            (g for g in self.style_guides if g.applies_to(filename)),
            key=lambda g: len(g.filename or ""),
        )

    @contextlib.contextmanager
    def processing_file(self, filename: str) -> Generator[StyleGuide]:
        """Record the fact that we're processing the file's results."""
        guide = self.style_guide_for(filename)
        with guide.processing_file(filename):
            yield guide

    def handle_error(
        self,
        code: str,
        filename: str,
        line_number: int,
        column_number: int,
        text: str,
        physical_line: str | None = None,
    ) -> int:
        """Handle an error reported by a check.

        :param code:
            The error code found, e.g., E123.
        :param filename:
            The file in which the error was found.
        :param line_number:
            The line number (where counting starts at 1) at which the error
            occurs.
        :param column_number:
            The column number (where counting starts at 1) at which the error
            occurs.
        :param text:
            The text of the error message.
        :param physical_line:
            The actual physical line causing the error.
        :returns:
            1 if the error was reported. 0 if it was ignored. This is to allow
            for counting of the number of errors found that were not ignored.
        """
        guide = self.style_guide_for(filename)
        return guide.handle_error(
            code, filename, line_number, column_number, text, physical_line
        )


class StyleGuide:
    """Manage a Flake8 user's style guide."""

    def __init__(
        self,
        options: argparse.Namespace,
        formatter: base_formatter.BaseFormatter,
        stats: statistics.Statistics,
        filename: str | None = None,
        decider: DecisionEngine | None = None,
    ):
        """Initialize our StyleGuide.

        .. todo:: Add parameter documentation.
        """
        self.options = options
        self.formatter = formatter
        self.stats = stats
        self.decider = decider or DecisionEngine(options)
        self.filename = filename
        if self.filename:
            self.filename = utils.normalize_path(self.filename)

    def __repr__(self) -> str:
        """Make it easier to debug which StyleGuide we're using."""
        return f"<StyleGuide [{self.filename}]>"

    def copy(
        self,
        filename: str | None = None,
        extend_ignore_with: Sequence[str] | None = None,
    ) -> StyleGuide:
        """Create a copy of this style guide with different values."""
        filename = filename or self.filename
        options = copy.deepcopy(self.options)
        options.extend_ignore = options.extend_ignore or []
        options.extend_ignore.extend(extend_ignore_with or [])
        return StyleGuide(
            options, self.formatter, self.stats, filename=filename
        )

    @contextlib.contextmanager
    def processing_file(self, filename: str) -> Generator[StyleGuide]:
        """Record the fact that we're processing the file's results."""
        self.formatter.beginning(filename)
        yield self
        self.formatter.finished(filename)

    def applies_to(self, filename: str) -> bool:
        """Check if this StyleGuide applies to the file.

        :param filename:
            The name of the file with violations that we're potentially
            applying this StyleGuide to.
        :returns:
            True if this applies, False otherwise
        """
        if self.filename is None:
            return True
        return utils.matches_filename(
            filename,
            patterns=[self.filename],
            log_message=f'{self!r} does %(whether)smatch "%(path)s"',
            logger=LOG,
        )

    def should_report_error(self, code: str) -> Decision:
        """Determine if the error code should be reported or ignored.

        This method only cares about the select and ignore rules as specified
        by the user in their configuration files and command-line flags.

        This method does not look at whether the specific line is being
        ignored in the file itself.

        :param code:
            The code for the check that has been run.
        """
        return self.decider.decision_for(code)

    def handle_error(
        self,
        code: str,
        filename: str,
        line_number: int,
        column_number: int,
        text: str,
        physical_line: str | None = None,
    ) -> int:
        """Handle an error reported by a check.

        :param code:
            The error code found, e.g., E123.
        :param filename:
            The file in which the error was found.
        :param line_number:
            The line number (where counting starts at 1) at which the error
            occurs.
        :param column_number:
            The column number (where counting starts at 1) at which the error
            occurs.
        :param text:
            The text of the error message.
        :param physical_line:
            The actual physical line causing the error.
        :returns:
            1 if the error was reported. 0 if it was ignored. This is to allow
            for counting of the number of errors found that were not ignored.
        """
        disable_noqa = self.options.disable_noqa
        # NOTE(sigmavirus24): Apparently we're provided with 0-indexed column
        # numbers so we have to offset that here.
        if not column_number:
            column_number = 0
        error = Violation(
            code,
            filename,
            line_number,
            column_number + 1,
            text,
            physical_line,
        )
        error_is_selected = (
            self.should_report_error(error.code) is Decision.Selected
        )
        is_not_inline_ignored = error.is_inline_ignored(disable_noqa) is False
        if error_is_selected and is_not_inline_ignored:
            self.formatter.handle(error)
            self.stats.record(error)
            return 1
        return 0
