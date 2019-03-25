# -*- coding: utf-8 -*-
"""
    sphinx.util.docfields
    ~~~~~~~~~~~~~~~~~~~~~

    "Doc fields" are reST field lists in object descriptions that will
    be domain-specifically transformed to a more appealing presentation.

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""
from __future__ import absolute_import

from docutils import nodes

from sphinx import addnodes

if False:
    # For type annotation
    from typing import Any, Dict, List, Tuple  # NOQA
    from sphinx.domains import Domain  # NOQA
    from sphinx.environment import BuildEnvironment  # NOQA


def _is_single_paragraph(node):
    # type: (nodes.Node) -> bool
    """True if the node only contains one paragraph (and system messages)."""
    if len(node) == 0:
        return False
    elif len(node) > 1:
        for subnode in node[1:]:
            if not isinstance(subnode, nodes.system_message):
                return False
    if isinstance(node[0], nodes.paragraph):
        return True
    return False


class Field(object):
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

    def __init__(self, name, names=(), label=None, has_arg=True, rolename=None,
                 bodyrolename=None):
        # type: (unicode, Tuple[unicode, ...], unicode, bool, unicode, unicode) -> None
        self.name = name
        self.names = names
        self.label = label
        self.has_arg = has_arg
        self.rolename = rolename
        self.bodyrolename = bodyrolename

    def make_xref(self,
                  rolename,       # type: unicode
                  domain,         # type: unicode
                  target,         # type: unicode
                  innernode=addnodes.literal_emphasis,  # type: nodes.Node
                  contnode=None,  # type: nodes.Node
                  env=None,       # type: BuildEnvironment
                  ):
        # type: (...) -> nodes.Node
        if not rolename:
            return contnode or innernode(target, target)
        refnode = addnodes.pending_xref('', refdomain=domain, refexplicit=False,
                                        reftype=rolename, reftarget=target)
        refnode += contnode or innernode(target, target)
        if env:
            env.domains[domain].process_field_xref(refnode)
        return refnode

    def make_xrefs(self,
                   rolename,       # type: unicode
                   domain,         # type: unicode
                   target,         # type: unicode
                   innernode=addnodes.literal_emphasis,  # type: nodes.Node
                   contnode=None,  # type: nodes.Node
                   env=None,       # type: BuildEnvironment
                   ):
        # type: (...) -> List[nodes.Node]
        return [self.make_xref(rolename, domain, target, innernode, contnode, env)]

    def make_entry(self, fieldarg, content):
        # type: (List, unicode) -> Tuple[List, unicode]
        return (fieldarg, content)

    def make_field(self,
                   types,     # type: Dict[unicode, List[nodes.Node]]
                   domain,    # type: unicode
                   item,      # type: Tuple
                   env=None,  # type: BuildEnvironment
                   ):
        # type: (...) -> nodes.field
        fieldarg, content = item
        fieldname = nodes.field_name('', self.label)
        if fieldarg:
            fieldname += nodes.Text(' ')
            fieldname.extend(self.make_xrefs(self.rolename, domain,
                                             fieldarg, nodes.Text, env=env))

        if len(content) == 1 and (
                isinstance(content[0], nodes.Text) or
                (isinstance(content[0], nodes.inline) and len(content[0]) == 1 and
                 isinstance(content[0][0], nodes.Text))):
            content = self.make_xrefs(self.bodyrolename, domain,
                                      content[0].astext(), contnode=content[0], env=env)
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

    def __init__(self, name, names=(), label=None, rolename=None,
                 can_collapse=False):
        # type: (unicode, Tuple[unicode, ...], unicode, unicode, bool) -> None
        Field.__init__(self, name, names, label, True, rolename)
        self.can_collapse = can_collapse

    def make_field(self,
                   types,     # type: Dict[unicode, List[nodes.Node]]
                   domain,    # type: unicode
                   items,     # type: Tuple
                   env=None,  # type: BuildEnvironment
                   ):
        # type: (...) -> nodes.field
        fieldname = nodes.field_name('', self.label)
        listnode = self.list_type()
        for fieldarg, content in items:
            par = nodes.paragraph()
            par.extend(self.make_xrefs(self.rolename, domain, fieldarg,
                                       addnodes.literal_strong, env=env))
            par += nodes.Text(' -- ')
            par += content
            listnode += nodes.list_item('', par)

        if len(items) == 1 and self.can_collapse:
            fieldbody = nodes.field_body('', listnode[0][0])
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

    def __init__(self, name, names=(), typenames=(), label=None,
                 rolename=None, typerolename=None, can_collapse=False):
        # type: (unicode, Tuple[unicode, ...], Tuple[unicode, ...], unicode, unicode, unicode, bool) -> None  # NOQA
        GroupedField.__init__(self, name, names, label, rolename, can_collapse)
        self.typenames = typenames
        self.typerolename = typerolename

    def make_field(self,
                   types,     # type: Dict[unicode, List[nodes.Node]]
                   domain,    # type: unicode
                   items,     # type: Tuple
                   env=None,  # type: BuildEnvironment
                   ):
        # type: (...) -> nodes.field
        def handle_item(fieldarg, content):
            # type: (unicode, unicode) -> nodes.paragraph
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
                    typename = u''.join(n.astext() for n in fieldtype)
                    par.extend(self.make_xrefs(self.typerolename, domain, typename,
                                               addnodes.literal_emphasis, env=env))
                else:
                    par += fieldtype
                par += nodes.Text(')')
            par += nodes.Text(' -- ')
            par += content
            return par

        fieldname = nodes.field_name('', self.label)
        if len(items) == 1 and self.can_collapse:
            fieldarg, content = items[0]
            bodynode = handle_item(fieldarg, content)
        else:
            bodynode = self.list_type()
            for fieldarg, content in items:
                bodynode += nodes.list_item('', handle_item(fieldarg, content))
        fieldbody = nodes.field_body('', bodynode)
        return nodes.field('', fieldname, fieldbody)


class DocFieldTransformer(object):
    """
    Transforms field lists in "doc field" syntax into better-looking
    equivalents, using the field type definitions given on a domain.
    """

    def __init__(self, directive):
        # type: (Any) -> None
        self.directive = directive
        if '_doc_field_type_map' not in directive.__class__.__dict__:
            directive.__class__._doc_field_type_map = \
                self.preprocess_fieldtypes(directive.__class__.doc_field_types)
        self.typemap = directive._doc_field_type_map

    def preprocess_fieldtypes(self, types):
        # type: (List) -> Dict[unicode, Tuple[Any, bool]]
        typemap = {}
        for fieldtype in types:
            for name in fieldtype.names:
                typemap[name] = fieldtype, False
            if fieldtype.is_typed:
                for name in fieldtype.typenames:
                    typemap[name] = fieldtype, True
        return typemap

    def transform_all(self, node):
        # type: (nodes.Node) -> None
        """Transform all field list children of a node."""
        # don't traverse, only handle field lists that are immediate children
        for child in node:
            if isinstance(child, nodes.field_list):
                self.transform(child)

    def transform(self, node):
        # type: (nodes.Node) -> None
        """Transform a single field list *node*."""
        typemap = self.typemap

        entries = []
        groupindices = {}  # type: Dict[unicode, int]
        types = {}  # type: Dict[unicode, Dict]

        # step 1: traverse all fields and collect field types and content
        for field in node:
            fieldname, fieldbody = field
            try:
                # split into field type and argument
                fieldtype, fieldarg = fieldname.astext().split(None, 1)
            except ValueError:
                # maybe an argument-less field type?
                fieldtype, fieldarg = fieldname.astext(), ''
            typedesc, is_typefield = typemap.get(fieldtype, (None, None))

            # collect the content, trying not to keep unnecessary paragraphs
            if _is_single_paragraph(fieldbody):
                content = fieldbody.children[0].children
            else:
                content = fieldbody.children

            # sort out unknown fields
            if typedesc is None or typedesc.has_arg != bool(fieldarg):
                # either the field name is unknown, or the argument doesn't
                # match the spec; capitalize field name and be done with it
                new_fieldname = fieldtype[0:1].upper() + fieldtype[1:]
                if fieldarg:
                    new_fieldname += ' ' + fieldarg
                fieldname[0] = nodes.Text(new_fieldname)
                entries.append(field)

                # but if this has a type then we can at least link it
                if (typedesc and is_typefield and content and
                        len(content) == 1 and isinstance(content[0], nodes.Text)):
                    target = content[0].astext()
                    xrefs = typedesc.make_xrefs(
                        typedesc.typerolename,
                        self.directive.domain,
                        target,
                        contnode=content[0],
                    )
                    if _is_single_paragraph(fieldbody):
                        fieldbody.children[0].clear()
                        fieldbody.children[0].extend(xrefs)
                    else:
                        fieldbody.clear()
                        fieldbody += nodes.paragraph()
                        fieldbody[0].extend(xrefs)

                continue

            typename = typedesc.name

            # if the field specifies a type, put it in the types collection
            if is_typefield:
                # filter out only inline nodes; others will result in invalid
                # markup being written out
                content = [n for n in content if isinstance(n, nodes.Inline) or
                           isinstance(n, nodes.Text)]
                if content:
                    types.setdefault(typename, {})[fieldarg] = content
                continue

            # also support syntax like ``:param type name:``
            if typedesc.is_typed:
                try:
                    argtype, argname = fieldarg.split(None, 1)
                except ValueError:
                    pass
                else:
                    types.setdefault(typename, {})[argname] = \
                        [nodes.Text(argtype)]
                    fieldarg = argname

            translatable_content = nodes.inline(fieldbody.rawsource,
                                                translatable=True)
            translatable_content.document = fieldbody.parent.document
            translatable_content.source = fieldbody.parent.source
            translatable_content.line = fieldbody.parent.line
            translatable_content += content

            # grouped entries need to be collected in one entry, while others
            # get one entry per field
            if typedesc.is_grouped:
                if typename in groupindices:
                    group = entries[groupindices[typename]]
                else:
                    groupindices[typename] = len(entries)
                    group = [typedesc, []]
                    entries.append(group)
                entry = typedesc.make_entry(fieldarg, [translatable_content])
                group[1].append(entry)
            else:
                entry = typedesc.make_entry(fieldarg, [translatable_content])
                entries.append([typedesc, entry])

        # step 2: all entries are collected, construct the new field list
        new_list = nodes.field_list()
        for entry in entries:
            if isinstance(entry, nodes.field):
                # pass-through old field
                new_list += entry
            else:
                fieldtype, content = entry
                fieldtypes = types.get(fieldtype.name, {})
                env = self.directive.state.document.settings.env
                new_list += fieldtype.make_field(fieldtypes, self.directive.domain,
                                                 content, env=env)

        node.replace_self(new_list)
