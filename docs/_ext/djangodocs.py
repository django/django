"""
Sphinx plugins for Django documentation.
"""

import re

from docutils import nodes
from docutils.statemachine import ViewList
from sphinx import addnodes
from sphinx.directives.code import CodeBlock
from sphinx.domains import changeset
from sphinx.domains.std import Cmdoption
from sphinx.locale import _
from sphinx.util import logging
from sphinx.writers.html import HTMLTranslator

logger = logging.getLogger(__name__)
# RE for option descriptions without a '--' prefix
simple_option_desc_re = re.compile(r"([-_a-zA-Z0-9]+)(\s*.*?)(?=,\s+(?:/|-|--)|$)")

# Refer to "Django N.M" rather than "version N.M".
django_changeset_versionlabels = {
    "deprecated": _("Deprecated since Django %s"),
    "versionadded": _("New in Django %s"),
    "versionchanged": _("Changed in Django %s"),
    "versionremoved": _("Removed in Django %s"),
}


def setup(app):
    app.add_crossref_type(
        directivename="setting",
        rolename="setting",
        indextemplate="pair: %s; setting",
    )
    app.add_crossref_type(
        directivename="templatetag",
        rolename="ttag",
        indextemplate="pair: %s; template tag",
    )
    app.add_crossref_type(
        directivename="templatefilter",
        rolename="tfilter",
        indextemplate="pair: %s; template filter",
    )
    app.add_crossref_type(
        directivename="fieldlookup",
        rolename="lookup",
        indextemplate="pair: %s; field lookup type",
    )
    app.add_object_type(
        directivename="django-admin",
        rolename="djadmin",
        indextemplate="pair: %s; django-admin command",
        parse_node=parse_django_admin_node,
    )
    app.add_directive("django-admin-option", Cmdoption)

    app.add_config_value("django_next_version", "0.0", True)
    changeset_directives = set(changeset.versionlabels)
    if hasattr(changeset, "name_aliases"):
        # Sphinx 9.0+ also allows "version-added", "version-changed", etc.
        changeset_directives.update(changeset.name_aliases)
    for directive in changeset_directives:
        app.add_directive(directive, DjangoVersionChange, override=True)
    # Patch Sphinx versionlabels to refer to "Django".
    if set(changeset.versionlabels) != set(django_changeset_versionlabels):
        raise RuntimeError(
            "djangodocs extension needs to be updated: "
            "sphinx.domains.changeset.versionlabels has changed."
        )
    changeset.versionlabels.update(django_changeset_versionlabels)

    app.connect("builder-inited", set_django_html_translator)

    app.add_node(
        ConsoleNode,
        html=(visit_console_html, None),
        latex=(visit_console_dummy, depart_console_dummy),
        man=(visit_console_dummy, depart_console_dummy),
        text=(visit_console_dummy, depart_console_dummy),
        texinfo=(visit_console_dummy, depart_console_dummy),
    )
    app.add_directive("console", ConsoleDirective)
    app.add_role("default-role-error", default_role_error)
    return {"parallel_read_safe": True}


def set_django_html_translator(app):
    if app.builder.format == "html":
        app.set_translator(app.builder.name, DjangoHTMLTranslator, override=True)


class DjangoVersionChange(changeset.VersionChange):
    def run(self):
        if self.arguments[0] == self.env.config.django_next_version:
            self.arguments[0] = _("development version")
        return super().run()


class DjangoHTMLTranslator(HTMLTranslator):
    """
    Django-specific reST to HTML tweaks.
    """

    # Give each section a unique ID -- nice for custom CSS hooks
    def visit_section(self, node):
        old_ids = node.get("ids", [])
        node["ids"] = ["s-" + i for i in old_ids]
        node["ids"].extend(old_ids)
        super().visit_section(node)
        node["ids"] = old_ids


def parse_django_admin_node(env, sig, signode):
    command = sig.split(" ")[0]
    env.ref_context["std:program"] = command
    title = "django-admin %s" % sig
    signode += addnodes.desc_name(title, title)
    return command


class ConsoleNode(nodes.literal_block):
    """
    Custom node to override the visit/depart event handlers at registration
    time. Wrap a literal_block object and defer to it.
    """

    tagname = "ConsoleNode"

    def __init__(self, litblk_obj):
        self.wrapped = litblk_obj

    def __getattr__(self, attr):
        if attr == "wrapped":
            return self.__dict__.wrapped
        return getattr(self.wrapped, attr)


def visit_console_dummy(self, node):
    """Defer to the corresponding parent's handler."""
    self.visit_literal_block(node)


def depart_console_dummy(self, node):
    """Defer to the corresponding parent's handler."""
    self.depart_literal_block(node)


def visit_console_html(self, node):
    """Generate HTML for the console directive."""
    # The epub builder uses the HTML format but produces XHTML for e-readers,
    # where the CSS-driven tabs neither work nor validate as XML, so fall back
    # to a plain literal block there (as the non-HTML formats already do).
    if (
        self.builder.format == "html"
        and self.builder.name != "epub"
        and node["win_console_text"]
    ):
        uid = node["uid"]
        self.body.append(f"""\
<div class="console-block" id="console-block-{uid}">
<input class="c-tab-unix" id="c-tab-{uid}-unix" type="radio" name="console-{uid}" \
checked>
<label for="c-tab-{uid}-unix"><span>Unix/macOS</span></label>
<input class="c-tab-win" id="c-tab-{uid}-win" type="radio" name="console-{uid}">
<label for="c-tab-{uid}-win"><span>Windows</span></label>
<section class="c-content-unix" id="c-content-{uid}-unix">\n""")
        try:
            self.visit_literal_block(node)
        except nodes.SkipNode:
            pass
        self.body.append("</section>\n")

        self.body.append(
            '<section class="c-content-win" id="c-content-%(id)s-win">\n' % {"id": uid}
        )
        win_text = node["win_console_text"]
        win_node = nodes.literal_block(win_text, win_text)
        win_node.update_all_atts(node)
        win_node["language"] = "doscon"
        try:
            self.visit_literal_block(win_node)
        except nodes.SkipNode:
            pass
        self.body.append("</section>\n")
        self.body.append("</div>\n")
        raise nodes.SkipNode
    else:
        self.visit_literal_block(node)


class ConsoleDirective(CodeBlock):
    """
    A reStructuredText directive which renders a two-tab code block in which
    the second tab shows a Windows command line equivalent of the usual
    Unix-oriented examples.
    """

    required_arguments = 0
    # The 'doscon' Pygments formatter needs a prompt like this. '>' alone
    # won't do it because then it simply paints the whole command line as a
    # gray comment with no highlighting at all.
    WIN_PROMPT = r"...\> "

    def run(self):
        def args_to_win(cmdline):
            changed = False
            out = []
            for token in cmdline.split():
                if token[:2] == "./":
                    token = token[2:]
                    changed = True
                elif token[:2] == "~/":
                    token = "%HOMEPATH%\\" + token[2:]
                    changed = True
                elif token == "make":
                    token = "make.bat"
                    changed = True
                if "://" not in token and "git" not in cmdline:
                    out.append(token.replace("/", "\\"))
                    changed = True
                else:
                    out.append(token)
            if changed:
                return " ".join(out)
            return cmdline

        def cmdline_to_win(line):
            if line.startswith("# "):
                return "REM " + args_to_win(line[2:])
            if line.startswith("$ # "):
                return "REM " + args_to_win(line[4:])
            if line.startswith("$ ./manage.py"):
                return "manage.py " + args_to_win(line[13:])
            if line.startswith("$ manage.py"):
                return "manage.py " + args_to_win(line[11:])
            if line.startswith("$ ./runtests.py"):
                return "runtests.py " + args_to_win(line[15:])
            if line.startswith("$ ./"):
                return args_to_win(line[4:])
            if line.startswith("$ python3"):
                return "py " + args_to_win(line[9:])
            if line.startswith("$ python"):
                return "py " + args_to_win(line[8:])
            if line.startswith("$ "):
                return args_to_win(line[2:])
            return None

        def code_block_to_win(content):
            bchanged = False
            lines = []
            for line in content:
                modline = cmdline_to_win(line)
                if modline is None:
                    lines.append(line)
                else:
                    lines.append(self.WIN_PROMPT + modline)
                    bchanged = True
            if bchanged:
                return ViewList(lines)
            return None

        env = self.state.document.settings.env
        self.arguments = ["console"]
        lit_blk_obj = super().run()[0]

        # Only do work when an HTML-format Sphinx builder is being used,
        # invoke the default behavior for the rest.
        if env.app.builder.format != "html":
            return [lit_blk_obj]

        lit_blk_obj["uid"] = str(env.new_serialno("console"))
        # Only add the tabbed UI if there is actually a Windows-specific
        # version of the CLI example.
        win_content = code_block_to_win(self.content)
        if win_content is None:
            lit_blk_obj["win_console_text"] = None
        else:
            self.content = win_content
            lit_blk_obj["win_console_text"] = super().run()[0].rawsource

        # Replace the literal_node object returned by Sphinx's CodeBlock with
        # the ConsoleNode wrapper.
        return [ConsoleNode(lit_blk_obj)]


def default_role_error(
    name, rawtext, text, lineno, inliner, options=None, content=None
):
    msg = (
        "Default role used (`single backticks`): %s. Did you mean to use two "
        "backticks for ``code``, or miss an underscore for a `link`_ ?" % rawtext
    )
    logger.warning(msg, location=(inliner.document.current_source, lineno))
    return [nodes.Text(text)], []
