"""
Functions for reversing a regular expression (used in reverse URL resolving).

This is not, and is not intended to be, a complete reg-exp decompiler. It
should be good enough for almost all sane URLs.
"""

import re
from bisect import bisect

GROUP_CLASS = re.compile(r'''\((?:
        (?P<positional>[^?])|       # Unnamed (positional) capturing group.
        \?(?:
            P<(?P<named>[\w]+)>(?P<contents>.*)|    # Named capturing group.
            P=(?P<repeat>.+)|       # Repeat of a previous named group.
            (?P<grouping>:)|        # Non-capturing grouping parens.
            (?P<comment>\#)|        # Comment group
            (?P<illegal>.)          # Anything else (which will be an error)
        )
    ).*\)''', re.VERBOSE)

def normalize(pattern):
    """
    Given a reg-exp pattern, normalizes it to a list of forms that suffice for
    reverse matching. This does the following:

    (1) For any repeating sections, keeps the minimum number of occurrences
    permitted (this means zero for optional groups).
    (2) If an optional group includes parameters, include one occurrence of
    that group (along with the zero occurrence case from step (1)).
    (3) Select the first (essentially an arbitrary) element from any character
    class. Select an arbitrary character for any unordered class (e.g. '.' or
    '\w') in the pattern.
    (4) Take the first alternative in any '|' division, unless other
    alternatives would involve different parameters.
    (5) Ignore comments. Error on all other non-capturing (?...) forms (e.g.
    look-ahead and look-behind matches).

    Returns a list of tuples, each tuple containing (a) a pattern, (b) the
    number of parameters, (c) the names of the parameters. Any unnamed
    parameters are called '_0', '_1', etc.
    """
    # Do a linear scan to work out the special features of this pattern. The
    # idea is that we scan once here and collect all the information we need to
    # make future decisions.
    groups = []             # (start, end)
    quantifiers = []        # start pos
    ranges = []             # (start, end)
    eols = []               # pos
    disjunctions = []       # pos
    unclosed_groups = []
    unclosed_ranges = []
    escaped = False
    quantify = False
    in_range = False
    for pos, c in enumerate(pattern):
        if in_range and c != ']' or (c == ']' and
                unclosed_ranges[-1] == pos - 1):
            continue
        elif c == '[':
            unclosed_ranges.append(pos)
        elif c == ']':
            ranges.append((unclosed_ranges.pop(), pos + 1))
            in_range = False
        elif c == '.':
            # Treat this as a one-character long range:
            ranges.append((pos, pos + 1))
        elif escaped or c == '\\':
            escaped = not escaped
        elif c == '(':
            unclosed_groups.append(pos)
        elif c == ')':
            groups.append((unclosed_groups.pop(), pos + 1))
        elif quantify and c == '?':
            quantify = False
        elif c in '?*+{':
            quantifiers.append(pos)
            quantify = True
        elif c == '$':
            eols.append(pos)
        elif c == '|':
            disjunctions.append(pos)

    # Now classify each of the parenthetical groups to work out which ones take
    # parameters. Only the outer-most of a set of nested capturing groups is
    # important.
    groups.sort()
    params = []
    comments = []
    last_end = 0
    for start, end in groups:
        if start < last_end:
            # Skip over inner nested capturing groups.
            continue
        m = GROUP_CLASS.match(pattern, start)
        if m.group('positional'):
            params.append((start, end, '_%d' % len(params), start + 1))
        elif m.group('named'):
            params.append((start, end, m.group('named'), m.start('contents')))
        elif m.group('repeat'):
            params.append((start, end, m.group('repeat'), start + 1))
        elif m.group('illegal'):
            raise ValueError('The pattern construct %r is not valid here.'
                    % pattern[start:end])
        elif m.group('comment'):
            comments.extend([start, end])
        else:
            # This is a non-capturing set, so nesting prohibitions don't apply
            # to any inner groups.
            continue
        last_end = end

    # XXX: Got to here!
    results = []
    end = groups[0][0]
    # The first bit, before the first group starts.
    if end == 0:
        # FIXME: don't want to handle this case just yet.
        raise Exception

    quant_end = bisect(quantifiers, end)
    range_end = bisect(ranges, end)
    dis_end = bisect(disjunctions, end)
