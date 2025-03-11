"""Checker Manager and Checker classes."""
from __future__ import annotations

import argparse
import contextlib
import errno
import logging
import multiprocessing.pool
import operator
import signal
import tokenize
from typing import Any
from typing import Generator
from typing import List
from typing import Optional
from typing import Sequence
from typing import Tuple

from flake8 import defaults
from flake8 import exceptions
from flake8 import processor
from flake8 import utils
from flake8._compat import FSTRING_START
from flake8.discover_files import expand_paths
from flake8.options.parse_args import parse_args
from flake8.plugins.finder import Checkers
from flake8.plugins.finder import LoadedPlugin
from flake8.style_guide import StyleGuideManager

Results = List[Tuple[str, int, int, str, Optional[str]]]

LOG = logging.getLogger(__name__)

SERIAL_RETRY_ERRNOS = {
    # ENOSPC: Added by sigmavirus24
    # > On some operating systems (OSX), multiprocessing may cause an
    # > ENOSPC error while trying to create a Semaphore.
    # > In those cases, we should replace the customized Queue Report
    # > class with pep8's StandardReport class to ensure users don't run
    # > into this problem.
    # > (See also: https://github.com/pycqa/flake8/issues/117)
    errno.ENOSPC,
    # NOTE(sigmavirus24): When adding to this list, include the reasoning
    # on the lines before the error code and always append your error
    # code. Further, please always add a trailing `,` to reduce the visual
    # noise in diffs.
}

_mp_plugins: Checkers
_mp_options: argparse.Namespace


@contextlib.contextmanager
def _mp_prefork(
    plugins: Checkers, options: argparse.Namespace
) -> Generator[None, None, None]:
    # we can save significant startup work w/ `fork` multiprocessing
    global _mp_plugins, _mp_options
    _mp_plugins, _mp_options = plugins, options
    try:
        yield
    finally:
        del _mp_plugins, _mp_options


def _mp_init(argv: Sequence[str]) -> None:
    global _mp_plugins, _mp_options

    # Ensure correct signaling of ^C using multiprocessing.Pool.
    signal.signal(signal.SIGINT, signal.SIG_IGN)

    try:
        # for `fork` this'll already be set
        _mp_plugins, _mp_options  # noqa: B018
    except NameError:
        plugins, options = parse_args(argv)
        _mp_plugins, _mp_options = plugins.checkers, options


def _mp_run(filename: str) -> tuple[str, Results, dict[str, int]]:
    return FileChecker(
        filename=filename, plugins=_mp_plugins, options=_mp_options
    ).run_checks()


class Manager:
    """Manage the parallelism and checker instances for each plugin and file.

    This class will be responsible for the following:

    - Determining the parallelism of Flake8, e.g.:

      * Do we use :mod:`multiprocessing` or is it unavailable?

      * Do we automatically decide on the number of jobs to use or did the
        user provide that?

    - Falling back to a serial way of processing files if we run into an
      OSError related to :mod:`multiprocessing`

    - Organizing the results of each checker so we can group the output
      together and make our output deterministic.
    """

    def __init__(
        self,
        style_guide: StyleGuideManager,
        plugins: Checkers,
        argv: Sequence[str],
    ) -> None:
        """Initialize our Manager instance."""
        self.style_guide = style_guide
        self.options = style_guide.options
        self.plugins = plugins
        self.jobs = self._job_count()
        self.statistics = {
            "files": 0,
            "logical lines": 0,
            "physical lines": 0,
            "tokens": 0,
        }
        self.exclude = (*self.options.exclude, *self.options.extend_exclude)
        self.argv = argv
        self.results: list[tuple[str, Results, dict[str, int]]] = []

    def _process_statistics(self) -> None:
        for _, _, statistics in self.results:
            for statistic in defaults.STATISTIC_NAMES:
                self.statistics[statistic] += statistics[statistic]
        self.statistics["files"] += len(self.filenames)

    def _job_count(self) -> int:
        # First we walk through all of our error cases:
        # - multiprocessing library is not present
        # - the user provided stdin and that's not something we can handle
        #   well
        # - the user provided some awful input

        if utils.is_using_stdin(self.options.filenames):
            LOG.warning(
                "The --jobs option is not compatible with supplying "
                "input using - . Ignoring --jobs arguments."
            )
            return 0

        jobs = self.options.jobs

        # If the value is "auto", we want to let the multiprocessing library
        # decide the number based on the number of CPUs. However, if that
        # function is not implemented for this particular value of Python we
        # default to 1
        if jobs.is_auto:
            try:
                return multiprocessing.cpu_count()
            except NotImplementedError:
                return 0

        # Otherwise, we know jobs should be an integer and we can just convert
        # it to an integer
        return jobs.n_jobs

    def _handle_results(self, filename: str, results: Results) -> int:
        style_guide = self.style_guide
        reported_results_count = 0
        for error_code, line_number, column, text, physical_line in results:
            reported_results_count += style_guide.handle_error(
                code=error_code,
                filename=filename,
                line_number=line_number,
                column_number=column,
                text=text,
                physical_line=physical_line,
            )
        return reported_results_count

    def report(self) -> tuple[int, int]:
        """Report all of the errors found in the managed file checkers.

        This iterates over each of the checkers and reports the errors sorted
        by line number.

        :returns:
            A tuple of the total results found and the results reported.
        """
        results_reported = results_found = 0
        self.results.sort(key=operator.itemgetter(0))
        for filename, results, _ in self.results:
            results.sort(key=operator.itemgetter(1, 2))
            with self.style_guide.processing_file(filename):
                results_reported += self._handle_results(filename, results)
            results_found += len(results)
        return (results_found, results_reported)

    def run_parallel(self) -> None:
        """Run the checkers in parallel."""
        with _mp_prefork(self.plugins, self.options):
            pool = _try_initialize_processpool(self.jobs, self.argv)

        if pool is None:
            self.run_serial()
            return

        pool_closed = False
        try:
            self.results = list(pool.imap_unordered(_mp_run, self.filenames))
            pool.close()
            pool.join()
            pool_closed = True
        finally:
            if not pool_closed:
                pool.terminate()
                pool.join()

    def run_serial(self) -> None:
        """Run the checkers in serial."""
        self.results = [
            FileChecker(
                filename=filename,
                plugins=self.plugins,
                options=self.options,
            ).run_checks()
            for filename in self.filenames
        ]

    def run(self) -> None:
        """Run all the checkers.

        This will intelligently decide whether to run the checks in parallel
        or whether to run them in serial.

        If running the checks in parallel causes a problem (e.g.,
        :issue:`117`) this also implements fallback to serial processing.
        """
        try:
            if self.jobs > 1 and len(self.filenames) > 1:
                self.run_parallel()
            else:
                self.run_serial()
        except KeyboardInterrupt:
            LOG.warning("Flake8 was interrupted by the user")
            raise exceptions.EarlyQuit("Early quit while running checks")

    def start(self) -> None:
        """Start checking files.

        :param paths:
            Path names to check. This is passed directly to
            :meth:`~Manager.make_checkers`.
        """
        LOG.info("Making checkers")
        self.filenames = tuple(
            expand_paths(
                paths=self.options.filenames,
                stdin_display_name=self.options.stdin_display_name,
                filename_patterns=self.options.filename,
                exclude=self.exclude,
            )
        )
        self.jobs = min(len(self.filenames), self.jobs)

    def stop(self) -> None:
        """Stop checking files."""
        self._process_statistics()


class FileChecker:
    """Manage running checks for a file and aggregate the results."""

    def __init__(
        self,
        *,
        filename: str,
        plugins: Checkers,
        options: argparse.Namespace,
    ) -> None:
        """Initialize our file checker."""
        self.options = options
        self.filename = filename
        self.plugins = plugins
        self.results: Results = []
        self.statistics = {
            "tokens": 0,
            "logical lines": 0,
            "physical lines": 0,
        }
        self.processor = self._make_processor()
        self.display_name = filename
        self.should_process = False
        if self.processor is not None:
            self.display_name = self.processor.filename
            self.should_process = not self.processor.should_ignore_file()
            self.statistics["physical lines"] = len(self.processor.lines)

    def __repr__(self) -> str:
        """Provide helpful debugging representation."""
        return f"FileChecker for {self.filename}"

    def _make_processor(self) -> processor.FileProcessor | None:
        try:
            return processor.FileProcessor(self.filename, self.options)
        except OSError as e:
            # If we can not read the file due to an IOError (e.g., the file
            # does not exist or we do not have the permissions to open it)
            # then we need to format that exception for the user.
            # NOTE(sigmavirus24): Historically, pep8 has always reported this
            # as an E902. We probably *want* a better error code for this
            # going forward.
            self.report("E902", 0, 0, f"{type(e).__name__}: {e}")
            return None

    def report(
        self,
        error_code: str | None,
        line_number: int,
        column: int,
        text: str,
    ) -> str:
        """Report an error by storing it in the results list."""
        if error_code is None:
            error_code, text = text.split(" ", 1)

        # If we're recovering from a problem in _make_processor, we will not
        # have this attribute.
        if hasattr(self, "processor") and self.processor is not None:
            line = self.processor.noqa_line_for(line_number)
        else:
            line = None

        self.results.append((error_code, line_number, column, text, line))
        return error_code

    def run_check(self, plugin: LoadedPlugin, **arguments: Any) -> Any:
        """Run the check in a single plugin."""
        assert self.processor is not None, self.filename
        try:
            params = self.processor.keyword_arguments_for(
                plugin.parameters, arguments
            )
        except AttributeError as ae:
            raise exceptions.PluginRequestedUnknownParameters(
                plugin_name=plugin.display_name, exception=ae
            )
        try:
            return plugin.obj(**arguments, **params)
        except Exception as all_exc:
            LOG.critical(
                "Plugin %s raised an unexpected exception",
                plugin.display_name,
                exc_info=True,
            )
            raise exceptions.PluginExecutionFailed(
                filename=self.filename,
                plugin_name=plugin.display_name,
                exception=all_exc,
            )

    @staticmethod
    def _extract_syntax_information(exception: Exception) -> tuple[int, int]:
        if (
            len(exception.args) > 1
            and exception.args[1]
            and len(exception.args[1]) > 2
        ):
            token = exception.args[1]
            row, column = token[1:3]
        elif (
            isinstance(exception, tokenize.TokenError)
            and len(exception.args) == 2
            and len(exception.args[1]) == 2
        ):
            token = ()
            row, column = exception.args[1]
        else:
            token = ()
            row, column = (1, 0)

        if (
            column > 0
            and token
            and isinstance(exception, SyntaxError)
            and len(token) == 4  # Python 3.9 or earlier
        ):
            # NOTE(sigmavirus24): SyntaxErrors report 1-indexed column
            # numbers. We need to decrement the column number by 1 at
            # least.
            column_offset = 1
            row_offset = 0
            # See also: https://github.com/pycqa/flake8/issues/169,
            # https://github.com/PyCQA/flake8/issues/1372
            # On Python 3.9 and earlier, token will be a 4-item tuple with the
            # last item being the string. Starting with 3.10, they added to
            # the tuple so now instead of it ending with the code that failed
            # to parse, it ends with the end of the section of code that
            # failed to parse. Luckily the absolute position in the tuple is
            # stable across versions so we can use that here
            physical_line = token[3]

            # NOTE(sigmavirus24): Not all "tokens" have a string as the last
            # argument. In this event, let's skip trying to find the correct
            # column and row values.
            if physical_line is not None:
                # NOTE(sigmavirus24): SyntaxErrors also don't exactly have a
                # "physical" line so much as what was accumulated by the point
                # tokenizing failed.
                # See also: https://github.com/pycqa/flake8/issues/169
                lines = physical_line.rstrip("\n").split("\n")
                row_offset = len(lines) - 1
                logical_line = lines[0]
                logical_line_length = len(logical_line)
                if column > logical_line_length:
                    column = logical_line_length
            row -= row_offset
            column -= column_offset
        return row, column

    def run_ast_checks(self) -> None:
        """Run all checks expecting an abstract syntax tree."""
        assert self.processor is not None, self.filename
        ast = self.processor.build_ast()

        for plugin in self.plugins.tree:
            checker = self.run_check(plugin, tree=ast)
            # If the plugin uses a class, call the run method of it, otherwise
            # the call should return something iterable itself
            try:
                runner = checker.run()
            except AttributeError:
                runner = checker
            for line_number, offset, text, _ in runner:
                self.report(
                    error_code=None,
                    line_number=line_number,
                    column=offset,
                    text=text,
                )

    def run_logical_checks(self) -> None:
        """Run all checks expecting a logical line."""
        assert self.processor is not None
        comments, logical_line, mapping = self.processor.build_logical_line()
        if not mapping:
            return
        self.processor.update_state(mapping)

        LOG.debug('Logical line: "%s"', logical_line.rstrip())

        for plugin in self.plugins.logical_line:
            self.processor.update_checker_state_for(plugin)
            results = self.run_check(plugin, logical_line=logical_line) or ()
            for offset, text in results:
                line_number, column_offset = find_offset(offset, mapping)
                if line_number == column_offset == 0:
                    LOG.warning("position of error out of bounds: %s", plugin)
                self.report(
                    error_code=None,
                    line_number=line_number,
                    column=column_offset,
                    text=text,
                )

        self.processor.next_logical_line()

    def run_physical_checks(self, physical_line: str) -> None:
        """Run all checks for a given physical line.

        A single physical check may return multiple errors.
        """
        assert self.processor is not None
        for plugin in self.plugins.physical_line:
            self.processor.update_checker_state_for(plugin)
            result = self.run_check(plugin, physical_line=physical_line)

            if result is not None:
                # This is a single result if first element is an int
                column_offset = None
                try:
                    column_offset = result[0]
                except (IndexError, TypeError):
                    pass

                if isinstance(column_offset, int):
                    # If we only have a single result, convert to a collection
                    result = (result,)

                for result_single in result:
                    column_offset, text = result_single
                    self.report(
                        error_code=None,
                        line_number=self.processor.line_number,
                        column=column_offset,
                        text=text,
                    )

    def process_tokens(self) -> None:
        """Process tokens and trigger checks.

        Instead of using this directly, you should use
        :meth:`flake8.checker.FileChecker.run_checks`.
        """
        assert self.processor is not None
        parens = 0
        statistics = self.statistics
        file_processor = self.processor
        prev_physical = ""
        for token in file_processor.generate_tokens():
            statistics["tokens"] += 1
            self.check_physical_eol(token, prev_physical)
            token_type, text = token[0:2]
            if token_type == tokenize.OP:
                parens = processor.count_parentheses(parens, text)
            elif parens == 0:
                if processor.token_is_newline(token):
                    self.handle_newline(token_type)
            prev_physical = token[4]

        if file_processor.tokens:
            # If any tokens are left over, process them
            self.run_physical_checks(file_processor.lines[-1])
            self.run_logical_checks()

    def run_checks(self) -> tuple[str, Results, dict[str, int]]:
        """Run checks against the file."""
        if self.processor is None or not self.should_process:
            return self.display_name, self.results, self.statistics

        try:
            self.run_ast_checks()
            self.process_tokens()
        except (SyntaxError, tokenize.TokenError) as e:
            code = "E902" if isinstance(e, tokenize.TokenError) else "E999"
            row, column = self._extract_syntax_information(e)
            self.report(code, row, column, f"{type(e).__name__}: {e.args[0]}")
            return self.display_name, self.results, self.statistics

        logical_lines = self.processor.statistics["logical lines"]
        self.statistics["logical lines"] = logical_lines
        return self.display_name, self.results, self.statistics

    def handle_newline(self, token_type: int) -> None:
        """Handle the logic when encountering a newline token."""
        assert self.processor is not None
        if token_type == tokenize.NEWLINE:
            self.run_logical_checks()
            self.processor.reset_blank_before()
        elif len(self.processor.tokens) == 1:
            # The physical line contains only this token.
            self.processor.visited_new_blank_line()
            self.processor.delete_first_token()
        else:
            self.run_logical_checks()

    def check_physical_eol(
        self, token: tokenize.TokenInfo, prev_physical: str
    ) -> None:
        """Run physical checks if and only if it is at the end of the line."""
        assert self.processor is not None
        if token.type == FSTRING_START:  # pragma: >=3.12 cover
            self.processor.fstring_start(token.start[0])
        # a newline token ends a single physical line.
        elif processor.is_eol_token(token):
            # if the file does not end with a newline, the NEWLINE
            # token is inserted by the parser, but it does not contain
            # the previous physical line in `token[4]`
            if token.line == "":
                self.run_physical_checks(prev_physical)
            else:
                self.run_physical_checks(token.line)
        elif processor.is_multiline_string(token):
            # Less obviously, a string that contains newlines is a
            # multiline string, either triple-quoted or with internal
            # newlines backslash-escaped. Check every physical line in the
            # string *except* for the last one: its newline is outside of
            # the multiline string, so we consider it a regular physical
            # line, and will check it like any other physical line.
            #
            # Subtleties:
            # - have to wind self.line_number back because initially it
            #   points to the last line of the string, and we want
            #   check_physical() to give accurate feedback
            for line in self.processor.multiline_string(token):
                self.run_physical_checks(line)


def _try_initialize_processpool(
    job_count: int,
    argv: Sequence[str],
) -> multiprocessing.pool.Pool | None:
    """Return a new process pool instance if we are able to create one."""
    try:
        return multiprocessing.Pool(job_count, _mp_init, initargs=(argv,))
    except OSError as err:
        if err.errno not in SERIAL_RETRY_ERRNOS:
            raise
    except ImportError:
        pass

    return None


def find_offset(
    offset: int, mapping: processor._LogicalMapping
) -> tuple[int, int]:
    """Find the offset tuple for a single offset."""
    if isinstance(offset, tuple):
        return offset

    for token in mapping:
        token_offset = token[0]
        if offset <= token_offset:
            position = token[1]
            break
    else:
        position = (0, 0)
        offset = token_offset = 0
    return (position[0], position[1] + offset - token_offset)
