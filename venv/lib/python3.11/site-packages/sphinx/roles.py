"""Handlers for additional ReST roles."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

import docutils.parsers.rst.directives
import docutils.parsers.rst.roles
import docutils.parsers.rst.states
from docutils import nodes, utils

from sphinx import addnodes
from sphinx.locale import _, __
from sphinx.util import ws_re
from sphinx.util.docutils import ReferenceRole, SphinxRole

if TYPE_CHECKING:
    from collections.abc import Sequence

    from docutils.nodes import Element, Node, TextElement, system_message

    from sphinx.application import Sphinx
    from sphinx.environment import BuildEnvironment
    from sphinx.util.typing import RoleFunction


generic_docroles = {
    'command': addnodes.literal_strong,
    'dfn': nodes.emphasis,
    'kbd': nodes.literal,
    'mailheader': addnodes.literal_emphasis,
    'makevar': addnodes.literal_strong,
    'manpage': addnodes.manpage,
    'mimetype': addnodes.literal_emphasis,
    'newsgroup': addnodes.literal_emphasis,
    'program': addnodes.literal_strong,  # XXX should be an x-ref
    'regexp': nodes.literal,
}


# -- generic cross-reference role ----------------------------------------------

class XRefRole(ReferenceRole):
    """
    A generic cross-referencing role.  To create a callable that can be used as
    a role function, create an instance of this class.

    The general features of this role are:

    * Automatic creation of a reference and a content node.
    * Optional separation of title and target with `title <target>`.
    * The implementation is a class rather than a function to make
      customization easier.

    Customization can be done in two ways:

    * Supplying constructor parameters:
      * `fix_parens` to normalize parentheses (strip from target, and add to
        title if configured)
      * `lowercase` to lowercase the target
      * `nodeclass` and `innernodeclass` select the node classes for
        the reference and the content node

    * Subclassing and overwriting `process_link()` and/or `result_nodes()`.
    """

    nodeclass: type[Element] = addnodes.pending_xref
    innernodeclass: type[TextElement] = nodes.literal

    def __init__(self, fix_parens: bool = False, lowercase: bool = False,
                 nodeclass: type[Element] | None = None,
                 innernodeclass: type[TextElement] | None = None,
                 warn_dangling: bool = False) -> None:
        self.fix_parens = fix_parens
        self.lowercase = lowercase
        self.warn_dangling = warn_dangling
        if nodeclass is not None:
            self.nodeclass = nodeclass
        if innernodeclass is not None:
            self.innernodeclass = innernodeclass

        super().__init__()

    def update_title_and_target(self, title: str, target: str) -> tuple[str, str]:
        if not self.has_explicit_title:
            if title.endswith('()'):
                # remove parentheses
                title = title[:-2]
            if self.config.add_function_parentheses:
                # add them back to all occurrences if configured
                title += '()'
        # remove parentheses from the target too
        if target.endswith('()'):
            target = target[:-2]
        return title, target

    def run(self) -> tuple[list[Node], list[system_message]]:
        if ':' not in self.name:
            self.refdomain, self.reftype = '', self.name
            self.classes = ['xref', self.reftype]
        else:
            self.refdomain, self.reftype = self.name.split(':', 1)
            self.classes = ['xref', self.refdomain, f'{self.refdomain}-{self.reftype}']

        if self.disabled:
            return self.create_non_xref_node()
        else:
            return self.create_xref_node()

    def create_non_xref_node(self) -> tuple[list[Node], list[system_message]]:
        text = utils.unescape(self.text[1:])
        if self.fix_parens:
            self.has_explicit_title = False  # treat as implicit
            text, target = self.update_title_and_target(text, "")

        node = self.innernodeclass(self.rawtext, text, classes=self.classes)
        return self.result_nodes(self.inliner.document, self.env, node, is_ref=False)

    def create_xref_node(self) -> tuple[list[Node], list[system_message]]:
        target = self.target
        title = self.title
        if self.lowercase:
            target = target.lower()
        if self.fix_parens:
            title, target = self.update_title_and_target(title, target)

        # create the reference node
        options = {'refdoc': self.env.docname,
                   'refdomain': self.refdomain,
                   'reftype': self.reftype,
                   'refexplicit': self.has_explicit_title,
                   'refwarn': self.warn_dangling}
        refnode = self.nodeclass(self.rawtext, **options)
        self.set_source_info(refnode)

        # determine the target and title for the class
        title, target = self.process_link(self.env, refnode, self.has_explicit_title,
                                          title, target)
        refnode['reftarget'] = target
        refnode += self.innernodeclass(self.rawtext, title, classes=self.classes)

        return self.result_nodes(self.inliner.document, self.env, refnode, is_ref=True)

    # methods that can be overwritten

    def process_link(self, env: BuildEnvironment, refnode: Element, has_explicit_title: bool,
                     title: str, target: str) -> tuple[str, str]:
        """Called after parsing title and target text, and creating the
        reference node (given in *refnode*).  This method can alter the
        reference node and must return a new (or the same) ``(title, target)``
        tuple.
        """
        return title, ws_re.sub(' ', target)

    def result_nodes(self, document: nodes.document, env: BuildEnvironment, node: Element,
                     is_ref: bool) -> tuple[list[Node], list[system_message]]:
        """Called before returning the finished nodes.  *node* is the reference
        node if one was created (*is_ref* is then true), else the content node.
        This method can add other nodes and must return a ``(nodes, messages)``
        tuple (the usual return value of a role function).
        """
        return [node], []


class AnyXRefRole(XRefRole):
    def process_link(self, env: BuildEnvironment, refnode: Element, has_explicit_title: bool,
                     title: str, target: str) -> tuple[str, str]:
        result = super().process_link(env, refnode, has_explicit_title, title, target)
        # add all possible context info (i.e. std:program, py:module etc.)
        refnode.attributes.update(env.ref_context)
        return result


class PEP(ReferenceRole):
    def run(self) -> tuple[list[Node], list[system_message]]:
        target_id = 'index-%s' % self.env.new_serialno('index')
        entries = [('single', _('Python Enhancement Proposals; PEP %s') % self.target,
                    target_id, '', None)]

        index = addnodes.index(entries=entries)
        target = nodes.target('', '', ids=[target_id])
        self.inliner.document.note_explicit_target(target)

        try:
            refuri = self.build_uri()
            reference = nodes.reference('', '', internal=False, refuri=refuri, classes=['pep'])
            if self.has_explicit_title:
                reference += nodes.strong(self.title, self.title)
            else:
                title = "PEP " + self.title
                reference += nodes.strong(title, title)
        except ValueError:
            msg = self.inliner.reporter.error(__('invalid PEP number %s') % self.target,
                                              line=self.lineno)
            prb = self.inliner.problematic(self.rawtext, self.rawtext, msg)
            return [prb], [msg]

        return [index, target, reference], []

    def build_uri(self) -> str:
        base_url = self.inliner.document.settings.pep_base_url
        ret = self.target.split('#', 1)
        if len(ret) == 2:
            return base_url + 'pep-%04d/#%s' % (int(ret[0]), ret[1])
        else:
            return base_url + 'pep-%04d/' % int(ret[0])


class RFC(ReferenceRole):
    def run(self) -> tuple[list[Node], list[system_message]]:
        target_id = 'index-%s' % self.env.new_serialno('index')
        entries = [('single', 'RFC; RFC %s' % self.target, target_id, '', None)]

        index = addnodes.index(entries=entries)
        target = nodes.target('', '', ids=[target_id])
        self.inliner.document.note_explicit_target(target)

        try:
            refuri = self.build_uri()
            reference = nodes.reference('', '', internal=False, refuri=refuri, classes=['rfc'])
            if self.has_explicit_title:
                reference += nodes.strong(self.title, self.title)
            else:
                title = "RFC " + self.title
                reference += nodes.strong(title, title)
        except ValueError:
            msg = self.inliner.reporter.error(__('invalid RFC number %s') % self.target,
                                              line=self.lineno)
            prb = self.inliner.problematic(self.rawtext, self.rawtext, msg)
            return [prb], [msg]

        return [index, target, reference], []

    def build_uri(self) -> str:
        base_url = self.inliner.document.settings.rfc_base_url
        ret = self.target.split('#', 1)
        if len(ret) == 2:
            return base_url + self.inliner.rfc_url % int(ret[0]) + '#' + ret[1]
        else:
            return base_url + self.inliner.rfc_url % int(ret[0])


_amp_re = re.compile(r'(?<!&)&(?![&\s])')


class GUILabel(SphinxRole):
    amp_re = re.compile(r'(?<!&)&(?![&\s])')

    def run(self) -> tuple[list[Node], list[system_message]]:
        node = nodes.inline(rawtext=self.rawtext, classes=[self.name])
        spans = self.amp_re.split(self.text)
        node += nodes.Text(spans.pop(0))
        for span in spans:
            span = span.replace('&&', '&')

            letter = nodes.Text(span[0])
            accelerator = nodes.inline('', '', letter, classes=['accelerator'])
            node += accelerator
            node += nodes.Text(span[1:])

        return [node], []


class MenuSelection(GUILabel):
    BULLET_CHARACTER = '\N{TRIANGULAR BULLET}'

    def run(self) -> tuple[list[Node], list[system_message]]:
        self.text = self.text.replace('-->', self.BULLET_CHARACTER)
        return super().run()


_litvar_re = re.compile('{([^}]+)}')
parens_re = re.compile(r'(\\*{|\\*})')


class EmphasizedLiteral(SphinxRole):
    parens_re = re.compile(r'(\\\\|\\{|\\}|{|})')

    def run(self) -> tuple[list[Node], list[system_message]]:
        children = self.parse(self.text)
        node = nodes.literal(self.rawtext, '', *children,
                             role=self.name.lower(), classes=[self.name])

        return [node], []

    def parse(self, text: str) -> list[Node]:
        result: list[Node] = []

        stack = ['']
        for part in self.parens_re.split(text):
            if part == '\\\\':  # escaped backslash
                stack[-1] += '\\'
            elif part == '{':
                if len(stack) >= 2 and stack[-2] == "{":  # nested
                    stack[-1] += "{"
                else:
                    # start emphasis
                    stack.append('{')
                    stack.append('')
            elif part == '}':
                if len(stack) == 3 and stack[1] == "{" and len(stack[2]) > 0:
                    # emphasized word found
                    if stack[0]:
                        result.append(nodes.Text(stack[0]))
                    result.append(nodes.emphasis(stack[2], stack[2]))
                    stack = ['']
                else:
                    # emphasized word not found; the rparen is not a special symbol
                    stack.append('}')
                    stack = [''.join(stack)]
            elif part == '\\{':  # escaped left-brace
                stack[-1] += '{'
            elif part == '\\}':  # escaped right-brace
                stack[-1] += '}'
            else:  # others (containing escaped braces)
                stack[-1] += part

        if ''.join(stack):
            # remaining is treated as Text
            text = ''.join(stack)
            result.append(nodes.Text(text))

        return result


_abbr_re = re.compile(r'\((.*)\)$', re.S)


class Abbreviation(SphinxRole):
    abbr_re = re.compile(r'\((.*)\)$', re.S)

    def run(self) -> tuple[list[Node], list[system_message]]:
        options = self.options.copy()
        matched = self.abbr_re.search(self.text)
        if matched:
            text = self.text[:matched.start()].strip()
            options['explanation'] = matched.group(1)
        else:
            text = self.text

        return [nodes.abbreviation(self.rawtext, text, **options)], []


# Sphinx provides the `code-block` directive for highlighting code blocks.
# Docutils provides the `code` role which in theory can be used similarly by
# defining a custom role for a given programming language:
#
#     .. .. role:: python(code)
#          :language: python
#          :class: highlight
#
# In practice this does not produce correct highlighting because it uses a
# separate highlighting mechanism that results in the "long" pygments class
# names rather than "short" pygments class names produced by the Sphinx
# `code-block` directive and for which this extension contains CSS rules.
#
# In addition, even if that issue is fixed, because the highlighting
# implementation in docutils, despite being based on pygments, differs from that
# used by Sphinx, the output does not exactly match that produced by the Sphinx
# `code-block` directive.
#
# This issue is noted here: //github.com/sphinx-doc/sphinx/issues/5157
#
# This overrides the docutils `code` role to perform highlighting in the same
# way as the Sphinx `code-block` directive.
#
# TODO: Change to use `SphinxRole` once SphinxRole is fixed to support options.
def code_role(name: str, rawtext: str, text: str, lineno: int,
              inliner: docutils.parsers.rst.states.Inliner,
              options: dict | None = None, content: Sequence[str] = (),
              ) -> tuple[list[Node], list[system_message]]:
    if options is None:
        options = {}
    options = options.copy()
    docutils.parsers.rst.roles.set_classes(options)
    language = options.get('language', '')
    classes = ['code']
    if language:
        classes.append('highlight')
    if 'classes' in options:
        classes.extend(options['classes'])

    if language and language not in classes:
        classes.append(language)

    node = nodes.literal(rawtext, text, classes=classes, language=language)

    return [node], []


code_role.options = {  # type: ignore[attr-defined]
    'class': docutils.parsers.rst.directives.class_option,
    'language': docutils.parsers.rst.directives.unchanged,
}


specific_docroles: dict[str, RoleFunction] = {
    # links to download references
    'download': XRefRole(nodeclass=addnodes.download_reference),
    # links to anything
    'any': AnyXRefRole(warn_dangling=True),

    'pep': PEP(),
    'rfc': RFC(),
    'guilabel': GUILabel(),
    'menuselection': MenuSelection(),
    'file': EmphasizedLiteral(),
    'samp': EmphasizedLiteral(),
    'abbr': Abbreviation(),
}


def setup(app: Sphinx) -> dict[str, Any]:
    from docutils.parsers.rst import roles

    for rolename, nodeclass in generic_docroles.items():
        generic = roles.GenericRole(rolename, nodeclass)
        role = roles.CustomRole(rolename, generic, {'classes': [rolename]})
        roles.register_local_role(rolename, role)

    for rolename, func in specific_docroles.items():
        roles.register_local_role(rolename, func)

    # Since docutils registers it as a canonical role, override it as a
    # canonical role as well.
    roles.register_canonical_role('code', code_role)

    return {
        'version': 'builtin',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
