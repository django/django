"Misc. utility functions/classes for admin documentation generator."

import functools
import re
from email.errors import HeaderParseError
from email.parser import HeaderParser
from inspect import cleandoc

from asgiref.local import Local

from django.urls import reverse
from django.urls.resolvers import URLPattern
from django.utils.regex_helper import _lazy_re_compile
from django.utils.safestring import mark_safe

try:
    import docutils.core
    import docutils.nodes
    import docutils.parsers.rst.roles
except ImportError:
    docutils_is_available = False
else:
    docutils_is_available = True


def get_view_name(view_func):
    if hasattr(view_func, "view_class"):
        klass = view_func.view_class
        return f"{klass.__module__}.{klass.__qualname__}"
    mod_name = view_func.__module__
    view_name = getattr(view_func, "__qualname__", view_func.__class__.__name__)
    return mod_name + "." + view_name


def parse_docstring(docstring):
    """
    Parse out the parts of a docstring.  Return (title, body, metadata).
    """
    if not docstring:
        return "", "", {}
    docstring = cleandoc(docstring)
    parts = re.split(r"\n{2,}", docstring)
    title = parts[0]
    if len(parts) == 1:
        body = ""
        metadata = {}
    else:
        parser = HeaderParser()
        try:
            metadata = parser.parsestr(parts[-1])
        except HeaderParseError:
            metadata = {}
            body = "\n\n".join(parts[1:])
        else:
            metadata = dict(metadata.items())
            if metadata:
                body = "\n\n".join(parts[1:-1])
            else:
                body = "\n\n".join(parts[1:])
    return title, body, metadata


def parse_rst(text, default_reference_context, thing_being_parsed=None):
    """
    Convert the string from reST to an XHTML fragment.
    """
    overrides = {
        "doctitle_xform": True,
        "initial_header_level": 3,
        "default_reference_context": default_reference_context,
        "link_base": reverse("django-admindocs-docroot").rstrip("/"),
        "raw_enabled": False,
        "file_insertion_enabled": False,
    }
    thing_being_parsed = thing_being_parsed and "<%s>" % thing_being_parsed
    # Wrap ``text`` in some reST that sets the default role to ``cmsreference``,
    # then restores it.
    source = """
.. default-role:: cmsreference

%s

.. default-role::
"""
    parts = docutils.core.publish_parts(
        source % text,
        source_path=thing_being_parsed,
        destination_path=None,
        writer_name="html",
        settings_overrides=overrides,
    )
    return mark_safe(parts["fragment"])


#
# reST roles
#
ROLES = {
    "model": "%s/models/%s/",
    "view": "%s/views/%s/",
    "template": "%s/templates/%s/",
    "filter": "%s/filters/#%s",
    "tag": "%s/tags/#%s",
}


def create_reference_role(rolename, urlbase):
    def _role(name, rawtext, text, lineno, inliner, options=None, content=None):
        if options is None:
            options = {}
        node = docutils.nodes.reference(
            rawtext,
            text,
            refuri=(
                urlbase
                % (
                    inliner.document.settings.link_base,
                    text.lower(),
                )
            ),
            **options,
        )
        return [node], []

    docutils.parsers.rst.roles.register_canonical_role(rolename, _role)


def default_reference_role(
    name, rawtext, text, lineno, inliner, options=None, content=None
):
    if options is None:
        options = {}
    context = inliner.document.settings.default_reference_context
    node = docutils.nodes.reference(
        rawtext,
        text,
        refuri=(
            ROLES[context]
            % (
                inliner.document.settings.link_base,
                text.lower(),
            )
        ),
        **options,
    )
    return [node], []


if docutils_is_available:
    docutils.parsers.rst.roles.register_canonical_role(
        "cmsreference", default_reference_role
    )

    for name, urlbase in ROLES.items():
        create_reference_role(name, urlbase)

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


# Callback strings are cached in a dictionary for every urlconf.
# The active calback_strs are stored by thread id to make them thread local.
_callback_strs = set()
_active = Local()
_active.local_value = _callback_strs


def _is_callback(name, urlresolver=None):
    if not hasattr(_active, "local_value"):
        _active.local_value = _callback_strs
    if urlresolver and not urlresolver._populated:
        register_callback(urlresolver, _active.local_value)
    return name in _active.local_value


@functools.lru_cache(maxsize=None)
def lookup_str(urlpattern):
    """
    A string that identifies the view (e.g. 'path.to.view_function' or
    'path.to.ClassBasedView').
    """
    callback = urlpattern.callback
    if isinstance(callback, functools.partial):
        callback = callback.func
    if hasattr(callback, "view_class"):
        callback = callback.view_class
    elif not hasattr(callback, "__name__"):
        return callback.__module__ + "." + callback.__class__.__name__
    return callback.__module__ + "." + callback.__qualname__


def register_callback(urlresolver, thread):
    for url_pattern in reversed(urlresolver.url_patterns):
        if isinstance(url_pattern, URLPattern):
            thread.add(lookup_str(url_pattern))
        else:  # url_pattern is a URLResolver.
            _active.url_pattern_value = _callback_strs
            register_callback(url_pattern, _active.url_pattern_value)
            thread.update(_active.url_pattern_value)
    urlresolver._populated = True
