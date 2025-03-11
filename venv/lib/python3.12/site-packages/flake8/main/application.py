"""Module containing the application logic for Flake8."""
from __future__ import annotations

import argparse
import json
import logging
import time
from typing import Sequence

import flake8
from flake8 import checker
from flake8 import defaults
from flake8 import exceptions
from flake8 import style_guide
from flake8.formatting.base import BaseFormatter
from flake8.main import debug
from flake8.options.parse_args import parse_args
from flake8.plugins import finder
from flake8.plugins import reporter


LOG = logging.getLogger(__name__)


class Application:
    """Abstract our application into a class."""

    def __init__(self) -> None:
        """Initialize our application."""
        #: The timestamp when the Application instance was instantiated.
        self.start_time = time.time()
        #: The timestamp when the Application finished reported errors.
        self.end_time: float | None = None

        self.plugins: finder.Plugins | None = None
        #: The user-selected formatter from :attr:`formatting_plugins`
        self.formatter: BaseFormatter | None = None
        #: The :class:`flake8.style_guide.StyleGuideManager` built from the
        #: user's options
        self.guide: style_guide.StyleGuideManager | None = None
        #: The :class:`flake8.checker.Manager` that will handle running all of
        #: the checks selected by the user.
        self.file_checker_manager: checker.Manager | None = None

        #: The user-supplied options parsed into an instance of
        #: :class:`argparse.Namespace`
        self.options: argparse.Namespace | None = None
        #: The number of errors, warnings, and other messages after running
        #: flake8 and taking into account ignored errors and lines.
        self.result_count = 0
        #: The total number of errors before accounting for ignored errors and
        #: lines.
        self.total_result_count = 0
        #: Whether or not something catastrophic happened and we should exit
        #: with a non-zero status code
        self.catastrophic_failure = False

    def exit_code(self) -> int:
        """Return the program exit code."""
        if self.catastrophic_failure:
            return 1
        assert self.options is not None
        if self.options.exit_zero:
            return 0
        else:
            return int(self.result_count > 0)

    def make_formatter(self) -> None:
        """Initialize a formatter based on the parsed options."""
        assert self.plugins is not None
        assert self.options is not None
        self.formatter = reporter.make(self.plugins.reporters, self.options)

    def make_guide(self) -> None:
        """Initialize our StyleGuide."""
        assert self.formatter is not None
        assert self.options is not None
        self.guide = style_guide.StyleGuideManager(
            self.options, self.formatter
        )

    def make_file_checker_manager(self, argv: Sequence[str]) -> None:
        """Initialize our FileChecker Manager."""
        assert self.guide is not None
        assert self.plugins is not None
        self.file_checker_manager = checker.Manager(
            style_guide=self.guide,
            plugins=self.plugins.checkers,
            argv=argv,
        )

    def run_checks(self) -> None:
        """Run the actual checks with the FileChecker Manager.

        This method encapsulates the logic to make a
        :class:`~flake8.checker.Manger` instance run the checks it is
        managing.
        """
        assert self.file_checker_manager is not None

        self.file_checker_manager.start()
        try:
            self.file_checker_manager.run()
        except exceptions.PluginExecutionFailed as plugin_failed:
            print(str(plugin_failed))
            print("Run flake8 with greater verbosity to see more details")
            self.catastrophic_failure = True
        LOG.info("Finished running")
        self.file_checker_manager.stop()
        self.end_time = time.time()

    def report_benchmarks(self) -> None:
        """Aggregate, calculate, and report benchmarks for this run."""
        assert self.options is not None
        if not self.options.benchmark:
            return

        assert self.file_checker_manager is not None
        assert self.end_time is not None
        time_elapsed = self.end_time - self.start_time
        statistics = [("seconds elapsed", time_elapsed)]
        add_statistic = statistics.append
        for statistic in defaults.STATISTIC_NAMES + ("files",):
            value = self.file_checker_manager.statistics[statistic]
            total_description = f"total {statistic} processed"
            add_statistic((total_description, value))
            per_second_description = f"{statistic} processed per second"
            add_statistic((per_second_description, int(value / time_elapsed)))

        assert self.formatter is not None
        self.formatter.show_benchmarks(statistics)

    def report_errors(self) -> None:
        """Report all the errors found by flake8 3.0.

        This also updates the :attr:`result_count` attribute with the total
        number of errors, warnings, and other messages found.
        """
        LOG.info("Reporting errors")
        assert self.file_checker_manager is not None
        results = self.file_checker_manager.report()
        self.total_result_count, self.result_count = results
        LOG.info(
            "Found a total of %d violations and reported %d",
            self.total_result_count,
            self.result_count,
        )

    def report_statistics(self) -> None:
        """Aggregate and report statistics from this run."""
        assert self.options is not None
        if not self.options.statistics:
            return

        assert self.formatter is not None
        assert self.guide is not None
        self.formatter.show_statistics(self.guide.stats)

    def initialize(self, argv: Sequence[str]) -> None:
        """Initialize the application to be run.

        This finds the plugins, registers their options, and parses the
        command-line arguments.
        """
        self.plugins, self.options = parse_args(argv)

        if self.options.bug_report:
            info = debug.information(flake8.__version__, self.plugins)
            print(json.dumps(info, indent=2, sort_keys=True))
            raise SystemExit(0)

        self.make_formatter()
        self.make_guide()
        self.make_file_checker_manager(argv)

    def report(self) -> None:
        """Report errors, statistics, and benchmarks."""
        assert self.formatter is not None
        self.formatter.start()
        self.report_errors()
        self.report_statistics()
        self.report_benchmarks()
        self.formatter.stop()

    def _run(self, argv: Sequence[str]) -> None:
        self.initialize(argv)
        self.run_checks()
        self.report()

    def run(self, argv: Sequence[str]) -> None:
        """Run our application.

        This method will also handle KeyboardInterrupt exceptions for the
        entirety of the flake8 application. If it sees a KeyboardInterrupt it
        will forcibly clean up the :class:`~flake8.checker.Manager`.
        """
        try:
            self._run(argv)
        except KeyboardInterrupt as exc:
            print("... stopped")
            LOG.critical("Caught keyboard interrupt from user")
            LOG.exception(exc)
            self.catastrophic_failure = True
        except exceptions.ExecutionError as exc:
            print("There was a critical error during execution of Flake8:")
            print(exc)
            LOG.exception(exc)
            self.catastrophic_failure = True
        except exceptions.EarlyQuit:
            self.catastrophic_failure = True
            print("... stopped while processing files")
        else:
            assert self.options is not None
            if self.options.count:
                print(self.result_count)
