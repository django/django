# -*- coding: utf-8 -*-
"""
    sphinx.roles
    ~~~~~~~~~~~~

    Handlers for additional ReST roles.

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from docutils import nodes, utils
from six import iteritems

from sphinx import addnodes
from sphinx.errors import SphinxError
from sphinx.locale import _
from sphinx.util import ws_re
from sphinx.util.nodes import split_explicit_title, process_index_entry, \
    set_role_source_info

if False:
    # For type annotation
    from typing import Any, Dict, List, Tuple, Type  # NOQA
    from docutils.parsers.rst.states import Inliner  # NOQA
    from sphinx.application import Sphinx  # NOQA
    from sphinx.environment import BuildEnvironment  # NOQA


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

class XRefRole(object):
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

    nodeclass = addnodes.pending_xref  # type: Type[nodes.Node]
    innernodeclass = nodes.literal

    def __init__(self, fix_parens=False, lowercase=False,
                 nodeclass=None, innernodeclass=None, warn_dangling=False):
        # type: (bool, bool, Type[nodes.Node], Type[nodes.Node], bool) -> None
        self.fix_parens = fix_parens
        self.lowercase = lowercase
        self.warn_dangling = warn_dangling
        if nodeclass is not None:
            self.nodeclass = nodeclass
        if innernodeclass is not None:
            self.innernodeclass = innernodeclass

    def _fix_parens(self, env, has_explicit_title, title, target):
        # type: (BuildEnvironment, bool, unicode, unicode) -> Tuple[unicode, unicode]
        if not has_explicit_title:
            if title.endswith('()'):
                # remove parentheses
                title = title[:-2]
            if env.config.add_function_parentheses:
                # add them back to all occurrences if configured
                title += '()'
        # remove parentheses from the target too
        if target.endswith('()'):
            target = target[:-2]
        return title, target

    def __call__(self, typ, rawtext, text, lineno, inliner,
                 options={}, content=[]):
        # type: (unicode, unicode, unicode, int, Inliner, Dict, List[unicode]) -> Tuple[List[nodes.Node], List[nodes.Node]]  # NOQA
        env = inliner.document.settings.env
        if not typ:
            typ = env.temp_data.get('default_role')
            if not typ:
                typ = env.config.default_role
            if not typ:
                raise SphinxError('cannot determine default role!')
        else:
            typ = typ.lower()
        if ':' not in typ:
            domain, role = '', typ  # type: unicode, unicode
            classes = ['xref', role]
        else:
            domain, role = typ.split(':', 1)
            classes = ['xref', domain, '%s-%s' % (domain, role)]
        # if the first character is a bang, don't cross-reference at all
        if text[0:1] == '!':
            text = utils.unescape(text)[1:]
            if self.fix_parens:
                text, tgt = self._fix_parens(env, False, text, "")
            innernode = self.innernodeclass(rawtext, text, classes=classes)
            return self.result_nodes(inliner.document, env, innernode,
                                     is_ref=False)
        # split title and target in role content
        has_explicit_title, title, target = split_explicit_title(text)
        title = utils.unescape(title)
        target = utils.unescape(target)
        # fix-up title and target
        if self.lowercase:
            target = target.lower()
        if self.fix_parens:
            title, target = self._fix_parens(
                env, has_explicit_title, title, target)
        # create the reference node
        refnode = self.nodeclass(rawtext, reftype=role, refdomain=domain,
                                 refexplicit=has_explicit_title)
        # we may need the line number for warnings
        set_role_source_info(inliner, lineno, refnode)  # type: ignore
        title, target = self.process_link(
            env, refnode, has_explicit_title, title, target)
        # now that the target and title are finally determined, set them
        refnode['reftarget'] = target
        refnode += self.innernodeclass(rawtext, title, classes=classes)
        # we also need the source document
        refnode['refdoc'] = env.docname
        refnode['refwarn'] = self.warn_dangling
        # result_nodes allow further modification of return values
        return self.result_nodes(inliner.document, env, refnode, is_ref=True)

    # methods that can be overwritten

    def process_link(self, env, refnode, has_explicit_title, title, target):
        # type: (BuildEnvironment, nodes.reference, bool, unicode, unicode) -> Tuple[unicode, unicode]  # NOQA
        """Called after parsing title and target text, and creating the
        reference node (given in *refnode*).  This method can alter the
        reference node and must return a new (or the same) ``(title, target)``
        tuple.
        """
        return title, ws_re.sub(' ', target)

    def result_nodes(self, document, env, node, is_ref):
        # type: (nodes.document, BuildEnvironment, nodes.Node, bool) -> Tuple[List[nodes.Node], List[nodes.Node]]  # NOQA
        """Called before returning the finished nodes.  *node* is the reference
        node if one was created (*is_ref* is then true), else the content node.
        This method can add other nodes and must return a ``(nodes, messages)``
        tuple (the usual return value of a role function).
        """
        return [node], []


class AnyXRefRole(XRefRole):
    def process_link(self, env, refnode, has_explicit_title, title, target):
        # type: (BuildEnvironment, nodes.reference, bool, unicode, unicode) -> Tuple[unicode, unicode]  # NOQA
        result = XRefRole.process_link(self, env, refnode, has_explicit_title,
                                       title, target)
        # add all possible context info (i.e. std:program, py:module etc.)
        refnode.attributes.update(env.ref_context)
        return result


def indexmarkup_role(typ, rawtext, text, lineno, inliner, options={}, content=[]):
    # type: (unicode, unicode, unicode, int, Inliner, Dict, List[unicode]) -> Tuple[List[nodes.Node], List[nodes.Node]]  # NOQA
    """Role for PEP/RFC references that generate an index entry."""
    env = inliner.document.settings.env
    if not typ:
        assert env.temp_data['default_role']
        typ = env.temp_data['default_role'].lower()
    else:
        typ = typ.lower()

    has_explicit_title, title, target = split_explicit_title(text)
    title = utils.unescape(title)
    target = utils.unescape(target)
    targetid = 'index-%s' % env.new_serialno('index')
    indexnode = addnodes.index()
    targetnode = nodes.target('', '', ids=[targetid])
    inliner.document.note_explicit_target(targetnode)
    if typ == 'pep':
        indexnode['entries'] = [
            ('single', _('Python Enhancement Proposals; PEP %s') % target,
             targetid, '', None)]
        anchor = ''  # type: unicode
        anchorindex = target.find('#')
        if anchorindex > 0:
            target, anchor = target[:anchorindex], target[anchorindex:]
        if not has_explicit_title:
            title = "PEP " + utils.unescape(title)
        try:
            pepnum = int(target)
        except ValueError:
            msg = inliner.reporter.error('invalid PEP number %s' % target,
                                         line=lineno)
            prb = inliner.problematic(rawtext, rawtext, msg)
            return [prb], [msg]
        ref = inliner.document.settings.pep_base_url + 'pep-%04d' % pepnum
        sn = nodes.strong(title, title)
        rn = nodes.reference('', '', internal=False, refuri=ref + anchor,
                             classes=[typ])
        rn += sn
        return [indexnode, targetnode, rn], []
    elif typ == 'rfc':
        indexnode['entries'] = [
            ('single', 'RFC; RFC %s' % target, targetid, '', None)]
        anchor = ''
        anchorindex = target.find('#')
        if anchorindex > 0:
            target, anchor = target[:anchorindex], target[anchorindex:]
        if not has_explicit_title:
            title = "RFC " + utils.unescape(title)
        try:
            rfcnum = int(target)
        except ValueError:
            msg = inliner.reporter.error('invalid RFC number %s' % target,
                                         line=lineno)
            prb = inliner.problematic(rawtext, rawtext, msg)
            return [prb], [msg]
        ref = inliner.document.settings.rfc_base_url + inliner.rfc_url % rfcnum
        sn = nodes.strong(title, title)
        rn = nodes.reference('', '', internal=False, refuri=ref + anchor,
                             classes=[typ])
        rn += sn
        return [indexnode, targetnode, rn], []
    else:
        raise ValueError('unknown role type: %s' % typ)


_amp_re = re.compile(r'(?<!&)&(?![&\s])')


def menusel_role(typ, rawtext, text, lineno, inliner, options={}, content=[]):
    # type: (unicode, unicode, unicode, int, Inliner, Dict, List[unicode]) -> Tuple[List[nodes.Node], List[nodes.Node]]  # NOQA
    env = inliner.document.settings.env
    if not typ:
        assert env.temp_data['default_role']
        typ = env.temp_data['default_role'].lower()
    else:
        typ = typ.lower()

    text = utils.unescape(text)
    if typ == 'menuselection':
        text = text.replace('-->', u'\N{TRIANGULAR BULLET}')
    spans = _amp_re.split(text)

    node = nodes.inline(rawtext=rawtext)
    for i, span in enumerate(spans):
        span = span.replace('&&', '&')
        if i == 0:
            if len(span) > 0:
                textnode = nodes.Text(span)
                node += textnode
            continue
        accel_node = nodes.inline()
        letter_node = nodes.Text(span[0])
        accel_node += letter_node
        accel_node['classes'].append('accelerator')
        node += accel_node
        textnode = nodes.Text(span[1:])
        node += textnode

    node['classes'].append(typ)
    return [node], []


_litvar_re = re.compile('{([^}]+)}')
parens_re = re.compile(r'(\\*{|\\*})')


def emph_literal_role(typ, rawtext, text, lineno, inliner,
                      options={}, content=[]):
    # type: (unicode, unicode, unicode, int, Inliner, Dict, List[unicode]) -> Tuple[List[nodes.Node], List[nodes.Node]]  # NOQA
    env = inliner.document.settings.env
    if not typ:
        assert env.temp_data['default_role']
        typ = env.temp_data['default_role'].lower()
    else:
        typ = typ.lower()

    retnode = nodes.literal(role=typ.lower(), classes=[typ])
    parts = list(parens_re.split(utils.unescape(text)))
    stack = ['']
    for part in parts:
        matched = parens_re.match(part)
        if matched:
            backslashes = len(part) - 1
            if backslashes % 2 == 1:    # escaped
                stack[-1] += "\\" * int((backslashes - 1) / 2) + part[-1]
            elif part[-1] == '{':       # rparen
                stack[-1] += "\\" * int(backslashes / 2)
                if len(stack) >= 2 and stack[-2] == "{":
                    # nested
                    stack[-1] += "{"
                else:
                    # start emphasis
                    stack.append('{')
                    stack.append('')
            else:                       # lparen
                stack[-1] += "\\" * int(backslashes / 2)
                if len(stack) == 3 and stack[1] == "{" and len(stack[2]) > 0:
                    # emphasized word found
                    if stack[0]:
                        retnode += nodes.Text(stack[0], stack[0])
                    retnode += nodes.emphasis(stack[2], stack[2])
                    stack = ['']
                else:
                    # emphasized word not found; the rparen is not a special symbol
                    stack.append('}')
                    stack = [''.join(stack)]
        else:
            stack[-1] += part
    if ''.join(stack):
        # remaining is treated as Text
        text = ''.join(stack)
        retnode += nodes.Text(text, text)

    return [retnode], []


_abbr_re = re.compile(r'\((.*)\)$', re.S)


def abbr_role(typ, rawtext, text, lineno, inliner, options={}, content=[]):
    # type: (unicode, unicode, unicode, int, Inliner, Dict, List[unicode]) -> Tuple[List[nodes.Node], List[nodes.Node]]  # NOQA
    text = utils.unescape(text)
    m = _abbr_re.search(text)
    if m is None:
        return [addnodes.abbreviation(text, text, **options)], []
    abbr = text[:m.start()].strip()
    expl = m.group(1)
    options = options.copy()
    options['explanation'] = expl
    return [addnodes.abbreviation(abbr, abbr, **options)], []


def index_role(typ, rawtext, text, lineno, inliner, options={}, content=[]):
    # type: (unicode, unicode, unicode, int, Inliner, Dict, List[unicode]) -> Tuple[List[nodes.Node], List[nodes.Node]]  # NOQA
    # create new reference target
    env = inliner.document.settings.env
    targetid = 'index-%s' % env.new_serialno('index')
    targetnode = nodes.target('', '', ids=[targetid])
    # split text and target in role content
    has_explicit_title, title, target = split_explicit_title(text)
    title = utils.unescape(title)
    target = utils.unescape(target)
    # if an explicit target is given, we can process it as a full entry
    if has_explicit_title:
        entries = process_index_entry(target, targetid)
    # otherwise we just create a "single" entry
    else:
        # but allow giving main entry
        main = ''
        if target.startswith('!'):
            target = target[1:]
            title = title[1:]
            main = 'main'
        entries = [('single', target, targetid, main, None)]
    indexnode = addnodes.index()
    indexnode['entries'] = entries
    set_role_source_info(inliner, lineno, indexnode)  # type: ignore
    textnode = nodes.Text(title, title)
    return [indexnode, targetnode, textnode], []


specific_docroles = {
    # links to download references
    'download': XRefRole(nodeclass=addnodes.download_reference),
    # links to anything
    'any': AnyXRefRole(warn_dangling=True),

    'pep': indexmarkup_role,
    'rfc': indexmarkup_role,
    'guilabel': menusel_role,
    'menuselection': menusel_role,
    'file': emph_literal_role,
    'samp': emph_literal_role,
    'abbr': abbr_role,
    'index': index_role,
}


def setup(app):
    # type: (Sphinx) -> Dict[unicode, Any]
    from docutils.parsers.rst import roles

    for rolename, nodeclass in iteritems(generic_docroles):
        generic = roles.GenericRole(rolename, nodeclass)
        role = roles.CustomRole(rolename, generic, {'classes': [rolename]})
        roles.register_local_role(rolename, role)

    for rolename, func in iteritems(specific_docroles):
        roles.register_local_role(rolename, func)

    return {
        'version': 'builtin',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
