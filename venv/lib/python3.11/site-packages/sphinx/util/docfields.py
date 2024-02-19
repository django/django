"""Utility code for "Doc fields".

"Doc fields" are reST field lists in object descriptions that will
be domain-specifically transformed to a more appealing presentation.
"""
from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, Any, cast

from docutils import nodes
from docutils.nodes import Element, Node

from sphinx import addnodes
from sphinx.locale import __
from sphinx.util import logging
from sphinx.util.nodes import get_node_line

if TYPE_CHECKING:
    from docutils.parsers.rst.states import Inliner

    from sphinx.directives import ObjectDescription
    from sphinx.environment import BuildEnvironment
    from sphinx.util.typing import TextlikeNode

logger = logging.getLogger(__name__)


def _is_single_paragraph(node: nodes.field_body) -> bool:
    """True if the node only contains one paragraph (and system messages)."""
    if len(node) == 0:
        return False
    elif len(node) > 1:
        for subnode in node[1:]:  # type: Node
            if not isinstance(subnode, nodes.system_message):
                return False
    if isinstance(node[0], nodes.paragraph):
        return True
    return False


class Field:
    """A doc field that is never grouped.  It can have an argument or not, the
    argument can be linked using a specified *rolename*.  Field should be used
    for doc fields that usually don't occur more than once.

    The body can be linked using a specified *bodyrolename* if the content is
    just a single inline or text node.

    Example::

       :returns: description of the return value
       :rtype: description of the return type
    """
    is_grouped = False
    is_typed = False

    def __init__(
        self,
        name: str,
        names: tuple[str, ...] = (),
        label: str = '',
        has_arg: bool = True,
        rolename: str = '',
        bodyrolename: str = '',
    ) -> None:
        self.name = name
        self.names = names
        self.label = label
        self.has_arg = has_arg
        self.rolename = rolename
        self.bodyrolename = bodyrolename

    def make_xref(self, rolename: str, domain: str, target: str,
                  innernode: type[TextlikeNode] = addnodes.literal_emphasis,
                  contnode: Node | None = None, env: BuildEnvironment | None = None,
                  inliner: Inliner | None = None, location: Element | None = None) -> Node:
        # note: for backwards compatibility env is last, but not optional
        assert env is not None
        assert (inliner is None) == (location is None), (inliner, location)
        if not rolename:
            return contnode or innernode(target, target)
        # The domain is passed from DocFieldTransformer. So it surely exists.
        # So we don't need to take care the env.get_domain() raises an exception.
        role = env.get_domain(domain).role(rolename)
        if role is None or inliner is None:
            if role is None and inliner is not None:
                msg = __("Problem in %s domain: field is supposed "
                         "to use role '%s', but that role is not in the domain.")
                logger.warning(__(msg), domain, rolename, location=location)
            refnode = addnodes.pending_xref('', refdomain=domain, refexplicit=False,
                                            reftype=rolename, reftarget=target)
            refnode += contnode or innernode(target, target)
            env.get_domain(domain).process_field_xref(refnode)
            return refnode
        lineno = -1
        if location is not None:
            with contextlib.suppress(ValueError):
                lineno = get_node_line(location)
        ns, messages = role(rolename, target, target, lineno, inliner, {}, [])
        return nodes.inline(target, '', *ns)

    def make_xrefs(self, rolename: str, domain: str, target: str,
                   innernode: type[TextlikeNode] = addnodes.literal_emphasis,
                   contnode: Node | None = None, env: BuildEnvironment | None = None,
                   inliner: Inliner | None = None, location: Element | None = None,
                   ) -> list[Node]:
        return [self.make_xref(rolename, domain, target, innernode, contnode,
                               env, inliner, location)]

    def make_entry(self, fieldarg: str, content: list[Node]) -> tuple[str, list[Node]]:
        return (fieldarg, content)

    def make_field(
        self,
        types: dict[str, list[Node]],
        domain: str,
        item: tuple,
        env: BuildEnvironment | None = None,
        inliner: Inliner | None = None,
        location: Element | None = None,
    ) -> nodes.field:
        fieldarg, content = item
        fieldname = nodes.field_name('', self.label)
        if fieldarg:
            fieldname += nodes.Text(' ')
            fieldname.extend(self.make_xrefs(self.rolename, domain,
                                             fieldarg, nodes.Text,
                                             env=env, inliner=inliner, location=location))

        if len(content) == 1 and (
                isinstance(content[0], nodes.Text) or
                (isinstance(content[0], nodes.inline) and len(content[0]) == 1 and
                 isinstance(content[0][0], nodes.Text))):
            content = self.make_xrefs(self.bodyrolename, domain,
                                      content[0].astext(), contnode=content[0],
                                      env=env, inliner=inliner, location=location)
        fieldbody = nodes.field_body('', nodes.paragraph('', '', *content))
        return nodes.field('', fieldname, fieldbody)


class GroupedField(Field):
    """
    A doc field that is grouped; i.e., all fields of that type will be
    transformed into one field with its body being a bulleted list.  It always
    has an argument.  The argument can be linked using the given *rolename*.
    GroupedField should be used for doc fields that can occur more than once.
    If *can_collapse* is true, this field will revert to a Field if only used
    once.

    Example::

       :raises ErrorClass: description when it is raised
    """
    is_grouped = True
    list_type = nodes.bullet_list

    def __init__(self, name: str, names: tuple[str, ...] = (), label: str = '',
                 rolename: str = '', can_collapse: bool = False) -> None:
        super().__init__(name, names, label, True, rolename)
        self.can_collapse = can_collapse

    def make_field(
        self,
        types: dict[str, list[Node]],
        domain: str,
        items: tuple,
        env: BuildEnvironment | None = None,
        inliner: Inliner | None = None,
        location: Element | None = None,
    ) -> nodes.field:
        fieldname = nodes.field_name('', self.label)
        listnode = self.list_type()
        for fieldarg, content in items:
            par = nodes.paragraph()
            par.extend(self.make_xrefs(self.rolename, domain, fieldarg,
                                       addnodes.literal_strong,
                                       env=env, inliner=inliner, location=location))
            par += nodes.Text(' -- ')
            par += content
            listnode += nodes.list_item('', par)

        if len(items) == 1 and self.can_collapse:
            list_item = cast(nodes.list_item, listnode[0])
            fieldbody = nodes.field_body('', list_item[0])
            return nodes.field('', fieldname, fieldbody)

        fieldbody = nodes.field_body('', listnode)
        return nodes.field('', fieldname, fieldbody)


class TypedField(GroupedField):
    """
    A doc field that is grouped and has type information for the arguments.  It
    always has an argument.  The argument can be linked using the given
    *rolename*, the type using the given *typerolename*.

    Two uses are possible: either parameter and type description are given
    separately, using a field from *names* and one from *typenames*,
    respectively, or both are given using a field from *names*, see the example.

    Example::

       :param foo: description of parameter foo
       :type foo:  SomeClass

       -- or --

       :param SomeClass foo: description of parameter foo
    """
    is_typed = True

    def __init__(
        self,
        name: str,
        names: tuple[str, ...] = (),
        typenames: tuple[str, ...] = (),
        label: str = '',
        rolename: str = '',
        typerolename: str = '',
        can_collapse: bool = False,
    ) -> None:
        super().__init__(name, names, label, rolename, can_collapse)
        self.typenames = typenames
        self.typerolename = typerolename

    def make_field(
        self,
        types: dict[str, list[Node]],
        domain: str,
        items: tuple,
        env: BuildEnvironment | None = None,
        inliner: Inliner | None = None,
        location: Element | None = None,
    ) -> nodes.field:
        def handle_item(fieldarg: str, content: str) -> nodes.paragraph:
            par = nodes.paragraph()
            par.extend(self.make_xrefs(self.rolename, domain, fieldarg,
                                       addnodes.literal_strong, env=env))
            if fieldarg in types:
                par += nodes.Text(' (')
                # NOTE: using .pop() here to prevent a single type node to be
                # inserted twice into the doctree, which leads to
                # inconsistencies later when references are resolved
                fieldtype = types.pop(fieldarg)
                if len(fieldtype) == 1 and isinstance(fieldtype[0], nodes.Text):
                    typename = fieldtype[0].astext()
                    par.extend(self.make_xrefs(self.typerolename, domain, typename,
                                               addnodes.literal_emphasis, env=env,
                                               inliner=inliner, location=location))
                else:
                    par += fieldtype
                par += nodes.Text(')')
            par += nodes.Text(' -- ')
            par += content
            return par

        fieldname = nodes.field_name('', self.label)
        if len(items) == 1 and self.can_collapse:
            fieldarg, content = items[0]
            bodynode: Node = handle_item(fieldarg, content)
        else:
            bodynode = self.list_type()
            for fieldarg, content in items:
                bodynode += nodes.list_item('', handle_item(fieldarg, content))
        fieldbody = nodes.field_body('', bodynode)
        return nodes.field('', fieldname, fieldbody)


class DocFieldTransformer:
    """
    Transforms field lists in "doc field" syntax into better-looking
    equivalents, using the field type definitions given on a domain.
    """
    typemap: dict[str, tuple[Field, bool]]

    def __init__(self, directive: ObjectDescription) -> None:
        self.directive = directive

        self.typemap = directive.get_field_type_map()

    def transform_all(self, node: addnodes.desc_content) -> None:
        """Transform all field list children of a node."""
        # don't traverse, only handle field lists that are immediate children
        for child in node:
            if isinstance(child, nodes.field_list):
                self.transform(child)

    def transform(self, node: nodes.field_list) -> None:
        """Transform a single field list *node*."""
        typemap = self.typemap

        entries: list[nodes.field | tuple[Field, Any, Element]] = []
        groupindices: dict[str, int] = {}
        types: dict[str, dict] = {}

        # step 1: traverse all fields and collect field types and content
        for field in cast(list[nodes.field], node):
            assert len(field) == 2
            field_name = cast(nodes.field_name, field[0])
            field_body = cast(nodes.field_body, field[1])
            try:
                # split into field type and argument
                fieldtype_name, fieldarg = field_name.astext().split(None, 1)
            except ValueError:
                # maybe an argument-less field type?
                fieldtype_name, fieldarg = field_name.astext(), ''
            typedesc, is_typefield = typemap.get(fieldtype_name, (None, None))

            # collect the content, trying not to keep unnecessary paragraphs
            if _is_single_paragraph(field_body):
                paragraph = cast(nodes.paragraph, field_body[0])
                content = paragraph.children
            else:
                content = field_body.children

            # sort out unknown fields
            if typedesc is None or typedesc.has_arg != bool(fieldarg):
                # either the field name is unknown, or the argument doesn't
                # match the spec; capitalize field name and be done with it
                new_fieldname = fieldtype_name[0:1].upper() + fieldtype_name[1:]
                if fieldarg:
                    new_fieldname += ' ' + fieldarg
                field_name[0] = nodes.Text(new_fieldname)
                entries.append(field)

                # but if this has a type then we can at least link it
                if (typedesc and is_typefield and content and
                        len(content) == 1 and isinstance(content[0], nodes.Text)):
                    typed_field = cast(TypedField, typedesc)
                    target = content[0].astext()
                    xrefs = typed_field.make_xrefs(
                        typed_field.typerolename,
                        self.directive.domain or '',
                        target,
                        contnode=content[0],
                        env=self.directive.state.document.settings.env,
                    )
                    if _is_single_paragraph(field_body):
                        paragraph = cast(nodes.paragraph, field_body[0])
                        paragraph.clear()
                        paragraph.extend(xrefs)
                    else:
                        field_body.clear()
                        field_body += nodes.paragraph('', '', *xrefs)

                continue

            typename = typedesc.name

            # if the field specifies a type, put it in the types collection
            if is_typefield:
                # filter out only inline nodes; others will result in invalid
                # markup being written out
                content = [n for n in content if isinstance(n, (nodes.Inline, nodes.Text))]
                if content:
                    types.setdefault(typename, {})[fieldarg] = content
                continue

            # also support syntax like ``:param type name:``
            if typedesc.is_typed:
                try:
                    argtype, argname = fieldarg.rsplit(None, 1)
                except ValueError:
                    pass
                else:
                    types.setdefault(typename, {})[argname] = \
                        [nodes.Text(argtype)]
                    fieldarg = argname

            translatable_content = nodes.inline(field_body.rawsource,
                                                translatable=True)
            translatable_content.document = field_body.parent.document
            translatable_content.source = field_body.parent.source
            translatable_content.line = field_body.parent.line
            translatable_content += content

            # grouped entries need to be collected in one entry, while others
            # get one entry per field
            if typedesc.is_grouped:
                if typename in groupindices:
                    group = cast(tuple[Field, list, Node], entries[groupindices[typename]])
                else:
                    groupindices[typename] = len(entries)
                    group = (typedesc, [], field)
                    entries.append(group)
                new_entry = typedesc.make_entry(fieldarg, [translatable_content])
                group[1].append(new_entry)
            else:
                new_entry = typedesc.make_entry(fieldarg, [translatable_content])
                entries.append((typedesc, new_entry, field))

        # step 2: all entries are collected, construct the new field list
        new_list = nodes.field_list()
        for entry in entries:
            if isinstance(entry, nodes.field):
                # pass-through old field
                new_list += entry
            else:
                fieldtype, items, location = entry
                fieldtypes = types.get(fieldtype.name, {})
                env = self.directive.state.document.settings.env
                inliner = self.directive.state.inliner
                domain = self.directive.domain or ''
                new_list += fieldtype.make_field(fieldtypes, domain, items,
                                                 env=env, inliner=inliner, location=location)

        node.replace_self(new_list)
