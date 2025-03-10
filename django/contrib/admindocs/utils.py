"Misc. utility functions/classes for admin documentation generator."

import re
from email.errors import HeaderParseError
from email.parser import HeaderParser
from inspect import cleandoc

from django.urls import reverse
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

explicit_title_re = re.compile(r"^(.+?)\s*(?<!\x00)<([^<]*?)>$", re.DOTALL)


def split_explicit_title(text):
    """
    Split role content into title and target, if given.

    From sphinx.util.nodes.split_explicit_title
    See https://github.com/sphinx-doc/sphinx/blob/230ccf2/sphinx/util/nodes.py#L389
    """
    match = explicit_title_re.match(text)
    if match:
        return True, match.group(1), match.group(2)
    return False, text, text


def create_reference_role(rolename, urlbase):
    # Views and template names are case-sensitive.
    is_case_sensitive = rolename in ["template", "view"]

    def _role(name, rawtext, text, lineno, inliner, options=None, content=None):
        if options is None:
            options = {}
        _, title, target = split_explicit_title(text)
        node = docutils.nodes.reference(
            rawtext,
            title,
            refuri=(
                urlbase
                % (
                    inliner.document.settings.link_base,
                    target if is_case_sensitive else target.lower(),
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


def strip_p_tags(value):
    return mark_safe(value.replace("<p>", "").replace("</p>", ""))
