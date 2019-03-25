# -*- coding: utf-8 -*-
"""
    sphinx.domains.changeset
    ~~~~~~~~~~~~~~~~~~~~~~~~

    The changeset domain.

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from collections import namedtuple

from docutils import nodes
from six import iteritems

from sphinx import addnodes
from sphinx import locale
from sphinx.deprecation import DeprecatedDict, RemovedInSphinx30Warning
from sphinx.domains import Domain
from sphinx.locale import _
from sphinx.util.docutils import SphinxDirective
from sphinx.util.nodes import set_source_info


if False:
    # For type annotation
    from typing import Any, Dict, List  # NOQA
    from sphinx.application import Sphinx  # NOQA
    from sphinx.environment import BuildEnvironment  # NOQA


versionlabels = {
    'versionadded':   _('New in version %s'),
    'versionchanged': _('Changed in version %s'),
    'deprecated':     _('Deprecated since version %s'),
}  # type: Dict[unicode, unicode]

locale.versionlabels = DeprecatedDict(
    versionlabels,
    'sphinx.locale.versionlabels is deprecated. '
    'Please use sphinx.domains.changeset.versionlabels instead.',
    RemovedInSphinx30Warning
)


# TODO: move to typing.NamedTuple after dropping py35 support (see #5958)
ChangeSet = namedtuple('ChangeSet',
                       ['type', 'docname', 'lineno', 'module', 'descname', 'content'])


class VersionChange(SphinxDirective):
    """
    Directive to describe a change/addition/deprecation in a specific version.
    """
    has_content = True
    required_arguments = 1
    optional_arguments = 1
    final_argument_whitespace = True
    option_spec = {}  # type: Dict

    def run(self):
        # type: () -> List[nodes.Node]
        node = addnodes.versionmodified()
        node.document = self.state.document
        set_source_info(self, node)
        node['type'] = self.name
        node['version'] = self.arguments[0]
        text = versionlabels[self.name] % self.arguments[0]
        if len(self.arguments) == 2:
            inodes, messages = self.state.inline_text(self.arguments[1],
                                                      self.lineno + 1)
            para = nodes.paragraph(self.arguments[1], '', *inodes, translatable=False)
            set_source_info(self, para)
            node.append(para)
        else:
            messages = []
        if self.content:
            self.state.nested_parse(self.content, self.content_offset, node)
        if len(node):
            if isinstance(node[0], nodes.paragraph) and node[0].rawsource:
                content = nodes.inline(node[0].rawsource, translatable=True)
                content.source = node[0].source
                content.line = node[0].line
                content += node[0].children
                node[0].replace_self(nodes.paragraph('', '', content, translatable=False))
            node[0].insert(0, nodes.inline('', '%s: ' % text,
                                           classes=['versionmodified']))
        else:
            para = nodes.paragraph('', '',
                                   nodes.inline('', '%s.' % text,
                                                classes=['versionmodified']),
                                   translatable=False)
            node.append(para)

        self.env.get_domain('changeset').note_changeset(node)  # type: ignore
        return [node] + messages


class ChangeSetDomain(Domain):
    """Domain for changesets."""

    name = 'changeset'
    label = 'changeset'

    initial_data = {
        'changes': {},      # version -> list of ChangeSet
    }  # type: Dict

    def clear_doc(self, docname):
        # type: (unicode) -> None
        for version, changes in iteritems(self.data['changes']):
            for changeset in changes[:]:
                if changeset.docname == docname:
                    changes.remove(changeset)

    def merge_domaindata(self, docnames, otherdata):
        # type: (List[unicode], Dict) -> None
        # XXX duplicates?
        for version, otherchanges in iteritems(otherdata['changes']):
            changes = self.data['changes'].setdefault(version, [])
            for changeset in otherchanges:
                if changeset.docname in docnames:
                    changes.append(changeset)

    def process_doc(self, env, docname, document):
        # type: (BuildEnvironment, unicode, nodes.Node) -> None
        pass  # nothing to do here. All changesets are registered on calling directive.

    def note_changeset(self, node):
        # type: (nodes.Node) -> None
        version = node['version']
        module = self.env.ref_context.get('py:module')
        objname = self.env.temp_data.get('object')
        changeset = ChangeSet(node['type'], self.env.docname, node.line,
                              module, objname, node.astext())
        self.data['changes'].setdefault(version, []).append(changeset)

    def get_changesets_for(self, version):
        # type: (unicode) -> List[ChangeSet]
        return self.data['changes'].get(version, [])


def setup(app):
    # type: (Sphinx) -> Dict[unicode, Any]
    app.add_domain(ChangeSetDomain)
    app.add_directive('deprecated', VersionChange)
    app.add_directive('versionadded', VersionChange)
    app.add_directive('versionchanged', VersionChange)

    return {
        'version': 'builtin',
        'env_version': 1,
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
