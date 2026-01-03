"""Contains the Violation error class used internally."""
from __future__ import annotations

import functools
import linecache
import logging
from re import Match
from typing import NamedTuple

from flake8 import defaults
from flake8 import utils


LOG = logging.getLogger(__name__)


@functools.lru_cache(maxsize=512)
def _find_noqa(physical_line: str) -> Match[str] | None:
    return defaults.NOQA_INLINE_REGEXP.search(physical_line)


class Violation(NamedTuple):
    """Class representing a violation reported by Flake8."""

    code: str
    filename: str
    line_number: int
    column_number: int
    text: str
    physical_line: str | None

    def is_inline_ignored(self, disable_noqa: bool) -> bool:
        """Determine if a comment has been added to ignore this line.

        :param disable_noqa:
            Whether or not users have provided ``--disable-noqa``.
        :returns:
            True if error is ignored in-line, False otherwise.
        """
        physical_line = self.physical_line
        # TODO(sigmavirus24): Determine how to handle stdin with linecache
        if disable_noqa:
            return False

        if physical_line is None:
            physical_line = linecache.getline(self.filename, self.line_number)
        noqa_match = _find_noqa(physical_line)
        if noqa_match is None:
            LOG.debug("%r is not inline ignored", self)
            return False

        codes_str = noqa_match.groupdict()["codes"]
        if codes_str is None:
            LOG.debug("%r is ignored by a blanket ``# noqa``", self)
            return True

        codes = set(utils.parse_comma_separated_list(codes_str))
        if self.code in codes or self.code.startswith(tuple(codes)):
            LOG.debug(
                "%r is ignored specifically inline with ``# noqa: %s``",
                self,
                codes_str,
            )
            return True

        LOG.debug(
            "%r is not ignored inline with ``# noqa: %s``", self, codes_str
        )
        return False
