"""
Functions for reversing a regular expression (used in reverse URL resolving).
Used internally by Django and not intended for external use.

This is not, and is not intended to be, a complete reg-exp decompiler. It
should be good enough for a large class of URLS, however.
"""

import re

from django.utils.functional import SimpleLazyObject

# Mapping of an escape character to a representative of that class. So, e.g.,
# "\w" is replaced by "x" in a reverse URL. A value of None means to ignore
# this sequence. Any missing key is mapped to itself.
ESCAPE_MAPPINGS = {
    "A": None,
    "b": None,
    "B": None,
    "d": "0",
    "D": "x",
    "s": " ",
    "S": "x",
    "w": "x",
    "W": "!",
    "Z": None,
}


class Choice(list):
    """Represent multiple possibilities at this point in a pattern string."""


class Group(list):
    """Represent a capturing group in the pattern string."""


class NonCapture(list):
    """Represent a non-capturing group in the pattern string."""


def normalize(pattern):
    r"""
    Given a reg-exp pattern, normalize it to an iterable of forms that
    suffice for reverse matching. This does the following:

    (1) For any repeating sections, keeps the minimum number of occurrences
        permitted (this means zero for optional groups).
    (2) If an optional group includes parameters, include one occurrence of
        that group (along with the zero occurrence case from step (1)).
    (3) Select the first (essentially an arbitrary) element from any character
        class. Select an arbitrary character for any unordered class (e.g. '.'
        or '\w') in the pattern.
    (4) Ignore look-ahead and look-behind assertions.
    (5) Raise an error on any disjunctive ('|') constructs.

    Django's URLs for forward resolving are either all positional arguments or
    all keyword arguments. That is assumed here, as well. Although reverse
    resolving can be done using positional args when keyword args are
    specified, the two cannot be mixed in the same reverse() call.
    """
    # Do a linear scan to work out the special features of this pattern. The
    # idea is that we scan once here and collect all the information we need to
    # make future decisions.
    result = []
    non_capturing_groups = []
    consume_next = True
    pattern_iter = next_char(iter(pattern))
    num_args = 0

    # A "while" loop is used here because later on we need to be able to peek
    # at the next character and possibly go around without consuming another
    # one at the top of the loop.
    try:
        ch, escaped = next(pattern_iter)
    except StopIteration:
        return [("", [])]

    try:
        while True:
            if escaped:
                result.append(ch)
            elif ch == ".":
                # Replace "any character" with an arbitrary representative.
                result.append(".")
            elif ch == "|":
                # FIXME: One day we'll should do this, but not in 1.0.
                raise NotImplementedError("Awaiting Implementation")
            elif ch == "^":
                pass
            elif ch == "$":
                break
            elif ch == ")":
                # This can only be the end of a non-capturing group, since all
                # other unescaped parentheses are handled by the grouping
                # section later (and the full group is handled there).
                #
                # We regroup everything inside the capturing group so that it
                # can be quantified, if necessary.
                start = non_capturing_groups.pop()
                inner = NonCapture(result[start:])
                result = result[:start] + [inner]
            elif ch == "[":
                # Replace ranges with the first character in the range.
                ch, escaped = next(pattern_iter)
                result.append(ch)
                ch, escaped = next(pattern_iter)
                while escaped or ch != "]":
                    ch, escaped = next(pattern_iter)
            elif ch == "(":
                # Some kind of group.
                ch, escaped = next(pattern_iter)
                if ch != "?" or escaped:
                    # A positional group
                    name = "_%d" % num_args
                    num_args += 1
                    result.append(Group((("%%(%s)s" % name), name)))
                    walk_to_end(ch, pattern_iter)
                else:
                    ch, escaped = next(pattern_iter)
                    if ch in "!=<":
                        # All of these are ignorable. Walk to the end of the
                        # group.
                        walk_to_end(ch, pattern_iter)
                    elif ch == ":":
                        # Non-capturing group
                        non_capturing_groups.append(len(result))
                    elif ch != "P":
                        # Anything else, other than a named group, is something
                        # we cannot reverse.
                        raise ValueError("Non-reversible reg-exp portion: '(?%s'" % ch)
                    else:
                        ch, escaped = next(pattern_iter)
                        if ch not in ("<", "="):
                            raise ValueError(
                                "Non-reversible reg-exp portion: '(?P%s'" % ch
                            )
                        # We are in a named capturing group. Extra the name and
                        # then skip to the end.
                        if ch == "<":
                            terminal_char = ">"
                        # We are in a named backreference.
                        else:
                            terminal_char = ")"
                        name = []
                        ch, escaped = next(pattern_iter)
                        while ch != terminal_char:
                            name.append(ch)
                            ch, escaped = next(pattern_iter)
                        param = "".join(name)
                        # Named backreferences have already consumed the
                        # parenthesis.
                        if terminal_char != ")":
                            result.append(Group((("%%(%s)s" % param), param)))
                            walk_to_end(ch, pattern_iter)
                        else:
                            result.append(Group((("%%(%s)s" % param), None)))
            elif ch in "*?+{":
                # Quantifiers affect the previous item in the result list.
                count, ch = get_quantifier(ch, pattern_iter)
                if ch:
                    # We had to look ahead, but it wasn't need to compute the
                    # quantifier, so use this character next time around the
                    # main loop.
                    consume_next = False

                if count == 0:
                    if contains(result[-1], Group):
                        # If we are quantifying a capturing group (or
                        # something containing such a group) and the minimum is
                        # zero, we must also handle the case of one occurrence
                        # being present. All the quantifiers (except {0,0},
                        # which we conveniently ignore) that have a 0 minimum
                        # also allow a single occurrence.
                        result[-1] = Choice([None, result[-1]])
                    else:
                        result.pop()
                elif count > 1:
                    result.extend([result[-1]] * (count - 1))
            else:
                # Anything else is a literal.
                result.append(ch)

            if consume_next:
                ch, escaped = next(pattern_iter)
            consume_next = True
    except StopIteration:
        pass
    except NotImplementedError:
        # A case of using the disjunctive form. No results for you!
        return [("", [])]

    return list(zip(*flatten_result(result)))


def next_char(input_iter):
    r"""
    An iterator that yields the next character from "pattern_iter", respecting
    escape sequences. An escaped character is replaced by a representative of
    its class (e.g. \w -> "x"). If the escaped character is one that is
    skipped, it is not returned (the next character is returned instead).

    Yield the next character, along with a boolean indicating whether it is a
    raw (unescaped) character or not.
    """
    for ch in input_iter:
        if ch != "\\":
            yield ch, False
            continue
        ch = next(input_iter)
        representative = ESCAPE_MAPPINGS.get(ch, ch)
        if representative is None:
            continue
        yield representative, True


def walk_to_end(ch, input_iter):
    """
    The iterator is currently inside a capturing group. Walk to the close of
    this group, skipping over any nested groups and handling escaped
    parentheses correctly.
    """
    if ch == "(":
        nesting = 1
    else:
        nesting = 0
    for ch, escaped in input_iter:
        if escaped:
            continue
        elif ch == "(":
            nesting += 1
        elif ch == ")":
            if not nesting:
                return
            nesting -= 1


def get_quantifier(ch, input_iter):
    """
    Parse a quantifier from the input, where "ch" is the first character in the
    quantifier.

    Return the minimum number of occurrences permitted by the quantifier and
    either None or the next character from the input_iter if the next character
    is not part of the quantifier.
    """
    if ch in "*?+":
        try:
            ch2, escaped = next(input_iter)
        except StopIteration:
            ch2 = None
        if ch2 == "?":
            ch2 = None
        if ch == "+":
            return 1, ch2
        return 0, ch2

    quant = []
    while ch != "}":
        ch, escaped = next(input_iter)
        quant.append(ch)
    quant = quant[:-1]
    values = "".join(quant).split(",")

    # Consume the trailing '?', if necessary.
    try:
        ch, escaped = next(input_iter)
    except StopIteration:
        ch = None
    if ch == "?":
        ch = None
    return int(values[0]), ch


def contains(source, inst):
    """
    Return True if the "source" contains an instance of "inst". False,
    otherwise.
    """
    if isinstance(source, inst):
        return True
    if isinstance(source, NonCapture):
        for elt in source:
            if contains(elt, inst):
                return True
    return False


def flatten_result(source):
    """
    Turn the given source sequence into a list of reg-exp possibilities and
    their arguments. Return a list of strings and a list of argument lists.
    Each of the two lists will be of the same length.
    """
    if source is None:
        return [""], [[]]
    if isinstance(source, Group):
        if source[1] is None:
            params = []
        else:
            params = [source[1]]
        return [source[0]], [params]
    result = [""]
    result_args = [[]]
    pos = last = 0
    for pos, elt in enumerate(source):
        if isinstance(elt, str):
            continue
        piece = "".join(source[last:pos])
        if isinstance(elt, Group):
            piece += elt[0]
            param = elt[1]
        else:
            param = None
        last = pos + 1
        for i in range(len(result)):
            result[i] += piece
            if param:
                result_args[i].append(param)
        if isinstance(elt, (Choice, NonCapture)):
            if isinstance(elt, NonCapture):
                elt = [elt]
            inner_result, inner_args = [], []
            for item in elt:
                res, args = flatten_result(item)
                inner_result.extend(res)
                inner_args.extend(args)
            new_result = []
            new_args = []
            for item, args in zip(result, result_args):
                for i_item, i_args in zip(inner_result, inner_args):
                    new_result.append(item + i_item)
                    new_args.append(args[:] + i_args)
            result = new_result
            result_args = new_args
    if pos >= last:
        piece = "".join(source[last:])
        for i in range(len(result)):
            result[i] += piece
    return result, result_args


def _lazy_re_compile(regex, flags=0):
    """Lazily compile a regex with flags."""

    def _compile():
        # Compile the regex if it was not passed pre-compiled.
        if isinstance(regex, (str, bytes)):
            return re.compile(regex, flags)
        else:
            assert not flags, "flags must be empty if regex is passed pre-compiled"
            return regex

    return SimpleLazyObject(_compile)
