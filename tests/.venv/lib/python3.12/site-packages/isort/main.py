"""Tool for sorting imports alphabetically, and automatically separated into sections."""

import argparse
import functools
import json
import os
import sys
from collections.abc import Sequence
from gettext import gettext as _
from io import TextIOWrapper
from pathlib import Path
from typing import Any
from warnings import warn

from . import __version__, api, files, sections
from .exceptions import FileSkipped, ISortError, UnsupportedEncoding
from .format import create_terminal_printer
from .logo import ASCII_ART
from .profiles import profiles
from .settings import VALID_PY_TARGETS, Config, find_all_configs
from .utils import Trie
from .wrap_modes import WrapModes

DEPRECATED_SINGLE_DASH_ARGS = {
    "-ac",
    "-af",
    "-ca",
    "-cs",
    "-df",
    "-ds",
    "-dt",
    "-fas",
    "-fass",
    "-ff",
    "-fgw",
    "-fss",
    "-lai",
    "-lbt",
    "-le",
    "-ls",
    "-nis",
    "-nlb",
    "-ot",
    "-rr",
    "-sd",
    "-sg",
    "-sl",
    "-sp",
    "-tc",
    "-wl",
    "-ws",
}
QUICK_GUIDE = f"""
{ASCII_ART}

Nothing to do: no files or paths have been passed in!

Try one of the following:

    `isort .` - sort all Python files, starting from the current directory, recursively.
    `isort . --interactive` - Do the same, but ask before making any changes.
    `isort . --check --diff` - Check to see if imports are correctly sorted within this project.
    `isort --help` - In-depth information about isort's available command-line options.

Visit https://pycqa.github.io/isort/ for complete information about how to use isort.
"""


class SortAttempt:
    def __init__(self, incorrectly_sorted: bool, skipped: bool, supported_encoding: bool) -> None:
        self.incorrectly_sorted = incorrectly_sorted
        self.skipped = skipped
        self.supported_encoding = supported_encoding


def sort_imports(
    file_name: str,
    config: Config,
    check: bool = False,
    ask_to_apply: bool = False,
    write_to_stdout: bool = False,
    **kwargs: Any,
) -> SortAttempt | None:
    incorrectly_sorted: bool = False
    skipped: bool = False
    try:
        if check:
            try:
                incorrectly_sorted = not api.check_file(file_name, config=config, **kwargs)
            except FileSkipped:
                skipped = True
            return SortAttempt(incorrectly_sorted, skipped, True)

        try:
            incorrectly_sorted = not api.sort_file(
                file_name,
                config=config,
                ask_to_apply=ask_to_apply,
                write_to_stdout=write_to_stdout,
                **kwargs,
            )
        except FileSkipped:
            skipped = True
        return SortAttempt(incorrectly_sorted, skipped, True)
    except (OSError, ValueError) as error:
        warn(f"Unable to parse file {file_name} due to {error}", stacklevel=2)
        return None
    except UnsupportedEncoding:
        if config.verbose:
            warn(f"Encoding not supported for {file_name}", stacklevel=2)
        return SortAttempt(incorrectly_sorted, skipped, False)
    except ISortError as error:
        _print_hard_fail(config, message=str(error))
        sys.exit(1)
    except Exception:
        _print_hard_fail(config, offending_file=file_name)
        raise


def _print_hard_fail(
    config: Config, offending_file: str | None = None, message: str | None = None
) -> None:
    """Fail on unrecoverable exception with custom message."""
    message = message or (
        f"Unrecoverable exception thrown when parsing {offending_file or ''}! "
        "This should NEVER happen.\n"
        "If encountered, please open an issue: https://github.com/PyCQA/isort/issues/new"
    )
    printer = create_terminal_printer(
        color=config.color_output, error=config.format_error, success=config.format_success
    )
    printer.error(message)


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Sort Python import definitions alphabetically "
        "within logical sections. Run with no arguments to see a quick "
        "start guide, otherwise, one or more files/directories/stdin must be provided. "
        "Use `-` as the first argument to represent stdin. Use --interactive to use the pre 5.0.0 "
        "interactive behavior."
        " "
        "If you've used isort 4 but are new to isort 5, see the upgrading guide: "
        "https://pycqa.github.io/isort/docs/upgrade_guides/5.0.0.html",
        add_help=False,  # prevent help option from appearing in "optional arguments" group
    )

    general_group = parser.add_argument_group("general options")
    target_group = parser.add_argument_group("target options")
    output_group = parser.add_argument_group("general output options")
    inline_args_group = output_group.add_mutually_exclusive_group()
    section_group = parser.add_argument_group("section output options")
    deprecated_group = parser.add_argument_group("deprecated options")

    general_group.add_argument(
        "-h",
        "--help",
        action="help",
        default=argparse.SUPPRESS,
        help=_("show this help message and exit"),
    )
    general_group.add_argument(
        "-V",
        "--version",
        action="store_true",
        dest="show_version",
        help="Displays the currently installed version of isort.",
    )
    general_group.add_argument(
        "--vn",
        "--version-number",
        action="version",
        version=__version__,
        help="Returns just the current version number without the logo",
    )
    general_group.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        dest="verbose",
        help="Shows verbose output, such as when files are skipped or when a check is successful.",
    )
    general_group.add_argument(
        "--only-modified",
        "--om",
        dest="only_modified",
        action="store_true",
        help="Suppresses verbose output for non-modified files.",
    )
    general_group.add_argument(
        "--dedup-headings",
        dest="dedup_headings",
        action="store_true",
        help="Tells isort to only show an identical custom import heading comment once, even if"
        " there are multiple sections with the comment set.",
    )
    general_group.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        dest="quiet",
        help="Shows extra quiet output, only errors are outputted.",
    )
    general_group.add_argument(
        "-d",
        "--stdout",
        help="Force resulting output to stdout, instead of in-place.",
        dest="write_to_stdout",
        action="store_true",
    )
    general_group.add_argument(
        "--overwrite-in-place",
        help="Tells isort to overwrite in place using the same file handle. "
        "Comes at a performance and memory usage penalty over its standard "
        "approach but ensures all file flags and modes stay unchanged.",
        dest="overwrite_in_place",
        action="store_true",
    )
    general_group.add_argument(
        "--show-config",
        dest="show_config",
        action="store_true",
        help="See isort's determined config, as well as sources of config options.",
    )
    general_group.add_argument(
        "--show-files",
        dest="show_files",
        action="store_true",
        help="See the files isort will be run against with the current config options.",
    )
    general_group.add_argument(
        "--df",
        "--diff",
        dest="show_diff",
        action="store_true",
        help="Prints a diff of all the changes isort would make to a file, instead of "
        "changing it in place",
    )
    general_group.add_argument(
        "-c",
        "--check-only",
        "--check",
        action="store_true",
        dest="check",
        help="Checks the file for unsorted / unformatted imports and prints them to the "
        "command line without modifying the file. Returns 0 when nothing would change and "
        "returns 1 when the file would be reformatted.",
    )
    general_group.add_argument(
        "--ws",
        "--ignore-whitespace",
        action="store_true",
        dest="ignore_whitespace",
        help="Tells isort to ignore whitespace differences when --check-only is being used.",
    )
    general_group.add_argument(
        "--sp",
        "--settings-path",
        "--settings-file",
        "--settings",
        dest="settings_path",
        help="Explicitly set the settings path or file instead of auto determining "
        "based on file location.",
    )
    general_group.add_argument(
        "--cr",
        "--config-root",
        dest="config_root",
        help="Explicitly set the config root for resolving all configs. When used "
        "with the --resolve-all-configs flag, isort will look at all sub-folders "
        "in this config root to resolve config files and sort files based on the "
        "closest available config(if any)",
    )
    general_group.add_argument(
        "--resolve-all-configs",
        dest="resolve_all_configs",
        action="store_true",
        help="Tells isort to resolve the configs for all sub-directories "
        "and sort files in terms of its closest config files.",
    )
    general_group.add_argument(
        "--profile",
        dest="profile",
        type=str,
        help="Base profile type to use for configuration. "
        f"Profiles include: {', '.join(profiles.keys())}. As well as any shared profiles.",
    )
    general_group.add_argument(
        "--old-finders",
        "--magic-placement",
        dest="old_finders",
        action="store_true",
        help="Use the old deprecated finder logic that relies on environment introspection magic.",
    )
    general_group.add_argument(
        "-j",
        "--jobs",
        help="Number of files to process in parallel. Negative value means use number of CPUs.",
        dest="jobs",
        type=int,
        nargs="?",
        const=-1,
    )
    general_group.add_argument(
        "--ac",
        "--atomic",
        dest="atomic",
        action="store_true",
        help="Ensures the output doesn't save if the resulting file contains syntax errors.",
    )
    general_group.add_argument(
        "--interactive",
        dest="ask_to_apply",
        action="store_true",
        help="Tells isort to apply changes interactively.",
    )
    general_group.add_argument(
        "--format-error",
        dest="format_error",
        help="Override the format used to print errors.",
    )
    general_group.add_argument(
        "--format-success",
        dest="format_success",
        help="Override the format used to print success.",
    )
    general_group.add_argument(
        "--srx",
        "--sort-reexports",
        dest="sort_reexports",
        action="store_true",
        help="Automatically sort all re-exports (module level __all__ collections)",
    )

    target_group.add_argument(
        "files", nargs="*", help="One or more Python source files that need their imports sorted."
    )
    target_group.add_argument(
        "--filter-files",
        dest="filter_files",
        action="store_true",
        help="Tells isort to filter files even when they are explicitly passed in as "
        "part of the CLI command.",
    )
    target_group.add_argument(
        "-s",
        "--skip",
        help="Files that isort should skip over. If you want to skip multiple "
        "files you should specify twice: --skip file1 --skip file2. Values can be "
        "file names, directory names or file paths. To skip all files in a nested path "
        "use --skip-glob.",
        dest="skip",
        action="append",
    )
    target_group.add_argument(
        "--extend-skip",
        help="Extends --skip to add additional files that isort should skip over. "
        "If you want to skip multiple "
        "files you should specify twice: --skip file1 --skip file2. Values can be "
        "file names, directory names or file paths. To skip all files in a nested path "
        "use --skip-glob.",
        dest="extend_skip",
        action="append",
    )
    target_group.add_argument(
        "--sg",
        "--skip-glob",
        help="Files that isort should skip over.",
        dest="skip_glob",
        action="append",
    )
    target_group.add_argument(
        "--extend-skip-glob",
        help="Additional files that isort should skip over (extending --skip-glob).",
        dest="extend_skip_glob",
        action="append",
    )
    target_group.add_argument(
        "--gitignore",
        "--skip-gitignore",
        action="store_true",
        dest="skip_gitignore",
        help="Treat project as a git repository and ignore files listed in .gitignore."
        "\nNOTE: This requires git to be installed and accessible from the same shell as isort.",
    )
    target_group.add_argument(
        "--ext",
        "--extension",
        "--supported-extension",
        dest="supported_extensions",
        action="append",
        help="Specifies what extensions isort can be run against.",
    )
    target_group.add_argument(
        "--blocked-extension",
        dest="blocked_extensions",
        action="append",
        help="Specifies what extensions isort can never be run against.",
    )
    target_group.add_argument(
        "--dont-follow-links",
        dest="dont_follow_links",
        action="store_true",
        help="Tells isort not to follow symlinks that are encountered when running recursively.",
    )
    target_group.add_argument(
        "--filename",
        dest="filename",
        help="Provide the filename associated with a stream.",
    )
    target_group.add_argument(
        "--allow-root",
        action="store_true",
        default=False,
        help="Tells isort not to treat / specially, allowing it to be run against the root dir.",
    )

    output_group.add_argument(
        "-a",
        "--add-import",
        dest="add_imports",
        action="append",
        help="Adds the specified import line to all files, "
        "automatically determining correct placement.",
    )
    output_group.add_argument(
        "--append",
        "--append-only",
        dest="append_only",
        action="store_true",
        help="Only adds the imports specified in --add-import if the file"
        " contains existing imports.",
    )
    output_group.add_argument(
        "--af",
        "--force-adds",
        dest="force_adds",
        action="store_true",
        help="Forces import adds even if the original file is empty.",
    )
    output_group.add_argument(
        "--rm",
        "--remove-import",
        dest="remove_imports",
        action="append",
        help="Removes the specified import from all files.",
    )
    output_group.add_argument(
        "--float-to-top",
        dest="float_to_top",
        action="store_true",
        help="Causes all non-indented imports to float to the top of the file having its imports "
        "sorted (immediately below the top of file comment).\n"
        "This can be an excellent shortcut for collecting imports every once in a while "
        "when you place them in the middle of a file to avoid context switching.\n\n"
        "*NOTE*: It currently doesn't work with cimports and introduces some extra over-head "
        "and a performance penalty.",
    )
    output_group.add_argument(
        "--dont-float-to-top",
        dest="dont_float_to_top",
        action="store_true",
        help="Forces --float-to-top setting off. See --float-to-top for more information.",
    )
    output_group.add_argument(
        "--ca",
        "--combine-as",
        dest="combine_as_imports",
        action="store_true",
        help="Combines as imports on the same line.",
    )
    output_group.add_argument(
        "--cs",
        "--combine-star",
        dest="combine_star",
        action="store_true",
        help="Ensures that if a star import is present, "
        "nothing else is imported from that namespace.",
    )
    output_group.add_argument(
        "-e",
        "--balanced",
        dest="balanced_wrapping",
        action="store_true",
        help="Balances wrapping to produce the most consistent line length possible",
    )
    output_group.add_argument(
        "--ff",
        "--from-first",
        dest="from_first",
        action="store_true",
        help="Switches the typical ordering preference, "
        "showing from imports first then straight ones.",
    )
    output_group.add_argument(
        "--fgw",
        "--force-grid-wrap",
        nargs="?",
        const=2,
        type=int,
        dest="force_grid_wrap",
        help="Force number of from imports (defaults to 2 when passed as CLI flag without value) "
        "to be grid wrapped regardless of line "
        "length. If 0 is passed in (the global default) only line length is considered.",
    )
    output_group.add_argument(
        "-i",
        "--indent",
        help='String to place for indents defaults to "    " (4 spaces).',
        dest="indent",
        type=str,
    )
    output_group.add_argument(
        "--lbi", "--lines-before-imports", dest="lines_before_imports", type=int
    )
    output_group.add_argument(
        "--lai", "--lines-after-imports", dest="lines_after_imports", type=int
    )
    output_group.add_argument(
        "--lbt", "--lines-between-types", dest="lines_between_types", type=int
    )
    output_group.add_argument(
        "--le",
        "--line-ending",
        dest="line_ending",
        help="Forces line endings to the specified value. "
        "If not set, values will be guessed per-file.",
    )
    output_group.add_argument(
        "--ls",
        "--length-sort",
        help="Sort imports by their string length.",
        dest="length_sort",
        action="store_true",
    )
    output_group.add_argument(
        "--lss",
        "--length-sort-straight",
        help="Sort straight imports by their string length. Similar to `length_sort` "
        "but applies only to straight imports and doesn't affect from imports.",
        dest="length_sort_straight",
        action="store_true",
    )
    output_group.add_argument(
        "-m",
        "--multi-line",
        dest="multi_line_output",
        choices=list(WrapModes.__members__.keys())
        + [str(mode.value) for mode in WrapModes.__members__.values()],
        type=str,
        help="Multi line output (0-grid, 1-vertical, 2-hanging, 3-vert-hanging, 4-vert-grid, "
        "5-vert-grid-grouped, 6-deprecated-alias-for-5, 7-noqa, "
        "8-vertical-hanging-indent-bracket, 9-vertical-prefix-from-module-import, "
        "10-hanging-indent-with-parentheses).",
    )
    output_group.add_argument(
        "-n",
        "--ensure-newline-before-comments",
        dest="ensure_newline_before_comments",
        action="store_true",
        help="Inserts a blank line before a comment following an import.",
    )
    inline_args_group.add_argument(
        "--nis",
        "--no-inline-sort",
        dest="no_inline_sort",
        action="store_true",
        help="Leaves `from` imports with multiple imports 'as-is' "
        "(e.g. `from foo import a, c ,b`).",
    )
    output_group.add_argument(
        "--ot",
        "--order-by-type",
        dest="order_by_type",
        action="store_true",
        help="Order imports by type, which is determined by case, in addition to alphabetically.\n"
        "\n**NOTE**: type here refers to the implied type from the import name capitalization.\n"
        ' isort does not do type introspection for the imports. These "types" are simply: '
        "CONSTANT_VARIABLE, CamelCaseClass, variable_or_function. If your project follows PEP8"
        " or a related coding standard and has many imports this is a good default, otherwise you "
        "likely will want to turn it off. From the CLI the `--dont-order-by-type` option will turn "
        "this off.",
    )
    output_group.add_argument(
        "--dt",
        "--dont-order-by-type",
        dest="dont_order_by_type",
        action="store_true",
        help="Don't order imports by type, which is determined by case, in addition to "
        "alphabetically.\n\n"
        "**NOTE**: type here refers to the implied type from the import name capitalization.\n"
        ' isort does not do type introspection for the imports. These "types" are simply: '
        "CONSTANT_VARIABLE, CamelCaseClass, variable_or_function. If your project follows PEP8"
        " or a related coding standard and has many imports this is a good default. You can turn "
        "this on from the CLI using `--order-by-type`.",
    )
    output_group.add_argument(
        "--rr",
        "--reverse-relative",
        dest="reverse_relative",
        action="store_true",
        help="Reverse order of relative imports.",
    )
    output_group.add_argument(
        "--reverse-sort",
        dest="reverse_sort",
        action="store_true",
        help="Reverses the ordering of imports.",
    )
    output_group.add_argument(
        "--sort-order",
        dest="sort_order",
        help="Specify sorting function. Can be built in (natural[default] = force numbers "
        "to be sequential, native = Python's built-in sorted function) or an installable plugin.",
    )
    inline_args_group.add_argument(
        "--sl",
        "--force-single-line-imports",
        dest="force_single_line",
        action="store_true",
        help="Forces all from imports to appear on their own line",
    )
    output_group.add_argument(
        "--nsl",
        "--single-line-exclusions",
        help="One or more modules to exclude from the single line rule.",
        dest="single_line_exclusions",
        action="append",
    )
    output_group.add_argument(
        "--tc",
        "--trailing-comma",
        dest="include_trailing_comma",
        action="store_true",
        help="Includes a trailing comma on multi line imports that include parentheses.",
    )
    output_group.add_argument(
        "--up",
        "--use-parentheses",
        dest="use_parentheses",
        action="store_true",
        help="Use parentheses for line continuation on length limit instead of slashes."
        " **NOTE**: This is separate from wrap modes, and only affects how individual lines that "
        " are too long get continued, not sections of multiple imports.",
    )
    output_group.add_argument(
        "-l",
        "-w",
        "--line-length",
        "--line-width",
        help="The max length of an import line (used for wrapping long imports).",
        dest="line_length",
        type=int,
    )
    output_group.add_argument(
        "--wl",
        "--wrap-length",
        dest="wrap_length",
        type=int,
        help="Specifies how long lines that are wrapped should be, if not set line_length is used."
        "\nNOTE: wrap_length must be LOWER than or equal to line_length.",
    )
    output_group.add_argument(
        "--case-sensitive",
        dest="case_sensitive",
        action="store_true",
        help="Tells isort to include casing when sorting module names",
    )
    output_group.add_argument(
        "--remove-redundant-aliases",
        dest="remove_redundant_aliases",
        action="store_true",
        help=(
            "Tells isort to remove redundant aliases from imports, such as `import os as os`."
            " This defaults to `False` simply because some projects use these seemingly useless "
            " aliases to signify intent and change behaviour."
        ),
    )
    output_group.add_argument(
        "--honor-noqa",
        dest="honor_noqa",
        action="store_true",
        help="Tells isort to honor noqa comments to enforce skipping those comments.",
    )
    output_group.add_argument(
        "--treat-comment-as-code",
        dest="treat_comments_as_code",
        action="append",
        help="Tells isort to treat the specified single line comment(s) as if they are code.",
    )
    output_group.add_argument(
        "--treat-all-comment-as-code",
        dest="treat_all_comments_as_code",
        action="store_true",
        help="Tells isort to treat all single line comments as if they are code.",
    )
    output_group.add_argument(
        "--formatter",
        dest="formatter",
        type=str,
        help="Specifies the name of a formatting plugin to use when producing output.",
    )
    output_group.add_argument(
        "--color",
        dest="color_output",
        action="store_true",
        help="Tells isort to use color in terminal output.",
    )
    output_group.add_argument(
        "--ext-format",
        dest="ext_format",
        help="Tells isort to format the given files according to an extensions formatting rules.",
    )
    output_group.add_argument(
        "--star-first",
        help="Forces star imports above others to avoid overriding directly imported variables.",
        dest="star_first",
        action="store_true",
    )
    output_group.add_argument(
        "--split-on-trailing-comma",
        help="Split imports list followed by a trailing comma into VERTICAL_HANGING_INDENT mode",
        dest="split_on_trailing_comma",
        action="store_true",
    )

    section_group.add_argument(
        "--sd",
        "--section-default",
        dest="default_section",
        help="Sets the default section for import options: " + str(sections.DEFAULT),
    )
    section_group.add_argument(
        "--only-sections",
        "--os",
        dest="only_sections",
        action="store_true",
        help="Causes imports to be sorted based on their sections like STDLIB, THIRDPARTY, etc. "
        "Within sections, the imports are ordered by their import style and the imports with "
        "the same style maintain their relative positions.",
    )
    section_group.add_argument(
        "--ds",
        "--no-sections",
        help="Put all imports into the same section bucket",
        dest="no_sections",
        action="store_true",
    )
    section_group.add_argument(
        "--fas",
        "--force-alphabetical-sort",
        action="store_true",
        dest="force_alphabetical_sort",
        help="Force all imports to be sorted as a single section",
    )
    section_group.add_argument(
        "--fss",
        "--force-sort-within-sections",
        action="store_true",
        dest="force_sort_within_sections",
        help="Don't sort straight-style imports (like import sys) before from-style imports "
        "(like from itertools import groupby). Instead, sort the imports by module, "
        "independent of import style.",
    )
    section_group.add_argument(
        "--hcss",
        "--honor-case-in-force-sorted-sections",
        action="store_true",
        dest="honor_case_in_force_sorted_sections",
        help="Honor `--case-sensitive` when `--force-sort-within-sections` is being used. "
        "Without this option set, `--order-by-type` decides module name ordering too.",
    )
    section_group.add_argument(
        "--srss",
        "--sort-relative-in-force-sorted-sections",
        action="store_true",
        dest="sort_relative_in_force_sorted_sections",
        help="When using `--force-sort-within-sections`, sort relative imports the same "
        "way as they are sorted when not using that setting.",
    )
    section_group.add_argument(
        "--fass",
        "--force-alphabetical-sort-within-sections",
        action="store_true",
        dest="force_alphabetical_sort_within_sections",
        help="Force all imports to be sorted alphabetically within a section",
    )
    section_group.add_argument(
        "-t",
        "--top",
        help="Force specific imports to the top of their appropriate section.",
        dest="force_to_top",
        action="append",
    )
    section_group.add_argument(
        "--combine-straight-imports",
        "--csi",
        dest="combine_straight_imports",
        action="store_true",
        help="Combines all the bare straight imports of the same section in a single line. "
        "Won't work with sections which have 'as' imports",
    )
    section_group.add_argument(
        "--nlb",
        "--no-lines-before",
        help="Sections which should not be split with previous by empty lines",
        dest="no_lines_before",
        action="append",
    )
    section_group.add_argument(
        "--src",
        "--src-path",
        dest="src_paths",
        action="append",
        help="Add an explicitly defined source path "
        "(modules within src paths have their imports automatically categorized as first_party)."
        " Glob expansion (`*` and `**`) is supported for this option.",
    )
    section_group.add_argument(
        "-b",
        "--builtin",
        dest="known_standard_library",
        action="append",
        help="Force isort to recognize a module as part of Python's standard library.",
    )
    section_group.add_argument(
        "--extra-builtin",
        dest="extra_standard_library",
        action="append",
        help="Extra modules to be included in the list of ones in Python's standard library.",
    )
    section_group.add_argument(
        "-f",
        "--future",
        dest="known_future_library",
        action="append",
        help="Force isort to recognize a module as part of Python's internal future compatibility "
        "libraries. WARNING: this overrides the behavior of __future__ handling and therefore"
        " can result in code that can't execute. If you're looking to add dependencies such "
        "as six, a better option is to create another section below --future using custom "
        "sections. See: https://github.com/PyCQA/isort#custom-sections-and-ordering and the "
        "discussion here: https://github.com/PyCQA/isort/issues/1463.",
    )
    section_group.add_argument(
        "-o",
        "--thirdparty",
        dest="known_third_party",
        action="append",
        help="Force isort to recognize a module as being part of a third party library.",
    )
    section_group.add_argument(
        "-p",
        "--project",
        dest="known_first_party",
        action="append",
        help="Force isort to recognize a module as being part of the current python project.",
    )
    section_group.add_argument(
        "--known-local-folder",
        dest="known_local_folder",
        action="append",
        help="Force isort to recognize a module as being a local folder. "
        "Generally, this is reserved for relative imports (from . import module).",
    )
    section_group.add_argument(
        "--virtual-env",
        dest="virtual_env",
        help="Virtual environment to use for determining whether a package is third-party",
    )
    section_group.add_argument(
        "--conda-env",
        dest="conda_env",
        help="Conda environment to use for determining whether a package is third-party",
    )
    section_group.add_argument(
        "--py",
        "--python-version",
        action="store",
        dest="py_version",
        choices=(*tuple(VALID_PY_TARGETS), "auto"),
        help="Tells isort to set the known standard library based on the specified Python "
        "version. Default is to assume any Python 3 version could be the target, and use a union "
        "of all stdlib modules across versions. If auto is specified, the version of the "
        "interpreter used to run isort "
        f"(currently: {sys.version_info.major}{sys.version_info.minor}) will be used.",
    )

    # deprecated options
    deprecated_group.add_argument(
        "--recursive",
        dest="deprecated_flags",
        action="append_const",
        const="--recursive",
        help=argparse.SUPPRESS,
    )
    deprecated_group.add_argument(
        "-rc", dest="deprecated_flags", action="append_const", const="-rc", help=argparse.SUPPRESS
    )
    deprecated_group.add_argument(
        "--dont-skip",
        dest="deprecated_flags",
        action="append_const",
        const="--dont-skip",
        help=argparse.SUPPRESS,
    )
    deprecated_group.add_argument(
        "-ns", dest="deprecated_flags", action="append_const", const="-ns", help=argparse.SUPPRESS
    )
    deprecated_group.add_argument(
        "--apply",
        dest="deprecated_flags",
        action="append_const",
        const="--apply",
        help=argparse.SUPPRESS,
    )
    deprecated_group.add_argument(
        "-k",
        "--keep-direct-and-as",
        dest="deprecated_flags",
        action="append_const",
        const="--keep-direct-and-as",
        help=argparse.SUPPRESS,
    )

    return parser


def parse_args(argv: Sequence[str] | None = None) -> dict[str, Any]:
    argv = sys.argv[1:] if argv is None else list(argv)
    remapped_deprecated_args = []
    for index, arg in enumerate(argv):
        if arg in DEPRECATED_SINGLE_DASH_ARGS:
            remapped_deprecated_args.append(arg)
            argv[index] = f"-{arg}"

    parser = _build_arg_parser()
    arguments = {key: value for key, value in vars(parser.parse_args(argv)).items() if value}
    if remapped_deprecated_args:
        arguments["remapped_deprecated_args"] = remapped_deprecated_args
    if "dont_order_by_type" in arguments:
        arguments["order_by_type"] = False
        del arguments["dont_order_by_type"]
    if "dont_follow_links" in arguments:
        arguments["follow_links"] = False
        del arguments["dont_follow_links"]
    if "dont_float_to_top" in arguments:
        del arguments["dont_float_to_top"]
        if arguments.get("float_to_top", False):
            sys.exit("Can't set both --float-to-top and --dont-float-to-top.")
        else:
            arguments["float_to_top"] = False
    multi_line_output = arguments.get("multi_line_output", None)
    if multi_line_output:
        if multi_line_output.isdigit():
            arguments["multi_line_output"] = WrapModes(int(multi_line_output))
        else:
            arguments["multi_line_output"] = WrapModes[multi_line_output]

    return arguments


def _preconvert(item: Any) -> str | list[Any]:
    """Preconverts objects from native types into JSONifyiable types"""
    if isinstance(item, (set, frozenset)):
        return list(item)
    if isinstance(item, WrapModes):
        return str(item.name)
    if isinstance(item, Path):
        return str(item)
    if callable(item) and hasattr(item, "__name__"):
        return str(item.__name__)
    raise TypeError(f"Unserializable object {item} of type {type(item)}")


def identify_imports_main(
    argv: Sequence[str] | None = None, stdin: TextIOWrapper | None = None
) -> None:
    parser = argparse.ArgumentParser(
        description="Get all import definitions from a given file."
        "Use `-` as the first argument to represent stdin."
    )
    parser.add_argument(
        "files", nargs="+", help="One or more Python source files that need their imports sorted."
    )
    parser.add_argument(
        "--top-only",
        action="store_true",
        default=False,
        help="Only identify imports that occur in before functions or classes.",
    )

    target_group = parser.add_argument_group("target options")
    target_group.add_argument(
        "--follow-links",
        action="store_true",
        default=False,
        help="Tells isort to follow symlinks that are encountered when running recursively.",
    )

    uniqueness = parser.add_mutually_exclusive_group()
    uniqueness.add_argument(
        "--unique",
        action="store_true",
        default=False,
        help="If true, isort will only identify unique imports.",
    )
    uniqueness.add_argument(
        "--packages",
        dest="unique",
        action="store_const",
        const=api.ImportKey.PACKAGE,
        default=False,
        help="If true, isort will only identify the unique top level modules imported.",
    )
    uniqueness.add_argument(
        "--modules",
        dest="unique",
        action="store_const",
        const=api.ImportKey.MODULE,
        default=False,
        help="If true, isort will only identify the unique modules imported.",
    )
    uniqueness.add_argument(
        "--attributes",
        dest="unique",
        action="store_const",
        const=api.ImportKey.ATTRIBUTE,
        default=False,
        help="If true, isort will only identify the unique attributes imported.",
    )

    arguments = parser.parse_args(argv)

    file_names = arguments.files
    if file_names == ["-"]:
        identified_imports = api.find_imports_in_stream(
            sys.stdin if stdin is None else stdin,
            unique=arguments.unique,
            top_only=arguments.top_only,
            follow_links=arguments.follow_links,
        )
    else:
        identified_imports = api.find_imports_in_paths(
            file_names,
            unique=arguments.unique,
            top_only=arguments.top_only,
            follow_links=arguments.follow_links,
        )

    for identified_import in identified_imports:
        if arguments.unique == api.ImportKey.PACKAGE:
            print(identified_import.module.split(".")[0])
        elif arguments.unique == api.ImportKey.MODULE:
            print(identified_import.module)
        elif arguments.unique == api.ImportKey.ATTRIBUTE:
            print(f"{identified_import.module}.{identified_import.attribute}")
        else:
            print(str(identified_import))


def main(argv: Sequence[str] | None = None, stdin: TextIOWrapper | None = None) -> None:
    arguments = parse_args(argv)
    if arguments.get("show_version"):
        print(ASCII_ART)
        return

    show_config: bool = arguments.pop("show_config", False)
    show_files: bool = arguments.pop("show_files", False)
    if show_config and show_files:
        sys.exit("Error: either specify show-config or show-files not both.")

    if "settings_path" in arguments:
        if os.path.isfile(arguments["settings_path"]):
            arguments["settings_file"] = os.path.abspath(arguments["settings_path"])
            arguments["settings_path"] = os.path.dirname(arguments["settings_file"])
        else:
            arguments["settings_path"] = os.path.abspath(arguments["settings_path"])

    if "virtual_env" in arguments:
        venv = arguments["virtual_env"]
        arguments["virtual_env"] = os.path.abspath(venv)
        if not os.path.isdir(arguments["virtual_env"]):
            warn(f"virtual_env dir does not exist: {arguments['virtual_env']}", stacklevel=2)

    file_names = arguments.pop("files", [])
    if not file_names and not show_config:
        print(QUICK_GUIDE)
        if arguments:
            sys.exit("Error: arguments passed in without any paths or content.")
        return
    if "settings_path" not in arguments:
        arguments["settings_path"] = (
            arguments.get("filename", None) or os.getcwd()
            if file_names == ["-"]
            else os.path.abspath(file_names[0] if file_names else ".")
        )
        if not os.path.isdir(arguments["settings_path"]):
            arguments["settings_path"] = os.path.dirname(arguments["settings_path"])

    config_dict = arguments.copy()
    ask_to_apply = config_dict.pop("ask_to_apply", False)
    jobs = config_dict.pop("jobs", None)
    check = config_dict.pop("check", False)
    show_diff = config_dict.pop("show_diff", False)
    write_to_stdout = config_dict.pop("write_to_stdout", False)
    deprecated_flags = config_dict.pop("deprecated_flags", False)
    remapped_deprecated_args = config_dict.pop("remapped_deprecated_args", False)
    stream_filename = config_dict.pop("filename", None)
    ext_format = config_dict.pop("ext_format", None)
    allow_root = config_dict.pop("allow_root", None)
    resolve_all_configs = config_dict.pop("resolve_all_configs", False)
    wrong_sorted_files = False
    all_attempt_broken = False
    no_valid_encodings = False

    config_trie: Trie | None = None
    if resolve_all_configs:
        config_trie = find_all_configs(config_dict.pop("config_root", "."))

    if "src_paths" in config_dict:
        config_dict["src_paths"] = {
            Path(src_path).resolve() for src_path in config_dict.get("src_paths", ())
        }

    config = Config(**config_dict)
    if show_config:
        print(json.dumps(config.__dict__, indent=4, separators=(",", ": "), default=_preconvert))
        return
    if file_names == ["-"]:
        file_path = Path(stream_filename) if stream_filename else None
        if show_files:
            sys.exit("Error: can't show files for streaming input.")

        input_stream = sys.stdin if stdin is None else stdin
        if check:
            incorrectly_sorted = not api.check_stream(
                input_stream=input_stream,
                config=config,
                show_diff=show_diff,
                file_path=file_path,
                extension=ext_format,
            )

            wrong_sorted_files = incorrectly_sorted
        else:
            try:
                api.sort_stream(
                    input_stream=input_stream,
                    output_stream=sys.stdout,
                    config=config,
                    show_diff=show_diff,
                    file_path=file_path,
                    extension=ext_format,
                    raise_on_skip=False,
                )
            except FileSkipped:
                sys.stdout.write(input_stream.read())
    elif "/" in file_names and not allow_root:
        printer = create_terminal_printer(
            color=config.color_output, error=config.format_error, success=config.format_success
        )
        printer.error("it is dangerous to operate recursively on '/'")
        printer.error("use --allow-root to override this failsafe")
        sys.exit(1)
    else:
        if stream_filename:
            printer = create_terminal_printer(
                color=config.color_output, error=config.format_error, success=config.format_success
            )
            printer.error("Filename override is intended only for stream (-) sorting.")
            sys.exit(1)
        skipped: list[str] = []
        broken: list[str] = []

        if config.filter_files:
            filtered_files = []
            for file_name in file_names:
                if config.is_skipped(Path(file_name)):
                    skipped.append(str(Path(file_name).resolve()))
                else:
                    filtered_files.append(file_name)
            file_names = filtered_files

        file_names = files.find(file_names, config, skipped, broken)
        if show_files:
            for file_name in file_names:
                print(file_name)
            return
        num_skipped = 0
        num_broken = 0
        num_invalid_encoding = 0
        if config.verbose:
            print(ASCII_ART)

        if jobs:
            import multiprocessing  # noqa: PLC0415

            executor = multiprocessing.Pool(jobs if jobs > 0 else multiprocessing.cpu_count())
            attempt_iterator = executor.imap(
                functools.partial(
                    sort_imports,
                    config=config,
                    check=check,
                    ask_to_apply=ask_to_apply,
                    show_diff=show_diff,
                    write_to_stdout=write_to_stdout,
                    extension=ext_format,
                    config_trie=config_trie,
                ),
                file_names,
            )
        else:
            # https://github.com/python/typeshed/pull/2814
            attempt_iterator = (
                sort_imports(  # type: ignore
                    file_name,
                    config=config,
                    check=check,
                    ask_to_apply=ask_to_apply,
                    show_diff=show_diff,
                    write_to_stdout=write_to_stdout,
                    extension=ext_format,
                    config_trie=config_trie,
                )
                for file_name in file_names
            )

        # If any files passed in are missing considered as error, should be removed
        is_no_attempt = True
        any_encoding_valid = False
        for sort_attempt in attempt_iterator:
            if not sort_attempt:
                continue  # pragma: no cover - shouldn't happen, satisfies type constraint
            incorrectly_sorted = sort_attempt.incorrectly_sorted
            if arguments.get("check", False) and incorrectly_sorted:
                wrong_sorted_files = True
            if sort_attempt.skipped:
                num_skipped += (
                    1  # pragma: no cover - shouldn't happen, due to skip in iter_source_code
                )

            if not sort_attempt.supported_encoding:
                num_invalid_encoding += 1
            else:
                any_encoding_valid = True

            is_no_attempt = False

        num_skipped += len(skipped)
        if num_skipped and not config.quiet:
            if config.verbose:
                for was_skipped in skipped:
                    print(
                        f"{was_skipped} was skipped as it's listed in 'skip' setting, "
                        "matches a glob in 'skip_glob' setting, or is in a .gitignore file with "
                        "--skip-gitignore enabled."
                    )
            print(f"Skipped {num_skipped} files")

        num_broken += len(broken)
        if num_broken and not config.quiet:
            if config.verbose:
                for was_broken in broken:
                    warn(
                        f"{was_broken} was broken path, make sure it exists correctly", stacklevel=2
                    )
            print(f"Broken {num_broken} paths")

        if num_broken > 0 and is_no_attempt:
            all_attempt_broken = True
        if num_invalid_encoding > 0 and not any_encoding_valid:
            no_valid_encodings = True

    if not config.quiet and (remapped_deprecated_args or deprecated_flags):
        if remapped_deprecated_args:
            warn(
                "W0502: The following deprecated single dash CLI flags were used and translated: "
                f"{', '.join(remapped_deprecated_args)}!",
                stacklevel=2,
            )
        if deprecated_flags:
            warn(
                "W0501: The following deprecated CLI flags were used and ignored: "
                f"{', '.join(deprecated_flags)}!",
                stacklevel=2,
            )
        warn(
            "W0500: Please see the 5.0.0 Upgrade guide: "
            "https://pycqa.github.io/isort/docs/upgrade_guides/5.0.0.html",
            stacklevel=2,
        )

    if wrong_sorted_files:
        sys.exit(1)

    if all_attempt_broken:
        sys.exit(1)

    if no_valid_encodings:
        printer = create_terminal_printer(
            color=config.color_output, error=config.format_error, success=config.format_success
        )
        printer.error("No valid encodings.")
        sys.exit(1)


if __name__ == "__main__":
    main()
