# -*- coding: utf-8 -*-
"""
    sphinx.domains.c
    ~~~~~~~~~~~~~~~~

    The C language domain.

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re
import string

from docutils import nodes

from sphinx import addnodes
from sphinx.directives import ObjectDescription
from sphinx.domains import Domain, ObjType
from sphinx.locale import _
from sphinx.roles import XRefRole
from sphinx.util.docfields import Field, TypedField
from sphinx.util.nodes import make_refnode

if False:
    # For type annotation
    from typing import Any, Dict, Iterator, List, Tuple  # NOQA
    from sphinx.application import Sphinx  # NOQA
    from sphinx.builders import Builder  # NOQA
    from sphinx.environment import BuildEnvironment  # NOQA


# RE to split at word boundaries
wsplit_re = re.compile(r'(\W+)')

# REs for C signatures
c_sig_re = re.compile(
    r'''^([^(]*?)          # return type
        ([\w:.]+)  \s*     # thing name (colon allowed for C++)
        (?: \((.*)\) )?    # optionally arguments
        (\s+const)? $      # const specifier
    ''', re.VERBOSE)
c_funcptr_sig_re = re.compile(
    r'''^([^(]+?)          # return type
        (\( [^()]+ \)) \s* # name in parentheses
        \( (.*) \)         # arguments
        (\s+const)? $      # const specifier
    ''', re.VERBOSE)
c_funcptr_arg_sig_re = re.compile(
    r'''^\s*([^(,]+?)      # return type
        \( ([^()]+) \) \s* # name in parentheses
        \( (.*) \)         # arguments
        (\s+const)?        # const specifier
        \s*(?=$|,)         # end with comma or end of string
    ''', re.VERBOSE)
c_funcptr_name_re = re.compile(r'^\(\s*\*\s*(.*?)\s*\)$')


class CObject(ObjectDescription):
    """
    Description of a C language object.
    """

    doc_field_types = [
        TypedField('parameter', label=_('Parameters'),
                   names=('param', 'parameter', 'arg', 'argument'),
                   typerolename='type', typenames=('type',)),
        Field('returnvalue', label=_('Returns'), has_arg=False,
              names=('returns', 'return')),
        Field('returntype', label=_('Return type'), has_arg=False,
              names=('rtype',)),
    ]

    # These C types aren't described anywhere, so don't try to create
    # a cross-reference to them
    stopwords = set((
        'const', 'void', 'char', 'wchar_t', 'int', 'short',
        'long', 'float', 'double', 'unsigned', 'signed', 'FILE',
        'clock_t', 'time_t', 'ptrdiff_t', 'size_t', 'ssize_t',
        'struct', '_Bool',
    ))

    def _parse_type(self, node, ctype):
        # type: (nodes.Node, unicode) -> None
        # add cross-ref nodes for all words
        for part in [_f for _f in wsplit_re.split(ctype) if _f]:
            tnode = nodes.Text(part, part)
            if part[0] in string.ascii_letters + '_' and \
               part not in self.stopwords:
                pnode = addnodes.pending_xref(
                    '', refdomain='c', reftype='type', reftarget=part,
                    modname=None, classname=None)
                pnode += tnode
                node += pnode
            else:
                node += tnode

    def _parse_arglist(self, arglist):
        # type: (unicode) -> Iterator[unicode]
        while True:
            m = c_funcptr_arg_sig_re.match(arglist)
            if m:
                yield m.group()
                arglist = c_funcptr_arg_sig_re.sub('', arglist)
                if ',' in arglist:
                    _, arglist = arglist.split(',', 1)
                else:
                    break
            else:
                if ',' in arglist:
                    arg, arglist = arglist.split(',', 1)
                    yield arg
                else:
                    yield arglist
                    break

    def handle_signature(self, sig, signode):
        # type: (unicode, addnodes.desc_signature) -> unicode
        """Transform a C signature into RST nodes."""
        # first try the function pointer signature regex, it's more specific
        m = c_funcptr_sig_re.match(sig)
        if m is None:
            m = c_sig_re.match(sig)
        if m is None:
            raise ValueError('no match')
        rettype, name, arglist, const = m.groups()

        signode += addnodes.desc_type('', '')
        self._parse_type(signode[-1], rettype)
        try:
            classname, funcname = name.split('::', 1)
            classname += '::'
            signode += addnodes.desc_addname(classname, classname)
            signode += addnodes.desc_name(funcname, funcname)
            # name (the full name) is still both parts
        except ValueError:
            signode += addnodes.desc_name(name, name)
        # clean up parentheses from canonical name
        m = c_funcptr_name_re.match(name)
        if m:
            name = m.group(1)

        typename = self.env.ref_context.get('c:type')
        if self.name == 'c:member' and typename:
            fullname = typename + '.' + name
        else:
            fullname = name

        if not arglist:
            if self.objtype == 'function' or \
                    self.objtype == 'macro' and sig.rstrip().endswith('()'):
                # for functions, add an empty parameter list
                signode += addnodes.desc_parameterlist()
            if const:
                signode += addnodes.desc_addname(const, const)
            return fullname

        paramlist = addnodes.desc_parameterlist()
        arglist = arglist.replace('`', '').replace('\\ ', '')  # remove markup
        # this messes up function pointer types, but not too badly ;)
        for arg in self._parse_arglist(arglist):
            arg = arg.strip()
            param = addnodes.desc_parameter('', '', noemph=True)
            try:
                m = c_funcptr_arg_sig_re.match(arg)
                if m:
                    self._parse_type(param, m.group(1) + '(')
                    param += nodes.emphasis(m.group(2), m.group(2))
                    self._parse_type(param, ')(' + m.group(3) + ')')
                    if m.group(4):
                        param += addnodes.desc_addname(m.group(4), m.group(4))
                else:
                    ctype, argname = arg.rsplit(' ', 1)
                    self._parse_type(param, ctype)
                    # separate by non-breaking space in the output
                    param += nodes.emphasis(' ' + argname, u'\xa0' + argname)
            except ValueError:
                # no argument name given, only the type
                self._parse_type(param, arg)
            paramlist += param
        signode += paramlist
        if const:
            signode += addnodes.desc_addname(const, const)
        return fullname

    def get_index_text(self, name):
        # type: (unicode) -> unicode
        if self.objtype == 'function':
            return _('%s (C function)') % name
        elif self.objtype == 'member':
            return _('%s (C member)') % name
        elif self.objtype == 'macro':
            return _('%s (C macro)') % name
        elif self.objtype == 'type':
            return _('%s (C type)') % name
        elif self.objtype == 'var':
            return _('%s (C variable)') % name
        else:
            return ''

    def add_target_and_index(self, name, sig, signode):
        # type: (unicode, unicode, addnodes.desc_signature) -> None
        # for C API items we add a prefix since names are usually not qualified
        # by a module name and so easily clash with e.g. section titles
        targetname = 'c.' + name
        if targetname not in self.state.document.ids:
            signode['names'].append(targetname)
            signode['ids'].append(targetname)
            signode['first'] = (not self.names)
            self.state.document.note_explicit_target(signode)
            inv = self.env.domaindata['c']['objects']
            if name in inv:
                self.state_machine.reporter.warning(
                    'duplicate C object description of %s, ' % name +
                    'other instance in ' + self.env.doc2path(inv[name][0]),
                    line=self.lineno)
            inv[name] = (self.env.docname, self.objtype)

        indextext = self.get_index_text(name)
        if indextext:
            self.indexnode['entries'].append(('single', indextext,
                                              targetname, '', None))

    def before_content(self):
        # type: () -> None
        self.typename_set = False
        if self.name == 'c:type':
            if self.names:
                self.env.ref_context['c:type'] = self.names[0]
                self.typename_set = True

    def after_content(self):
        # type: () -> None
        if self.typename_set:
            self.env.ref_context.pop('c:type', None)


class CXRefRole(XRefRole):
    def process_link(self, env, refnode, has_explicit_title, title, target):
        # type: (BuildEnvironment, nodes.Node, bool, unicode, unicode) -> Tuple[unicode, unicode]  # NOQA
        if not has_explicit_title:
            target = target.lstrip('~')  # only has a meaning for the title
            # if the first character is a tilde, don't display the module/class
            # parts of the contents
            if title[0:1] == '~':
                title = title[1:]
                dot = title.rfind('.')
                if dot != -1:
                    title = title[dot + 1:]
        return title, target


class CDomain(Domain):
    """C language domain."""
    name = 'c'
    label = 'C'
    object_types = {
        'function': ObjType(_('function'), 'func'),
        'member':   ObjType(_('member'),   'member'),
        'macro':    ObjType(_('macro'),    'macro'),
        'type':     ObjType(_('type'),     'type'),
        'var':      ObjType(_('variable'), 'data'),
    }

    directives = {
        'function': CObject,
        'member':   CObject,
        'macro':    CObject,
        'type':     CObject,
        'var':      CObject,
    }
    roles = {
        'func':   CXRefRole(fix_parens=True),
        'member': CXRefRole(),
        'macro':  CXRefRole(),
        'data':   CXRefRole(),
        'type':   CXRefRole(),
    }
    initial_data = {
        'objects': {},  # fullname -> docname, objtype
    }  # type: Dict[unicode, Dict[unicode, Tuple[unicode, Any]]]

    def clear_doc(self, docname):
        # type: (unicode) -> None
        for fullname, (fn, _l) in list(self.data['objects'].items()):
            if fn == docname:
                del self.data['objects'][fullname]

    def merge_domaindata(self, docnames, otherdata):
        # type: (List[unicode], Dict) -> None
        # XXX check duplicates
        for fullname, (fn, objtype) in otherdata['objects'].items():
            if fn in docnames:
                self.data['objects'][fullname] = (fn, objtype)

    def resolve_xref(self, env, fromdocname, builder,
                     typ, target, node, contnode):
        # type: (BuildEnvironment, unicode, Builder, unicode, unicode, nodes.Node, nodes.Node) -> nodes.Node  # NOQA
        # strip pointer asterisk
        target = target.rstrip(' *')
        # becase TypedField can generate xrefs
        if target in CObject.stopwords:
            return contnode
        if target not in self.data['objects']:
            return None
        obj = self.data['objects'][target]
        return make_refnode(builder, fromdocname, obj[0], 'c.' + target,
                            contnode, target)

    def resolve_any_xref(self, env, fromdocname, builder, target,
                         node, contnode):
        # type: (BuildEnvironment, unicode, Builder, unicode, nodes.Node, nodes.Node) -> List[Tuple[unicode, nodes.Node]]  # NOQA
        # strip pointer asterisk
        target = target.rstrip(' *')
        if target not in self.data['objects']:
            return []
        obj = self.data['objects'][target]
        return [('c:' + self.role_for_objtype(obj[1]),
                 make_refnode(builder, fromdocname, obj[0], 'c.' + target,
                              contnode, target))]

    def get_objects(self):
        # type: () -> Iterator[Tuple[unicode, unicode, unicode, unicode, unicode, int]]
        for refname, (docname, type) in list(self.data['objects'].items()):
            yield (refname, refname, type, docname, 'c.' + refname, 1)


def setup(app):
    # type: (Sphinx) -> Dict[unicode, Any]
    app.add_domain(CDomain)

    return {
        'version': 'builtin',
        'env_version': 1,
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
