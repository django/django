"""
Sphinx plugins for Django documentation.
"""
import json
import os
import re

from docutils import nodes
from docutils.parsers.rst import Directive
from docutils.statemachine import ViewList
from sphinx import addnodes
from sphinx.builders.html import StandaloneHTMLBuilder
from sphinx.directives.code import CodeBlock
from sphinx.domains.std import Cmdoption
from sphinx.errors import ExtensionError
from sphinx.util import logging
from sphinx.util.console import bold
from sphinx.writers.html import HTMLTranslator

logger = logging.getLogger(__name__)
# RE for option descriptions without a '--' prefix
simple_option_desc_re = re.compile(
    r'([-_a-zA-Z0-9]+)(\s*.*?)(?=,\s+(?:/|-|--)|$)')


def setup(app):
    app.add_crossref_type(
        directivename="setting",
        rolename="setting",
        indextemplate="pair: %s; setting",
    )
    app.add_crossref_type(
        directivename="templatetag",
        rolename="ttag",
        indextemplate="pair: %s; template tag"
    )
    app.add_crossref_type(
        directivename="templatefilter",
        rolename="tfilter",
        indextemplate="pair: %s; template filter"
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
    app.add_directive('django-admin-option', Cmdoption)
    app.add_config_value('django_next_version', '0.0', True)
    app.add_directive('versionadded', VersionDirective)
    app.add_directive('versionchanged', VersionDirective)
    app.add_builder(DjangoStandaloneHTMLBuilder)
    app.set_translator('djangohtml', DjangoHTMLTranslator)
    app.set_translator('json', DjangoHTMLTranslator)
    app.add_node(
        ConsoleNode,
        html=(visit_console_html, None),
        latex=(visit_console_dummy, depart_console_dummy),
        man=(visit_console_dummy, depart_console_dummy),
        text=(visit_console_dummy, depart_console_dummy),
        texinfo=(visit_console_dummy, depart_console_dummy),
    )
    app.add_directive('console', ConsoleDirective)
    app.connect('html-page-context', html_page_context_hook)
    app.add_role('default-role-error', default_role_error)
    return {'parallel_read_safe': True}


class VersionDirective(Directive):
    has_content = True
    required_arguments = 1
    optional_arguments = 1
    final_argument_whitespace = True
    option_spec = {}

    def run(self):
        if len(self.arguments) > 1:
            msg = """Only one argument accepted for directive '{directive_name}::'.
            Comments should be provided as content,
            not as an extra argument.""".format(directive_name=self.name)
            raise self.error(msg)

        env = self.state.document.settings.env
        ret = []
        node = addnodes.versionmodified()
        ret.append(node)

        if self.arguments[0] == env.config.django_next_version:
            node['version'] = "Development version"
        else:
            node['version'] = self.arguments[0]

        node['type'] = self.name
        if self.content:
            self.state.nested_parse(self.content, self.content_offset, node)
        try:
            env.get_domain('changeset').note_changeset(node)
        except ExtensionError:
            # Sphinx < 1.8: Domain 'changeset' is not registered
            env.note_versionchange(node['type'], node['version'], node, self.lineno)
        return ret


class DjangoHTMLTranslator(HTMLTranslator):
    """
    Django-specific reST to HTML tweaks.
    """

    # Don't use border=1, which docutils does by default.
    def visit_table(self, node):
        self.context.append(self.compact_p)
        self.compact_p = True
        self._table_row_index = 0  # Needed by Sphinx
        self.body.append(self.starttag(node, 'table', CLASS='docutils'))

    def depart_table(self, node):
        self.compact_p = self.context.pop()
        self.body.append('</table>\n')

    def visit_desc_parameterlist(self, node):
        self.body.append('(')  # by default sphinx puts <big> around the "("
        self.first_param = 1
        self.optional_param_level = 0
        self.param_separator = node.child_text_separator
        self.required_params_left = sum(isinstance(c, addnodes.desc_parameter) for c in node.children)

    def depart_desc_parameterlist(self, node):
        self.body.append(')')

    #
    # Turn the "new in version" stuff (versionadded/versionchanged) into a
    # better callout -- the Sphinx default is just a little span,
    # which is a bit less obvious that I'd like.
    #
    # FIXME: these messages are all hardcoded in English. We need to change
    # that to accommodate other language docs, but I can't work out how to make
    # that work.
    #
    version_text = {
        'versionchanged': 'Changed in Django %s',
        'versionadded': 'New in Django %s',
    }

    def visit_versionmodified(self, node):
        self.body.append(
            self.starttag(node, 'div', CLASS=node['type'])
        )
        version_text = self.version_text.get(node['type'])
        if version_text:
            title = "%s%s" % (
                version_text % node['version'],
                ":" if len(node) else "."
            )
            self.body.append('<span class="title">%s</span> ' % title)

    def depart_versionmodified(self, node):
        self.body.append("</div>\n")

    # Give each section a unique ID -- nice for custom CSS hooks
    def visit_section(self, node):
        old_ids = node.get('ids', [])
        node['ids'] = ['s-' + i for i in old_ids]
        node['ids'].extend(old_ids)
        super().visit_section(node)
        node['ids'] = old_ids


def parse_django_admin_node(env, sig, signode):
    command = sig.split(' ')[0]
    env.ref_context['std:program'] = command
    title = "django-admin %s" % sig
    signode += addnodes.desc_name(title, title)
    return command


class DjangoStandaloneHTMLBuilder(StandaloneHTMLBuilder):
    """
    Subclass to add some extra things we need.
    """

    name = 'djangohtml'

    def finish(self):
        super().finish()
        logger.info(bold("writing templatebuiltins.js..."))
        xrefs = self.env.domaindata["std"]["objects"]
        templatebuiltins = {
            "ttags": [
                n for ((t, n), (k, a)) in xrefs.items()
                if t == "templatetag" and k == "ref/templates/builtins"
            ],
            "tfilters": [
                n for ((t, n), (k, a)) in xrefs.items()
                if t == "templatefilter" and k == "ref/templates/builtins"
            ],
        }
        outfilename = os.path.join(self.outdir, "templatebuiltins.js")
        with open(outfilename, 'w') as fp:
            fp.write('var django_template_builtins = ')
            json.dump(templatebuiltins, fp)
            fp.write(';\n')


class ConsoleNode(nodes.literal_block):
    """
    Custom node to override the visit/depart event handlers at registration
    time. Wrap a literal_block object and defer to it.
    """
    tagname = 'ConsoleNode'

    def __init__(self, litblk_obj):
        self.wrapped = litblk_obj

    def __getattr__(self, attr):
        if attr == 'wrapped':
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
    if self.builder.name in ('djangohtml', 'json') and node['win_console_text']:
        # Put a mark on the document object signaling the fact the directive
        # has been used on it.
        self.document._console_directive_used_flag = True
        uid = node['uid']
        self.body.append('''\
<div class="console-block" id="console-block-%(id)s">
<input class="c-tab-unix" id="c-tab-%(id)s-unix" type="radio" name="console-%(id)s" checked>
<label for="c-tab-%(id)s-unix" title="Linux/macOS">&#xf17c/&#xf179</label>
<input class="c-tab-win" id="c-tab-%(id)s-win" type="radio" name="console-%(id)s">
<label for="c-tab-%(id)s-win" title="Windows">&#xf17a</label>
<section class="c-content-unix" id="c-content-%(id)s-unix">\n''' % {'id': uid})
        try:
            self.visit_literal_block(node)
        except nodes.SkipNode:
            pass
        self.body.append('</section>\n')

        self.body.append('<section class="c-content-win" id="c-content-%(id)s-win">\n' % {'id': uid})
        win_text = node['win_console_text']
        highlight_args = {'force': True}
        linenos = node.get('linenos', False)

        def warner(msg):
            self.builder.warn(msg, (self.builder.current_docname, node.line))

        highlighted = self.highlighter.highlight_block(
            win_text, 'doscon', warn=warner, linenos=linenos, **highlight_args
        )
        self.body.append(highlighted)
        self.body.append('</section>\n')
        self.body.append('</div>\n')
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
    # grey comment with no highlighting at all.
    WIN_PROMPT = r'...\> '

    def run(self):

        def args_to_win(cmdline):
            changed = False
            out = []
            for token in cmdline.split():
                if token[:2] == './':
                    token = token[2:]
                    changed = True
                elif token[:2] == '~/':
                    token = '%HOMEPATH%\\' + token[2:]
                    changed = True
                elif token == 'make':
                    token = 'make.bat'
                    changed = True
                if '://' not in token and 'git' not in cmdline:
                    out.append(token.replace('/', '\\'))
                    changed = True
                else:
                    out.append(token)
            if changed:
                return ' '.join(out)
            return cmdline

        def cmdline_to_win(line):
            if line.startswith('# '):
                return 'REM ' + args_to_win(line[2:])
            if line.startswith('$ # '):
                return 'REM ' + args_to_win(line[4:])
            if line.startswith('$ ./manage.py'):
                return 'manage.py ' + args_to_win(line[13:])
            if line.startswith('$ manage.py'):
                return 'manage.py ' + args_to_win(line[11:])
            if line.startswith('$ ./runtests.py'):
                return 'runtests.py ' + args_to_win(line[15:])
            if line.startswith('$ ./'):
                return args_to_win(line[4:])
            if line.startswith('$ python3'):
                return 'py ' + args_to_win(line[9:])
            if line.startswith('$ python'):
                return 'py ' + args_to_win(line[8:])
            if line.startswith('$ '):
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
        self.arguments = ['console']
        lit_blk_obj = super().run()[0]

        # Only do work when the djangohtml HTML Sphinx builder is being used,
        # invoke the default behavior for the rest.
        if env.app.builder.name not in ('djangohtml', 'json'):
            return [lit_blk_obj]

        lit_blk_obj['uid'] = '%s' % env.new_serialno('console')
        # Only add the tabbed UI if there is actually a Windows-specific
        # version of the CLI example.
        win_content = code_block_to_win(self.content)
        if win_content is None:
            lit_blk_obj['win_console_text'] = None
        else:
            self.content = win_content
            lit_blk_obj['win_console_text'] = super().run()[0].rawsource

        # Replace the literal_node object returned by Sphinx's CodeBlock with
        # the ConsoleNode wrapper.
        return [ConsoleNode(lit_blk_obj)]


def html_page_context_hook(app, pagename, templatename, context, doctree):
    # Put a bool on the context used to render the template. It's used to
    # control inclusion of console-tabs.css and activation of the JavaScript.
    # This way it's include only from HTML files rendered from reST files where
    # the ConsoleDirective is used.
    context['include_console_assets'] = getattr(doctree, '_console_directive_used_flag', False)


def default_role_error(
    name, rawtext, text, lineno, inliner, options=None, content=None
):
    msg = (
        "Default role used (`single backticks`): %s. Did you mean to use two "
        "backticks for ``code``, or miss an underscore for a `link`_ ?"
        % rawtext
    )
    logger.warning(msg, location=(inliner.document.current_source, lineno))
    return [nodes.Text(text)], []
