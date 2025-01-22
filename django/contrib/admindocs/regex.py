import re

from utils.regex_helper import _lazy_re_compile

# Match the beginning of a named, unnamed, or non-capturing groups.
named_group_matcher = _lazy_re_compile(r"\(\?P(<\w+>)")
unnamed_group_matcher = _lazy_re_compile(r"\(")
non_capturing_group_matcher = _lazy_re_compile(r"\(\?\:")


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
        for start, end, match in _find_groups(pattern, named_group_matcher)
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
    for start, end, _ in _find_groups(pattern, unnamed_group_matcher):
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
    group_start_end_indices = _find_groups(pattern, non_capturing_group_matcher)
    final_pattern, prev_end = "", None
    for start, end, _ in group_start_end_indices:
        final_pattern += pattern[prev_end:start]
        prev_end = end
    return final_pattern + pattern[prev_end:]


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
    if not pattern.startswith("/"):
        pattern = "/" + pattern
    return pattern
