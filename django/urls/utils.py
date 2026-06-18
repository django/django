import functools
import re
from importlib import import_module

from django.core.exceptions import ViewDoesNotExist
from django.utils.module_loading import module_has_submodule
from django.utils.regex_helper import _lazy_re_compile
from django.utils.translation import gettext as _


@functools.cache
def get_callable(lookup_view):
    """
    Return a callable corresponding to lookup_view.
    * If lookup_view is already a callable, return it.
    * If lookup_view is a string import path that can be resolved to a
      callable, import that callable and return it, otherwise raise an
      exception (ImportError or ViewDoesNotExist).
    """
    if callable(lookup_view):
        return lookup_view

    if not isinstance(lookup_view, str):
        raise ViewDoesNotExist(
            "'%s' is not a callable or a dot-notation path" % lookup_view
        )

    mod_name, func_name = get_mod_func(lookup_view)
    if not func_name:  # No '.' in lookup_view
        raise ImportError(
            "Could not import '%s'. The path must be fully qualified." % lookup_view
        )

    try:
        mod = import_module(mod_name)
    except ImportError:
        parentmod, submod = get_mod_func(mod_name)
        if submod and not module_has_submodule(import_module(parentmod), submod):
            raise ViewDoesNotExist(
                "Could not import '%s'. Parent module %s does not exist."
                % (lookup_view, mod_name)
            )
        else:
            raise
    else:
        try:
            view_func = getattr(mod, func_name)
        except AttributeError:
            raise ViewDoesNotExist(
                "Could not import '%s'. View does not exist in module %s."
                % (lookup_view, mod_name)
            )
        else:
            if not callable(view_func):
                raise ViewDoesNotExist(
                    "Could not import '%s.%s'. View is not callable."
                    % (mod_name, func_name)
                )
            return view_func


def get_mod_func(callback):
    # Convert 'django.views.news.stories.story_detail' to
    # ['django.views.news.stories', 'story_detail']
    try:
        dot = callback.rindex(".")
    except ValueError:
        return callback, ""
    return callback[:dot], callback[dot + 1 :]


# Match the beginning of a named, unnamed, or non-capturing groups.
_NAMED_GROUP_MATCHER = _lazy_re_compile(r"\(\?P(<\w+>)")
_UNNAMED_GROUP_MATCHER = _lazy_re_compile(r"\(")
_NON_CAPTURING_GROUP_MATCHER = _lazy_re_compile(r"\(\?\:")
_LITERAL_ESCAPE_RE = _lazy_re_compile(r"\\([./()_-])")


def replace_metacharacters(pattern):
    """Remove unescaped metacharacters from the pattern."""
    return re.sub(
        r"((?:^|(?<!\\))(?:\\\\)*)(\\?)([?*+^$]|\\[bBAZ])",
        lambda m: m[1] + m[3] if m[2] else m[1],
        pattern,
    )


def _get_group_start_end(start, end, pattern):
    # Handle nested parentheses, e.g. '^(?P<a>(x|y))/b' or '^b/((x|y)\w+)$'.
    unmatched_open_brackets, prev_char = 1, None
    for idx, val in enumerate(pattern[end:]):
        # Check for unescaped `(` and `)`. They mark the start and end of a
        # nested group.
        if val == "(" and prev_char != "\\":
            unmatched_open_brackets += 1
        elif val == ")" and prev_char != "\\":
            unmatched_open_brackets -= 1
        prev_char = val
        # If brackets are balanced, the end of the string for the current named
        # capture group pattern has been reached.
        if unmatched_open_brackets == 0:
            return start, end + idx + 1


def _find_groups(pattern, group_matcher):
    prev_end = None
    for match in group_matcher.finditer(pattern):
        if indices := _get_group_start_end(match.start(0), match.end(0), pattern):
            start, end = indices
            if prev_end and start > prev_end or not prev_end:
                yield start, end, match
            prev_end = end


def replace_named_groups(pattern):
    r"""
    Find named groups in `pattern` and replace them with the group name. E.g.,
    1. ^(?P<a>\w+)/b/(\w+)$ ==> ^<a>/b/(\w+)$
    2. ^(?P<a>\w+)/b/(?P<c>\w+)/$ ==> ^<a>/b/<c>/$
    3. ^(?P<a>\w+)/b/(\w+) ==> ^<a>/b/(\w+)
    4. ^(?P<a>\w+)/b/(?P<c>\w+) ==> ^<a>/b/<c>
    """
    group_pattern_and_name = [
        (pattern[start:end], match[1])
        for start, end, match in _find_groups(pattern, _NAMED_GROUP_MATCHER)
    ]
    for group_pattern, group_name in group_pattern_and_name:
        pattern = pattern.replace(group_pattern, group_name)
    return pattern


def replace_unnamed_groups(pattern):
    r"""
    Find unnamed groups in `pattern` and replace them with '<var>'. E.g.,
    1. ^(?P<a>\w+)/b/(\w+)$ ==> ^(?P<a>\w+)/b/<var>$
    2. ^(?P<a>\w+)/b/((x|y)\w+)$ ==> ^(?P<a>\w+)/b/<var>$
    3. ^(?P<a>\w+)/b/(\w+) ==> ^(?P<a>\w+)/b/<var>
    4. ^(?P<a>\w+)/b/((x|y)\w+) ==> ^(?P<a>\w+)/b/<var>
    """
    final_pattern, prev_end = "", None
    for start, end, _ignored in _find_groups(pattern, _UNNAMED_GROUP_MATCHER):
        if prev_end:
            final_pattern += pattern[prev_end:start]
        final_pattern += pattern[:start] + "<var>"
        prev_end = end
    return final_pattern + pattern[prev_end:]


def remove_non_capturing_groups(pattern):
    r"""
    Find non-capturing groups in the given `pattern` and remove them, e.g.
    1. (?P<a>\w+)/b/(?:\w+)c(?:\w+) => (?P<a>\\w+)/b/c
    2. ^(?:\w+(?:\w+))a => ^a
    3. ^a(?:\w+)/b(?:\w+) => ^a/b
    """
    group_start_end_indices = _find_groups(pattern, _NON_CAPTURING_GROUP_MATCHER)
    final_pattern, prev_end = "", None
    for start, end, _ignored in group_start_end_indices:
        final_pattern += pattern[prev_end:start]
        prev_end = end
    return final_pattern + pattern[prev_end:]


def unescape_literals(pattern):
    return _LITERAL_ESCAPE_RE.sub(r"\1", pattern)


def extract_views_from_urlpatterns(urlpatterns, base="", namespace=None):
    """
    Return a list of views from a list of urlpatterns.

    Each object in the returned list is a 4-tuple:
    (view_func, regex, namespace, name)
    """
    views = []
    for p in urlpatterns:
        if hasattr(p, "url_patterns"):
            try:
                patterns = p.url_patterns
            except ImportError:
                continue
            views.extend(
                extract_views_from_urlpatterns(
                    patterns,
                    base + str(p.pattern),
                    (namespace or []) + (p.namespace and [p.namespace] or []),
                )
            )
        elif hasattr(p, "callback"):
            try:
                views.append((p.callback, base + str(p.pattern), namespace, p.name))
            except ViewDoesNotExist:
                continue
        else:
            raise TypeError(_("%s does not appear to be a urlpattern object") % p)
    return views


def simplify_regex(pattern):
    r"""
    Clean up urlpattern regexes into something more readable by humans. For
    example, turn "^(?P<sport_slug>\w+)/athletes/(?P<athlete_slug>\w+)/$"
    into "/<sport_slug>/athletes/<athlete_slug>/".
    """
    pattern = remove_non_capturing_groups(pattern)
    pattern = replace_named_groups(pattern)
    pattern = replace_unnamed_groups(pattern)
    pattern = replace_metacharacters(pattern)
    pattern = unescape_literals(pattern)
    if not pattern.startswith("/"):
        pattern = "/" + pattern
    return pattern
