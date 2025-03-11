"""Plugin built-in to Flake8 to treat pyflakes as a plugin."""
from __future__ import annotations

import argparse
import ast
import logging
from typing import Any
from typing import Generator

import pyflakes.checker

from flake8.options.manager import OptionManager

LOG = logging.getLogger(__name__)

FLAKE8_PYFLAKES_CODES = {
    "UnusedImport": "F401",
    "ImportShadowedByLoopVar": "F402",
    "ImportStarUsed": "F403",
    "LateFutureImport": "F404",
    "ImportStarUsage": "F405",
    "ImportStarNotPermitted": "F406",
    "FutureFeatureNotDefined": "F407",
    "PercentFormatInvalidFormat": "F501",
    "PercentFormatExpectedMapping": "F502",
    "PercentFormatExpectedSequence": "F503",
    "PercentFormatExtraNamedArguments": "F504",
    "PercentFormatMissingArgument": "F505",
    "PercentFormatMixedPositionalAndNamed": "F506",
    "PercentFormatPositionalCountMismatch": "F507",
    "PercentFormatStarRequiresSequence": "F508",
    "PercentFormatUnsupportedFormatCharacter": "F509",
    "StringDotFormatInvalidFormat": "F521",
    "StringDotFormatExtraNamedArguments": "F522",
    "StringDotFormatExtraPositionalArguments": "F523",
    "StringDotFormatMissingArgument": "F524",
    "StringDotFormatMixingAutomatic": "F525",
    "FStringMissingPlaceholders": "F541",
    "MultiValueRepeatedKeyLiteral": "F601",
    "MultiValueRepeatedKeyVariable": "F602",
    "TooManyExpressionsInStarredAssignment": "F621",
    "TwoStarredExpressions": "F622",
    "AssertTuple": "F631",
    "IsLiteral": "F632",
    "InvalidPrintSyntax": "F633",
    "IfTuple": "F634",
    "BreakOutsideLoop": "F701",
    "ContinueOutsideLoop": "F702",
    "YieldOutsideFunction": "F704",
    "ReturnOutsideFunction": "F706",
    "DefaultExceptNotLast": "F707",
    "DoctestSyntaxError": "F721",
    "ForwardAnnotationSyntaxError": "F722",
    "RedefinedWhileUnused": "F811",
    "UndefinedName": "F821",
    "UndefinedExport": "F822",
    "UndefinedLocal": "F823",
    "DuplicateArgument": "F831",
    "UnusedVariable": "F841",
    "UnusedAnnotation": "F842",
    "RaiseNotImplemented": "F901",
}


class FlakesChecker(pyflakes.checker.Checker):
    """Subclass the Pyflakes checker to conform with the flake8 API."""

    with_doctest = False

    def __init__(self, tree: ast.AST, filename: str) -> None:
        """Initialize the PyFlakes plugin with an AST tree and filename."""
        super().__init__(
            tree, filename=filename, withDoctest=self.with_doctest
        )

    @classmethod
    def add_options(cls, parser: OptionManager) -> None:
        """Register options for PyFlakes on the Flake8 OptionManager."""
        parser.add_option(
            "--builtins",
            parse_from_config=True,
            comma_separated_list=True,
            help="define more built-ins, comma separated",
        )
        parser.add_option(
            "--doctests",
            default=False,
            action="store_true",
            parse_from_config=True,
            help="also check syntax of the doctests",
        )

    @classmethod
    def parse_options(cls, options: argparse.Namespace) -> None:
        """Parse option values from Flake8's OptionManager."""
        if options.builtins:
            cls.builtIns = cls.builtIns.union(options.builtins)
        cls.with_doctest = options.doctests

    def run(self) -> Generator[tuple[int, int, str, type[Any]], None, None]:
        """Run the plugin."""
        for message in self.messages:
            col = getattr(message, "col", 0)
            yield (
                message.lineno,
                col,
                "{} {}".format(
                    FLAKE8_PYFLAKES_CODES.get(type(message).__name__, "F999"),
                    message.message % message.message_args,
                ),
                message.__class__,
            )
