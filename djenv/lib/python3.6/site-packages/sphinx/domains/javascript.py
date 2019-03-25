# -*- coding: utf-8 -*-
"""
    sphinx.domains.javascript
    ~~~~~~~~~~~~~~~~~~~~~~~~~

    The JavaScript domain.

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from docutils import nodes
from docutils.parsers.rst import directives

from sphinx import addnodes
from sphinx.directives import ObjectDescription
from sphinx.domains import Domain, ObjType
from sphinx.domains.python import _pseudo_parse_arglist
from sphinx.locale import _
from sphinx.roles import XRefRole
from sphinx.util.docfields import Field, GroupedField, TypedField
from sphinx.util.docutils import SphinxDirective
from sphinx.util.nodes import make_refnode

if False:
    # For type annotation
    from typing import Any, Dict, Iterator, List, Tuple  # NOQA
    from docutils import nodes  # NOQA
    from sphinx.application import Sphinx  # NOQA
    from sphinx.builders import Builder  # NOQA
    from sphinx.environment import BuildEnvironment  # NOQA


class JSObject(ObjectDescription):
    """
    Description of a JavaScript object.
    """
    #: If set to ``True`` this object is callable and a `desc_parameterlist` is
    #: added
    has_arguments = False

    #: what is displayed right before the documentation entry
    display_prefix = None  # type: unicode

    #: If ``allow_nesting`` is ``True``, the object prefixes will be accumulated
    #: based on directive nesting
    allow_nesting = False

    def handle_signature(self, sig, signode):
        # type: (unicode, addnodes.desc_signature) -> Tuple[unicode, unicode]
        """Breaks down construct signatures

        Parses out prefix and argument list from construct definition. The
        namespace and class will be determined by the nesting of domain
        directives.
        """
        sig = sig.strip()
        if '(' in sig and sig[-1:] == ')':
            member, arglist = sig.split('(', 1)
            member = member.strip()
            arglist = arglist[:-1].strip()
        else:
            member = sig
            arglist = None
        # If construct is nested, prefix the current prefix
        prefix = self.env.ref_context.get('js:object', None)
        mod_name = self.env.ref_context.get('js:module')
        name = member
        try:
            member_prefix, member_name = member.rsplit('.', 1)
        except ValueError:
            member_name = name
            member_prefix = ''
        finally:
            name = member_name
            if prefix and member_prefix:
                prefix = '.'.join([prefix, member_prefix])
            elif prefix is None and member_prefix:
                prefix = member_prefix
        fullname = name
        if prefix:
            fullname = '.'.join([prefix, name])

        signode['module'] = mod_name
        signode['object'] = prefix
        signode['fullname'] = fullname

        if self.display_prefix:
            signode += addnodes.desc_annotation(self.display_prefix,
                                                self.display_prefix)
        if prefix:
            signode += addnodes.desc_addname(prefix + '.', prefix + '.')
        elif mod_name:
            signode += addnodes.desc_addname(mod_name + '.', mod_name + '.')
        signode += addnodes.desc_name(name, name)
        if self.has_arguments:
            if not arglist:
                signode += addnodes.desc_parameterlist()
            else:
                _pseudo_parse_arglist(signode, arglist)
        return fullname, prefix

    def add_target_and_index(self, name_obj, sig, signode):
        # type: (Tuple[unicode, unicode], unicode, addnodes.desc_signature) -> None
        mod_name = self.env.ref_context.get('js:module')
        fullname = (mod_name and mod_name + '.' or '') + name_obj[0]
        if fullname not in self.state.document.ids:
            signode['names'].append(fullname)
            signode['ids'].append(fullname.replace('$', '_S_'))
            signode['first'] = not self.names
            self.state.document.note_explicit_target(signode)
            objects = self.env.domaindata['js']['objects']
            if fullname in objects:
                self.state_machine.reporter.warning(
                    'duplicate object description of %s, ' % fullname +
                    'other instance in ' +
                    self.env.doc2path(objects[fullname][0]),
                    line=self.lineno)
            objects[fullname] = self.env.docname, self.objtype

        indextext = self.get_index_text(mod_name, name_obj)
        if indextext:
            self.indexnode['entries'].append(('single', indextext,
                                              fullname.replace('$', '_S_'),
                                              '', None))

    def get_index_text(self, objectname, name_obj):
        # type: (unicode, Tuple[unicode, unicode]) -> unicode
        name, obj = name_obj
        if self.objtype == 'function':
            if not obj:
                return _('%s() (built-in function)') % name
            return _('%s() (%s method)') % (name, obj)
        elif self.objtype == 'class':
            return _('%s() (class)') % name
        elif self.objtype == 'data':
            return _('%s (global variable or constant)') % name
        elif self.objtype == 'attribute':
            return _('%s (%s attribute)') % (name, obj)
        return ''

    def before_content(self):
        # type: () -> None
        """Handle object nesting before content

        :py:class:`JSObject` represents JavaScript language constructs. For
        constructs that are nestable, this method will build up a stack of the
        nesting heirarchy so that it can be later de-nested correctly, in
        :py:meth:`after_content`.

        For constructs that aren't nestable, the stack is bypassed, and instead
        only the most recent object is tracked. This object prefix name will be
        removed with :py:meth:`after_content`.

        The following keys are used in ``self.env.ref_context``:

            js:objects
                Stores the object prefix history. With each nested element, we
                add the object prefix to this list. When we exit that object's
                nesting level, :py:meth:`after_content` is triggered and the
                prefix is removed from the end of the list.

            js:object
                Current object prefix. This should generally reflect the last
                element in the prefix history
        """
        prefix = None
        if self.names:
            (obj_name, obj_name_prefix) = self.names.pop()
            prefix = obj_name_prefix.strip('.') if obj_name_prefix else None
            if self.allow_nesting:
                prefix = obj_name
        if prefix:
            self.env.ref_context['js:object'] = prefix
            if self.allow_nesting:
                objects = self.env.ref_context.setdefault('js:objects', [])
                objects.append(prefix)

    def after_content(self):
        # type: () -> None
        """Handle object de-nesting after content

        If this class is a nestable object, removing the last nested class prefix
        ends further nesting in the object.

        If this class is not a nestable object, the list of classes should not
        be altered as we didn't affect the nesting levels in
        :py:meth:`before_content`.
        """
        objects = self.env.ref_context.setdefault('js:objects', [])
        if self.allow_nesting:
            try:
                objects.pop()
            except IndexError:
                pass
        self.env.ref_context['js:object'] = (objects[-1] if len(objects) > 0
                                             else None)


class JSCallable(JSObject):
    """Description of a JavaScript function, method or constructor."""
    has_arguments = True

    doc_field_types = [
        TypedField('arguments', label=_('Arguments'),
                   names=('argument', 'arg', 'parameter', 'param'),
                   typerolename='func', typenames=('paramtype', 'type')),
        GroupedField('errors', label=_('Throws'), rolename='err',
                     names=('throws', ),
                     can_collapse=True),
        Field('returnvalue', label=_('Returns'), has_arg=False,
              names=('returns', 'return')),
        Field('returntype', label=_('Return type'), has_arg=False,
              names=('rtype',)),
    ]


class JSConstructor(JSCallable):
    """Like a callable but with a different prefix."""
    display_prefix = 'class '
    allow_nesting = True


class JSModule(SphinxDirective):
    """
    Directive to mark description of a new JavaScript module.

    This directive specifies the module name that will be used by objects that
    follow this directive.

    Options
    -------

    noindex
        If the ``noindex`` option is specified, no linkable elements will be
        created, and the module won't be added to the global module index. This
        is useful for splitting up the module definition across multiple
        sections or files.

    :param mod_name: Module name
    """

    has_content = False
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = False
    option_spec = {
        'noindex': directives.flag
    }

    def run(self):
        # type: () -> List[nodes.Node]
        mod_name = self.arguments[0].strip()
        self.env.ref_context['js:module'] = mod_name
        noindex = 'noindex' in self.options
        ret = []
        if not noindex:
            self.env.domaindata['js']['modules'][mod_name] = self.env.docname
            # Make a duplicate entry in 'objects' to facilitate searching for
            # the module in JavaScriptDomain.find_obj()
            self.env.domaindata['js']['objects'][mod_name] = (self.env.docname, 'module')
            targetnode = nodes.target('', '', ids=['module-' + mod_name],
                                      ismod=True)
            self.state.document.note_explicit_target(targetnode)
            ret.append(targetnode)
            indextext = _('%s (module)') % mod_name
            inode = addnodes.index(entries=[('single', indextext,
                                             'module-' + mod_name, '', None)])
            ret.append(inode)
        return ret


class JSXRefRole(XRefRole):
    def process_link(self, env, refnode, has_explicit_title, title, target):
        # type: (BuildEnvironment, nodes.Node, bool, unicode, unicode) -> Tuple[unicode, unicode]  # NOQA
        # basically what sphinx.domains.python.PyXRefRole does
        refnode['js:object'] = env.ref_context.get('js:object')
        refnode['js:module'] = env.ref_context.get('js:module')
        if not has_explicit_title:
            title = title.lstrip('.')
            target = target.lstrip('~')
            if title[0:1] == '~':
                title = title[1:]
                dot = title.rfind('.')
                if dot != -1:
                    title = title[dot + 1:]
        if target[0:1] == '.':
            target = target[1:]
            refnode['refspecific'] = True
        return title, target


class JavaScriptDomain(Domain):
    """JavaScript language domain."""
    name = 'js'
    label = 'JavaScript'
    # if you add a new object type make sure to edit JSObject.get_index_string
    object_types = {
        'function':  ObjType(_('function'),  'func'),
        'method':    ObjType(_('method'),    'meth'),
        'class':     ObjType(_('class'),     'class'),
        'data':      ObjType(_('data'),      'data'),
        'attribute': ObjType(_('attribute'), 'attr'),
        'module':    ObjType(_('module'),    'mod'),
    }
    directives = {
        'function':  JSCallable,
        'method':    JSCallable,
        'class':     JSConstructor,
        'data':      JSObject,
        'attribute': JSObject,
        'module':    JSModule,
    }
    roles = {
        'func':  JSXRefRole(fix_parens=True),
        'meth':  JSXRefRole(fix_parens=True),
        'class': JSXRefRole(fix_parens=True),
        'data':  JSXRefRole(),
        'attr':  JSXRefRole(),
        'mod':   JSXRefRole(),
    }
    initial_data = {
        'objects': {},  # fullname -> docname, objtype
        'modules': {},  # mod_name -> docname
    }  # type: Dict[unicode, Dict[unicode, Tuple[unicode, unicode]]]

    def clear_doc(self, docname):
        # type: (unicode) -> None
        for fullname, (pkg_docname, _l) in list(self.data['objects'].items()):
            if pkg_docname == docname:
                del self.data['objects'][fullname]
        for mod_name, pkg_docname in list(self.data['modules'].items()):
            if pkg_docname == docname:
                del self.data['modules'][mod_name]

    def merge_domaindata(self, docnames, otherdata):
        # type: (List[unicode], Dict) -> None
        # XXX check duplicates
        for fullname, (fn, objtype) in otherdata['objects'].items():
            if fn in docnames:
                self.data['objects'][fullname] = (fn, objtype)
        for mod_name, pkg_docname in otherdata['modules'].items():
            if pkg_docname in docnames:
                self.data['modules'][mod_name] = pkg_docname

    def find_obj(self, env, mod_name, prefix, name, typ, searchorder=0):
        # type: (BuildEnvironment, unicode, unicode, unicode, unicode, int) -> Tuple[unicode, Tuple[unicode, unicode]]  # NOQA
        if name[-2:] == '()':
            name = name[:-2]
        objects = self.data['objects']

        searches = []
        if mod_name and prefix:
            searches.append('.'.join([mod_name, prefix, name]))
        if mod_name:
            searches.append('.'.join([mod_name, name]))
        if prefix:
            searches.append('.'.join([prefix, name]))
        searches.append(name)

        if searchorder == 0:
            searches.reverse()

        newname = None
        for search_name in searches:
            if search_name in objects:
                newname = search_name

        return newname, objects.get(newname)

    def resolve_xref(self, env, fromdocname, builder, typ, target, node,
                     contnode):
        # type: (BuildEnvironment, unicode, Builder, unicode, unicode, nodes.Node, nodes.Node) -> nodes.Node  # NOQA
        mod_name = node.get('js:module')
        prefix = node.get('js:object')
        searchorder = node.hasattr('refspecific') and 1 or 0
        name, obj = self.find_obj(env, mod_name, prefix, target, typ, searchorder)
        if not obj:
            return None
        return make_refnode(builder, fromdocname, obj[0],
                            name.replace('$', '_S_'), contnode, name)

    def resolve_any_xref(self, env, fromdocname, builder, target, node,
                         contnode):
        # type: (BuildEnvironment, unicode, Builder, unicode, nodes.Node, nodes.Node) -> List[Tuple[unicode, nodes.Node]]  # NOQA
        mod_name = node.get('js:module')
        prefix = node.get('js:object')
        name, obj = self.find_obj(env, mod_name, prefix, target, None, 1)
        if not obj:
            return []
        return [('js:' + self.role_for_objtype(obj[1]),
                 make_refnode(builder, fromdocname, obj[0],
                              name.replace('$', '_S_'), contnode, name))]

    def get_objects(self):
        # type: () -> Iterator[Tuple[unicode, unicode, unicode, unicode, unicode, int]]
        for refname, (docname, type) in list(self.data['objects'].items()):
            yield refname, refname, type, docname, \
                refname.replace('$', '_S_'), 1

    def get_full_qualified_name(self, node):
        # type: (nodes.Node) -> unicode
        modname = node.get('js:module')
        prefix = node.get('js:object')
        target = node.get('reftarget')
        if target is None:
            return None
        else:
            return '.'.join(filter(None, [modname, prefix, target]))


def setup(app):
    # type: (Sphinx) -> Dict[unicode, Any]
    app.add_domain(JavaScriptDomain)

    return {
        'version': 'builtin',
        'env_version': 1,
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
