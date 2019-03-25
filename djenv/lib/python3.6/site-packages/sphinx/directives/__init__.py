# -*- coding: utf-8 -*-
"""
    sphinx.directives
    ~~~~~~~~~~~~~~~~~

    Handlers for additional ReST directives.

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from docutils import nodes
from docutils.parsers.rst import directives, roles

from sphinx import addnodes
from sphinx.util.docfields import DocFieldTransformer
from sphinx.util.docutils import SphinxDirective

# import all directives sphinx provides
from sphinx.directives.code import (  # noqa
    Highlight, CodeBlock, LiteralInclude
)
from sphinx.directives.other import (  # noqa
    TocTree, Author, Index, VersionChange, SeeAlso,
    TabularColumns, Centered, Acks, HList, Only, Include, Class
)
from sphinx.directives.patches import (  # noqa
    Figure, Meta
)

if False:
    # For type annotation
    from typing import Any, Dict, List  # NOQA
    from sphinx.application import Sphinx  # NOQA
    from sphinx.config import Config  # NOQA
    from sphinx.environment import BuildEnvironment  # NOQA


# RE to strip backslash escapes
nl_escape_re = re.compile(r'\\\n')
strip_backslash_re = re.compile(r'\\(.)')


class ObjectDescription(SphinxDirective):
    """
    Directive to describe a class, function or similar object.  Not used
    directly, but subclassed (in domain-specific directives) to add custom
    behavior.
    """

    has_content = True
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = True
    option_spec = {
        'noindex': directives.flag,
    }

    # types of doc fields that this directive handles, see sphinx.util.docfields
    doc_field_types = []    # type: List[Any]
    domain = None           # type: unicode
    objtype = None          # type: unicode
    indexnode = None        # type: addnodes.index

    def get_signatures(self):
        # type: () -> List[unicode]
        """
        Retrieve the signatures to document from the directive arguments.  By
        default, signatures are given as arguments, one per line.

        Backslash-escaping of newlines is supported.
        """
        lines = nl_escape_re.sub('', self.arguments[0]).split('\n')
        # remove backslashes to support (dummy) escapes; helps Vim highlighting
        return [strip_backslash_re.sub(r'\1', line.strip()) for line in lines]

    def handle_signature(self, sig, signode):
        # type: (unicode, addnodes.desc_signature) -> Any
        """
        Parse the signature *sig* into individual nodes and append them to
        *signode*. If ValueError is raised, parsing is aborted and the whole
        *sig* is put into a single desc_name node.

        The return value should be a value that identifies the object.  It is
        passed to :meth:`add_target_and_index()` unchanged, and otherwise only
        used to skip duplicates.
        """
        raise ValueError

    def add_target_and_index(self, name, sig, signode):
        # type: (Any, unicode, addnodes.desc_signature) -> None
        """
        Add cross-reference IDs and entries to self.indexnode, if applicable.

        *name* is whatever :meth:`handle_signature()` returned.
        """
        return  # do nothing by default

    def before_content(self):
        # type: () -> None
        """
        Called before parsing content. Used to set information about the current
        directive context on the build environment.
        """
        pass

    def after_content(self):
        # type: () -> None
        """
        Called after parsing content. Used to reset information about the
        current directive context on the build environment.
        """
        pass

    def run(self):
        # type: () -> List[nodes.Node]
        """
        Main directive entry function, called by docutils upon encountering the
        directive.

        This directive is meant to be quite easily subclassable, so it delegates
        to several additional methods.  What it does:

        * find out if called as a domain-specific directive, set self.domain
        * create a `desc` node to fit all description inside
        * parse standard options, currently `noindex`
        * create an index node if needed as self.indexnode
        * parse all given signatures (as returned by self.get_signatures())
          using self.handle_signature(), which should either return a name
          or raise ValueError
        * add index entries using self.add_target_and_index()
        * parse the content and handle doc fields in it
        """
        if ':' in self.name:
            self.domain, self.objtype = self.name.split(':', 1)
        else:
            self.domain, self.objtype = '', self.name
        self.indexnode = addnodes.index(entries=[])

        node = addnodes.desc()
        node.document = self.state.document
        node['domain'] = self.domain
        # 'desctype' is a backwards compatible attribute
        node['objtype'] = node['desctype'] = self.objtype
        node['noindex'] = noindex = ('noindex' in self.options)

        self.names = []  # type: List[unicode]
        signatures = self.get_signatures()
        for i, sig in enumerate(signatures):
            # add a signature node for each signature in the current unit
            # and add a reference target for it
            signode = addnodes.desc_signature(sig, '')
            signode['first'] = False
            node.append(signode)
            try:
                # name can also be a tuple, e.g. (classname, objname);
                # this is strictly domain-specific (i.e. no assumptions may
                # be made in this base class)
                name = self.handle_signature(sig, signode)
            except ValueError:
                # signature parsing failed
                signode.clear()
                signode += addnodes.desc_name(sig, sig)
                continue  # we don't want an index entry here
            if name not in self.names:
                self.names.append(name)
                if not noindex:
                    # only add target and index entry if this is the first
                    # description of the object with this name in this desc block
                    self.add_target_and_index(name, sig, signode)

        contentnode = addnodes.desc_content()
        node.append(contentnode)
        if self.names:
            # needed for association of version{added,changed} directives
            self.env.temp_data['object'] = self.names[0]
        self.before_content()
        self.state.nested_parse(self.content, self.content_offset, contentnode)
        DocFieldTransformer(self).transform_all(contentnode)
        self.env.temp_data['object'] = None
        self.after_content()
        return [self.indexnode, node]


# backwards compatible old name
DescDirective = ObjectDescription


class DefaultRole(SphinxDirective):
    """
    Set the default interpreted text role.  Overridden from docutils.
    """

    optional_arguments = 1
    final_argument_whitespace = False

    def run(self):
        # type: () -> List[nodes.Node]
        if not self.arguments:
            if '' in roles._roles:
                # restore the "default" default role
                del roles._roles['']
            return []
        role_name = self.arguments[0]
        role, messages = roles.role(role_name, self.state_machine.language,
                                    self.lineno, self.state.reporter)
        if role is None:
            error = self.state.reporter.error(
                'Unknown interpreted text role "%s".' % role_name,
                nodes.literal_block(self.block_text, self.block_text),
                line=self.lineno)
            return messages + [error]
        roles._roles[''] = role
        self.env.temp_data['default_role'] = role_name
        return messages


class DefaultDomain(SphinxDirective):
    """
    Directive to (re-)set the default domain for this source file.
    """

    has_content = False
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = False
    option_spec = {}  # type: Dict

    def run(self):
        # type: () -> List[nodes.Node]
        domain_name = self.arguments[0].lower()
        # if domain_name not in env.domains:
        #     # try searching by label
        #     for domain in itervalues(env.domains):
        #         if domain.label.lower() == domain_name:
        #             domain_name = domain.name
        #             break
        self.env.temp_data['default_domain'] = self.env.domains.get(domain_name)
        return []


def setup(app):
    # type: (Sphinx) -> Dict[unicode, Any]
    directives.register_directive('default-role', DefaultRole)
    directives.register_directive('default-domain', DefaultDomain)
    directives.register_directive('describe', ObjectDescription)
    # new, more consistent, name
    directives.register_directive('object', ObjectDescription)

    return {
        'version': 'builtin',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
