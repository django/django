"""Pattern-matching utility functions for Sphinx."""

from __future__ import annotations

import os.path
import re
from typing import TYPE_CHECKING, Callable

from sphinx.util.osutil import canon_path, path_stabilize

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator


def _translate_pattern(pat: str) -> str:
    """Translate a shell-style glob pattern to a regular expression.

    Adapted from the fnmatch module, but enhanced so that single stars don't
    match slashes.
    """
    i, n = 0, len(pat)
    res = ''
    while i < n:
        c = pat[i]
        i += 1
        if c == '*':
            if i < n and pat[i] == '*':
                # double star matches slashes too
                i += 1
                res = res + '.*'
            else:
                # single star doesn't match slashes
                res = res + '[^/]*'
        elif c == '?':
            # question mark doesn't match slashes too
            res = res + '[^/]'
        elif c == '[':
            j = i
            if j < n and pat[j] == '!':
                j += 1
            if j < n and pat[j] == ']':
                j += 1
            while j < n and pat[j] != ']':
                j += 1
            if j >= n:
                res = res + '\\['
            else:
                stuff = pat[i:j].replace('\\', '\\\\')
                i = j + 1
                if stuff[0] == '!':
                    # negative pattern mustn't match slashes too
                    stuff = '^/' + stuff[1:]
                elif stuff[0] == '^':
                    stuff = '\\' + stuff
                res = f'{res}[{stuff}]'
        else:
            res += re.escape(c)
    return res + '$'


def compile_matchers(
    patterns: Iterable[str],
) -> list[Callable[[str], re.Match[str] | None]]:
    return [re.compile(_translate_pattern(pat)).match for pat in patterns]


class Matcher:
    """A pattern matcher for Multiple shell-style glob patterns.

    Note: this modifies the patterns to work with copy_asset().
          For example, "**/index.rst" matches with "index.rst"
    """

    def __init__(self, exclude_patterns: Iterable[str]) -> None:
        expanded = [pat[3:] for pat in exclude_patterns if pat.startswith('**/')]
        self.patterns = compile_matchers(list(exclude_patterns) + expanded)

    def __call__(self, string: str) -> bool:
        return self.match(string)

    def match(self, string: str) -> bool:
        string = canon_path(string)
        return any(pat(string) for pat in self.patterns)


DOTFILES = Matcher(['**/.*'])


_pat_cache: dict[str, re.Pattern[str]] = {}


def patmatch(name: str, pat: str) -> re.Match[str] | None:
    """Return if name matches the regular expression (pattern)
    ``pat```. Adapted from fnmatch module."""
    if pat not in _pat_cache:
        _pat_cache[pat] = re.compile(_translate_pattern(pat))
    return _pat_cache[pat].match(name)


def patfilter(names: Iterable[str], pat: str) -> list[str]:
    """Return the subset of the list ``names`` that match
    the regular expression (pattern) ``pat``.

    Adapted from fnmatch module.
    """
    if pat not in _pat_cache:
        _pat_cache[pat] = re.compile(_translate_pattern(pat))
    match = _pat_cache[pat].match
    return list(filter(match, names))


def get_matching_files(
    dirname: str | os.PathLike[str],
    include_patterns: Iterable[str] = ("**",),
    exclude_patterns: Iterable[str] = (),
) -> Iterator[str]:
    """Get all file names in a directory, recursively.

    Filter file names by the glob-style include_patterns and exclude_patterns.
    The default values include all files ("**") and exclude nothing ("").

    Only files matching some pattern in *include_patterns* are included, and
    exclusions from *exclude_patterns* take priority over inclusions.

    """
    # dirname is a normalized absolute path.
    dirname = os.path.normpath(os.path.abspath(dirname))

    exclude_matchers = compile_matchers(exclude_patterns)
    include_matchers = compile_matchers(include_patterns)

    for root, dirs, files in os.walk(dirname, followlinks=True):
        relative_root = os.path.relpath(root, dirname)
        if relative_root == ".":
            relative_root = ""  # suppress dirname for files on the target dir

        # Filter files
        included_files = []
        for entry in sorted(files):
            entry = path_stabilize(os.path.join(relative_root, entry))
            keep = False
            for matcher in include_matchers:
                if matcher(entry):
                    keep = True
                    break  # break the inner loop

            for matcher in exclude_matchers:
                if matcher(entry):
                    keep = False
                    break  # break the inner loop

            if keep:
                included_files.append(entry)

        # Filter directories
        filtered_dirs = []
        for dir_name in sorted(dirs):
            normalised = path_stabilize(os.path.join(relative_root, dir_name))
            for matcher in exclude_matchers:
                if matcher(normalised):
                    break  # break the inner loop
            else:
                # if the loop didn't break
                filtered_dirs.append(dir_name)

        dirs[:] = filtered_dirs

        # Yield filtered files
        yield from included_files
