# -*- coding: utf-8 -*-
"""
    sphinx.domains
    ~~~~~~~~~~~~~~

    Support for domains, which are groupings of description directives
    and roles describing e.g. constructs of one programming language.

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import copy

from six import iteritems

from sphinx.errors import SphinxError
from sphinx.locale import _

if False:
    # For type annotation
    from typing import Any, Callable, Dict, Iterable, List, Tuple, Type, Union  # NOQA
    from docutils import nodes  # NOQA
    from docutils.parsers.rst.states import Inliner  # NOQA
    from sphinx.builders import Builder  # NOQA
    from sphinx.environment import BuildEnvironment  # NOQA
    from sphinx.roles import XRefRole  # NOQA
    from sphinx.util.typing import RoleFunction  # NOQA


class ObjType(object):
    """
    An ObjType is the description for a type of object that a domain can
    document.  In the object_types attribute of Domain subclasses, object type
    names are mapped to instances of this class.

    Constructor arguments:

    - *lname*: localized name of the type (do not include domain name)
    - *roles*: all the roles that can refer to an object of this type
    - *attrs*: object attributes -- currently only "searchprio" is known,
      which defines the object's priority in the full-text search index,
      see :meth:`Domain.get_objects()`.
    """

    known_attrs = {
        'searchprio': 1,
    }

    def __init__(self, lname, *roles, **attrs):
        # type: (unicode, Any, Any) -> None
        self.lname = lname                      # type: unicode
        self.roles = roles                      # type: Tuple
        self.attrs = self.known_attrs.copy()    # type: Dict
        self.attrs.update(attrs)


class Index(object):
    """
    An Index is the description for a domain-specific index.  To add an index to
    a domain, subclass Index, overriding the three name attributes:

    * `name` is an identifier used for generating file names.
    * `localname` is the section title for the index.
    * `shortname` is a short name for the index, for use in the relation bar in
      HTML output.  Can be empty to disable entries in the relation bar.

    and providing a :meth:`generate()` method.  Then, add the index class to
    your domain's `indices` list.  Extensions can add indices to existing
    domains using :meth:`~sphinx.application.Sphinx.add_index_to_domain()`.
    """

    name = None  # type: unicode
    localname = None  # type: unicode
    shortname = None  # type: unicode

    def __init__(self, domain):
        # type: (Domain) -> None
        if self.name is None or self.localname is None:
            raise SphinxError('Index subclass %s has no valid name or localname'
                              % self.__class__.__name__)
        self.domain = domain

    def generate(self, docnames=None):
        # type: (Iterable[unicode]) -> Tuple[List[Tuple[unicode, List[List[Union[unicode, int]]]]], bool]  # NOQA
        """Return entries for the index given by *name*.  If *docnames* is
        given, restrict to entries referring to these docnames.

        The return value is a tuple of ``(content, collapse)``, where *collapse*
        is a boolean that determines if sub-entries should start collapsed (for
        output formats that support collapsing sub-entries).

        *content* is a sequence of ``(letter, entries)`` tuples, where *letter*
        is the "heading" for the given *entries*, usually the starting letter.

        *entries* is a sequence of single entries, where a single entry is a
        sequence ``[name, subtype, docname, anchor, extra, qualifier, descr]``.
        The items in this sequence have the following meaning:

        - `name` -- the name of the index entry to be displayed
        - `subtype` -- sub-entry related type:
          0 -- normal entry
          1 -- entry with sub-entries
          2 -- sub-entry
        - `docname` -- docname where the entry is located
        - `anchor` -- anchor for the entry within `docname`
        - `extra` -- extra info for the entry
        - `qualifier` -- qualifier for the description
        - `descr` -- description for the entry

        Qualifier and description are not rendered e.g. in LaTeX output.
        """
        raise NotImplementedError


class Domain(object):
    """
    A Domain is meant to be a group of "object" description directives for
    objects of a similar nature, and corresponding roles to create references to
    them.  Examples would be Python modules, classes, functions etc., elements
    of a templating language, Sphinx roles and directives, etc.

    Each domain has a separate storage for information about existing objects
    and how to reference them in `self.data`, which must be a dictionary.  It
    also must implement several functions that expose the object information in
    a uniform way to parts of Sphinx that allow the user to reference or search
    for objects in a domain-agnostic way.

    About `self.data`: since all object and cross-referencing information is
    stored on a BuildEnvironment instance, the `domain.data` object is also
    stored in the `env.domaindata` dict under the key `domain.name`.  Before the
    build process starts, every active domain is instantiated and given the
    environment object; the `domaindata` dict must then either be nonexistent or
    a dictionary whose 'version' key is equal to the domain class'
    :attr:`data_version` attribute.  Otherwise, `IOError` is raised and the
    pickled environment is discarded.
    """

    #: domain name: should be short, but unique
    name = ''
    #: domain label: longer, more descriptive (used in messages)
    label = ''
    #: type (usually directive) name -> ObjType instance
    object_types = {}       # type: Dict[unicode, ObjType]
    #: directive name -> directive class
    directives = {}         # type: Dict[unicode, Any]
    #: role name -> role callable
    roles = {}              # type: Dict[unicode, Union[RoleFunction, XRefRole]]
    #: a list of Index subclasses
    indices = []            # type: List[Type[Index]]
    #: role name -> a warning message if reference is missing
    dangling_warnings = {}  # type: Dict[unicode, unicode]
    #: node_class -> (enum_node_type, title_getter)
    enumerable_nodes = {}   # type: Dict[nodes.Node, Tuple[unicode, Callable]]

    #: data value for a fresh environment
    initial_data = {}       # type: Dict
    #: data value
    data = None             # type: Dict
    #: data version, bump this when the format of `self.data` changes
    data_version = 0

    def __init__(self, env):
        # type: (BuildEnvironment) -> None
        self.env = env              # type: BuildEnvironment
        self._role_cache = {}       # type: Dict[unicode, Callable]
        self._directive_cache = {}  # type: Dict[unicode, Callable]
        self._role2type = {}        # type: Dict[unicode, List[unicode]]
        self._type2role = {}        # type: Dict[unicode, unicode]

        # convert class variables to instance one (to enhance through API)
        self.object_types = dict(self.object_types)
        self.directives = dict(self.directives)
        self.roles = dict(self.roles)
        self.indices = list(self.indices)

        if self.name not in env.domaindata:
            assert isinstance(self.initial_data, dict)
            new_data = copy.deepcopy(self.initial_data)
            new_data['version'] = self.data_version
            self.data = env.domaindata[self.name] = new_data
        else:
            self.data = env.domaindata[self.name]
            if self.data['version'] != self.data_version:
                raise IOError('data of %r domain out of date' % self.label)
        for name, obj in iteritems(self.object_types):
            for rolename in obj.roles:
                self._role2type.setdefault(rolename, []).append(name)
            self._type2role[name] = obj.roles[0] if obj.roles else ''
        self.objtypes_for_role = self._role2type.get    # type: Callable[[unicode], List[unicode]]  # NOQA
        self.role_for_objtype = self._type2role.get     # type: Callable[[unicode], unicode]

    def add_object_type(self, name, objtype):
        # type: (unicode, ObjType) -> None
        """Add an object type."""
        self.object_types[name] = objtype
        if objtype.roles:
            self._type2role[name] = objtype.roles[0]
        else:
            self._type2role[name] = ''

        for role in objtype.roles:
            self._role2type.setdefault(role, []).append(name)

    def role(self, name):
        # type: (unicode) -> Callable
        """Return a role adapter function that always gives the registered
        role its full name ('domain:name') as the first argument.
        """
        if name in self._role_cache:
            return self._role_cache[name]
        if name not in self.roles:
            return None
        fullname = '%s:%s' % (self.name, name)

        def role_adapter(typ, rawtext, text, lineno, inliner, options={}, content=[]):
            # type: (unicode, unicode, unicode, int, Inliner, Dict, List[unicode]) -> nodes.Node  # NOQA
            return self.roles[name](fullname, rawtext, text, lineno,
                                    inliner, options, content)
        self._role_cache[name] = role_adapter
        return role_adapter

    def directive(self, name):
        # type: (unicode) -> Callable
        """Return a directive adapter class that always gives the registered
        directive its full name ('domain:name') as ``self.name``.
        """
        if name in self._directive_cache:
            return self._directive_cache[name]
        if name not in self.directives:
            return None
        fullname = '%s:%s' % (self.name, name)
        BaseDirective = self.directives[name]

        class DirectiveAdapter(BaseDirective):  # type: ignore
            def run(self):
                # type: () -> List[nodes.Node]
                self.name = fullname
                return BaseDirective.run(self)
        self._directive_cache[name] = DirectiveAdapter
        return DirectiveAdapter

    # methods that should be overwritten

    def clear_doc(self, docname):
        # type: (unicode) -> None
        """Remove traces of a document in the domain-specific inventories."""
        pass

    def merge_domaindata(self, docnames, otherdata):
        # type: (List[unicode], Dict) -> None
        """Merge in data regarding *docnames* from a different domaindata
        inventory (coming from a subprocess in parallel builds).
        """
        raise NotImplementedError('merge_domaindata must be implemented in %s '
                                  'to be able to do parallel builds!' %
                                  self.__class__)

    def process_doc(self, env, docname, document):
        # type: (BuildEnvironment, unicode, nodes.Node) -> None
        """Process a document after it is read by the environment."""
        pass

    def check_consistency(self):
        # type: () -> None
        """Do consistency checks (**experimental**)."""
        pass

    def process_field_xref(self, pnode):
        # type: (nodes.Node) -> None
        """Process a pending xref created in a doc field.
        For example, attach information about the current scope.
        """
        pass

    def resolve_xref(self, env, fromdocname, builder,
                     typ, target, node, contnode):
        # type: (BuildEnvironment, unicode, Builder, unicode, unicode, nodes.Node, nodes.Node) -> nodes.Node  # NOQA
        """Resolve the pending_xref *node* with the given *typ* and *target*.

        This method should return a new node, to replace the xref node,
        containing the *contnode* which is the markup content of the
        cross-reference.

        If no resolution can be found, None can be returned; the xref node will
        then given to the :event:`missing-reference` event, and if that yields no
        resolution, replaced by *contnode*.

        The method can also raise :exc:`sphinx.environment.NoUri` to suppress
        the :event:`missing-reference` event being emitted.
        """
        pass

    def resolve_any_xref(self, env, fromdocname, builder, target, node, contnode):
        # type: (BuildEnvironment, unicode, Builder, unicode, nodes.Node, nodes.Node) -> List[Tuple[unicode, nodes.Node]]  # NOQA
        """Resolve the pending_xref *node* with the given *target*.

        The reference comes from an "any" or similar role, which means that we
        don't know the type.  Otherwise, the arguments are the same as for
        :meth:`resolve_xref`.

        The method must return a list (potentially empty) of tuples
        ``('domain:role', newnode)``, where ``'domain:role'`` is the name of a
        role that could have created the same reference, e.g. ``'py:func'``.
        ``newnode`` is what :meth:`resolve_xref` would return.

        .. versionadded:: 1.3
        """
        raise NotImplementedError

    def get_objects(self):
        # type: () -> Iterable[Tuple[unicode, unicode, unicode, unicode, unicode, int]]
        """Return an iterable of "object descriptions", which are tuples with
        five items:

        * `name`     -- fully qualified name
        * `dispname` -- name to display when searching/linking
        * `type`     -- object type, a key in ``self.object_types``
        * `docname`  -- the document where it is to be found
        * `anchor`   -- the anchor name for the object
        * `priority` -- how "important" the object is (determines placement
          in search results)

          - 1: default priority (placed before full-text matches)
          - 0: object is important (placed before default-priority objects)
          - 2: object is unimportant (placed after full-text matches)
          - -1: object should not show up in search at all
        """
        return []

    def get_type_name(self, type, primary=False):
        # type: (ObjType, bool) -> unicode
        """Return full name for given ObjType."""
        if primary:
            return type.lname
        return _('%s %s') % (self.label, type.lname)

    def get_enumerable_node_type(self, node):
        # type: (nodes.Node) -> unicode
        """Get type of enumerable nodes (experimental)."""
        enum_node_type, _ = self.enumerable_nodes.get(node.__class__, (None, None))
        return enum_node_type

    def get_full_qualified_name(self, node):
        # type: (nodes.Node) -> unicode
        """Return full qualified name for given node."""
        return None
