"""Handlers for additional ReST directives."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, Generic, TypeVar, cast

from docutils import nodes
from docutils.parsers.rst import directives, roles

from sphinx import addnodes
from sphinx.addnodes import desc_signature  # NoQA: TCH001
from sphinx.util import docutils
from sphinx.util.docfields import DocFieldTransformer, Field, TypedField
from sphinx.util.docutils import SphinxDirective
from sphinx.util.nodes import nested_parse_with_titles
from sphinx.util.typing import OptionSpec  # NoQA: TCH001

if TYPE_CHECKING:
    from docutils.nodes import Node

    from sphinx.application import Sphinx


# RE to strip backslash escapes
nl_escape_re = re.compile(r'\\\n')
strip_backslash_re = re.compile(r'\\(.)')


def optional_int(argument: str) -> int | None:
    """
    Check for an integer argument or None value; raise ``ValueError`` if not.
    """
    if argument is None:
        return None
    else:
        value = int(argument)
        if value < 0:
            msg = 'negative value; must be positive or zero'
            raise ValueError(msg)
        return value


ObjDescT = TypeVar('ObjDescT')


class ObjectDescription(SphinxDirective, Generic[ObjDescT]):
    """
    Directive to describe a class, function or similar object.  Not used
    directly, but subclassed (in domain-specific directives) to add custom
    behavior.
    """

    has_content = True
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = True
    option_spec: OptionSpec = {
        'no-index': directives.flag,
        'no-index-entry': directives.flag,
        'no-contents-entry': directives.flag,
        'no-typesetting': directives.flag,
        'noindex': directives.flag,
        'noindexentry': directives.flag,
        'nocontentsentry': directives.flag,
    }

    # types of doc fields that this directive handles, see sphinx.util.docfields
    doc_field_types: list[Field] = []
    domain: str | None = None
    objtype: str  # set when `run` method is called
    indexnode: addnodes.index

    # Warning: this might be removed in future version. Don't touch this from extensions.
    _doc_field_type_map: dict[str, tuple[Field, bool]] = {}

    def get_field_type_map(self) -> dict[str, tuple[Field, bool]]:
        if self._doc_field_type_map == {}:
            self._doc_field_type_map = {}
            for field in self.doc_field_types:
                for name in field.names:
                    self._doc_field_type_map[name] = (field, False)

                if field.is_typed:
                    typed_field = cast(TypedField, field)
                    for name in typed_field.typenames:
                        self._doc_field_type_map[name] = (field, True)

        return self._doc_field_type_map

    def get_signatures(self) -> list[str]:
        """
        Retrieve the signatures to document from the directive arguments.  By
        default, signatures are given as arguments, one per line.
        """
        lines = nl_escape_re.sub('', self.arguments[0]).split('\n')
        if self.config.strip_signature_backslash:
            # remove backslashes to support (dummy) escapes; helps Vim highlighting
            return [strip_backslash_re.sub(r'\1', line.strip()) for line in lines]
        else:
            return [line.strip() for line in lines]

    def handle_signature(self, sig: str, signode: desc_signature) -> ObjDescT:
        """
        Parse the signature *sig* into individual nodes and append them to
        *signode*. If ValueError is raised, parsing is aborted and the whole
        *sig* is put into a single desc_name node.

        The return value should be a value that identifies the object.  It is
        passed to :meth:`add_target_and_index()` unchanged, and otherwise only
        used to skip duplicates.
        """
        raise ValueError

    def add_target_and_index(self, name: ObjDescT, sig: str, signode: desc_signature) -> None:
        """
        Add cross-reference IDs and entries to self.indexnode, if applicable.

        *name* is whatever :meth:`handle_signature()` returned.
        """
        return  # do nothing by default

    def before_content(self) -> None:
        """
        Called before parsing content. Used to set information about the current
        directive context on the build environment.
        """
        pass

    def transform_content(self, contentnode: addnodes.desc_content) -> None:
        """
        Called after creating the content through nested parsing,
        but before the ``object-description-transform`` event is emitted,
        and before the info-fields are transformed.
        Can be used to manipulate the content.
        """
        pass

    def after_content(self) -> None:
        """
        Called after parsing content. Used to reset information about the
        current directive context on the build environment.
        """
        pass

    def _object_hierarchy_parts(self, sig_node: desc_signature) -> tuple[str, ...]:
        """
        Returns a tuple of strings, one entry for each part of the object's
        hierarchy (e.g. ``('module', 'submodule', 'Class', 'method')``). The
        returned tuple is used to properly nest children within parents in the
        table of contents, and can also be used within the
        :py:meth:`_toc_entry_name` method.

        This method must not be used outwith table of contents generation.
        """
        return ()

    def _toc_entry_name(self, sig_node: desc_signature) -> str:
        """
        Returns the text of the table of contents entry for the object.

        This function is called once, in :py:meth:`run`, to set the name for the
        table of contents entry (a special attribute ``_toc_name`` is set on the
        object node, later used in
        ``environment.collectors.toctree.TocTreeCollector.process_doc().build_toc()``
        when the table of contents entries are collected).

        To support table of contents entries for their objects, domains must
        override this method, also respecting the configuration setting
        ``toc_object_entries_show_parents``. Domains must also override
        :py:meth:`_object_hierarchy_parts`, with one (string) entry for each part of the
        object's hierarchy. The result of this method is set on the signature
        node, and can be accessed as ``sig_node['_toc_parts']`` for use within
        this method. The resulting tuple is also used to properly nest children
        within parents in the table of contents.

        An example implementations of this method is within the python domain
        (:meth:`!PyObject._toc_entry_name`). The python domain sets the
        ``_toc_parts`` attribute within the :py:meth:`handle_signature()`
        method.
        """
        return ''

    def run(self) -> list[Node]:
        """
        Main directive entry function, called by docutils upon encountering the
        directive.

        This directive is meant to be quite easily subclassable, so it delegates
        to several additional methods.  What it does:

        * find out if called as a domain-specific directive, set self.domain
        * create a `desc` node to fit all description inside
        * parse standard options, currently `no-index`
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
        source, line = self.get_source_info()
        # If any options were specified to the directive,
        # self.state.document.current_line will at this point be set to
        # None.  To ensure nodes created as part of the signature have a line
        # number set, set the document's line number correctly.
        #
        # Note that we need to subtract one from the line number since
        # note_source uses 0-based line numbers.
        if line is not None:
            line -= 1
        self.state.document.note_source(source, line)
        node['domain'] = self.domain
        # 'desctype' is a backwards compatible attribute
        node['objtype'] = node['desctype'] = self.objtype
        node['no-index'] = node['noindex'] = no_index = (
            'no-index' in self.options
            # xref RemovedInSphinx90Warning
            # deprecate noindex in Sphinx 9.0
            or 'noindex' in self.options)
        node['no-index-entry'] = node['noindexentry'] = (
            'no-index-entry' in self.options
            # xref RemovedInSphinx90Warning
            # deprecate noindexentry in Sphinx 9.0
            or 'noindexentry' in self.options)
        node['no-contents-entry'] = node['nocontentsentry'] = (
            'no-contents-entry' in self.options
            # xref RemovedInSphinx90Warning
            # deprecate nocontentsentry in Sphinx 9.0
            or 'nocontentsentry' in self.options)
        node['no-typesetting'] = ('no-typesetting' in self.options)
        if self.domain:
            node['classes'].append(self.domain)
        node['classes'].append(node['objtype'])

        self.names: list[ObjDescT] = []
        signatures = self.get_signatures()
        for sig in signatures:
            # add a signature node for each signature in the current unit
            # and add a reference target for it
            signode = addnodes.desc_signature(sig, '')
            self.set_source_info(signode)
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
            finally:
                # Private attributes for ToC generation. Will be modified or removed
                # without notice.
                if self.env.app.config.toc_object_entries:
                    signode['_toc_parts'] = self._object_hierarchy_parts(signode)
                    signode['_toc_name'] = self._toc_entry_name(signode)
                else:
                    signode['_toc_parts'] = ()
                    signode['_toc_name'] = ''
            if name not in self.names:
                self.names.append(name)
                if not no_index:
                    # only add target and index entry if this is the first
                    # description of the object with this name in this desc block
                    self.add_target_and_index(name, sig, signode)

        contentnode = addnodes.desc_content()
        node.append(contentnode)

        if self.names:
            # needed for association of version{added,changed} directives
            self.env.temp_data['object'] = self.names[0]
        self.before_content()
        nested_parse_with_titles(self.state, self.content, contentnode, self.content_offset)
        self.transform_content(contentnode)
        self.env.app.emit('object-description-transform',
                          self.domain, self.objtype, contentnode)
        DocFieldTransformer(self).transform_all(contentnode)
        self.env.temp_data['object'] = None
        self.after_content()

        if node['no-typesetting']:
            # Attempt to return the index node, and a new target node
            # containing all the ids of this node and its children.
            # If ``:no-index:`` is set, or there are no ids on the node
            # or any of its children, then just return the index node,
            # as Docutils expects a target node to have at least one id.
            if node_ids := [node_id for el in node.findall(nodes.Element)
                            for node_id in el.get('ids', ())]:
                target_node = nodes.target(ids=node_ids)
                self.set_source_info(target_node)
                return [self.indexnode, target_node]
            return [self.indexnode]
        return [self.indexnode, node]


class DefaultRole(SphinxDirective):
    """
    Set the default interpreted text role.  Overridden from docutils.
    """

    optional_arguments = 1
    final_argument_whitespace = False

    def run(self) -> list[Node]:
        if not self.arguments:
            docutils.unregister_role('')
            return []
        role_name = self.arguments[0]
        role, messages = roles.role(role_name, self.state_machine.language,
                                    self.lineno, self.state.reporter)
        if role:  # type: ignore[truthy-function]
            docutils.register_role('', role)  # type: ignore[arg-type]
            self.env.temp_data['default_role'] = role_name
        else:
            literal_block = nodes.literal_block(self.block_text, self.block_text)
            reporter = self.state.reporter
            error = reporter.error('Unknown interpreted text role "%s".' % role_name,
                                   literal_block, line=self.lineno)
            messages += [error]

        return cast(list[nodes.Node], messages)


class DefaultDomain(SphinxDirective):
    """
    Directive to (re-)set the default domain for this source file.
    """

    has_content = False
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = False
    option_spec: OptionSpec = {}

    def run(self) -> list[Node]:
        domain_name = self.arguments[0].lower()
        # if domain_name not in env.domains:
        #     # try searching by label
        #     for domain in env.domains.values():
        #         if domain.label.lower() == domain_name:
        #             domain_name = domain.name
        #             break
        self.env.temp_data['default_domain'] = self.env.domains.get(domain_name)
        return []


def setup(app: Sphinx) -> dict[str, Any]:
    app.add_config_value("strip_signature_backslash", False, 'env')
    directives.register_directive('default-role', DefaultRole)
    directives.register_directive('default-domain', DefaultDomain)
    directives.register_directive('describe', ObjectDescription)
    # new, more consistent, name
    directives.register_directive('object', ObjectDescription)

    app.add_event('object-description-transform')

    return {
        'version': 'builtin',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
