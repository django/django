"""The reStructuredText domain."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, cast

from docutils.parsers.rst import directives

from sphinx import addnodes
from sphinx.directives import ObjectDescription
from sphinx.domains import Domain, ObjType
from sphinx.locale import _, __
from sphinx.roles import XRefRole
from sphinx.util import logging
from sphinx.util.nodes import make_id, make_refnode

if TYPE_CHECKING:
    from collections.abc import Iterator

    from docutils.nodes import Element

    from sphinx.addnodes import desc_signature, pending_xref
    from sphinx.application import Sphinx
    from sphinx.builders import Builder
    from sphinx.environment import BuildEnvironment
    from sphinx.util.typing import OptionSpec

logger = logging.getLogger(__name__)

dir_sig_re = re.compile(r'\.\. (.+?)::(.*)$')


class ReSTMarkup(ObjectDescription[str]):
    """
    Description of generic reST markup.
    """
    option_spec: OptionSpec = {
        'no-index': directives.flag,
        'no-index-entry': directives.flag,
        'no-contents-entry': directives.flag,
        'no-typesetting': directives.flag,
        'noindex': directives.flag,
        'noindexentry': directives.flag,
        'nocontentsentry': directives.flag,
    }

    def add_target_and_index(self, name: str, sig: str, signode: desc_signature) -> None:
        node_id = make_id(self.env, self.state.document, self.objtype, name)
        signode['ids'].append(node_id)
        self.state.document.note_explicit_target(signode)

        domain = cast(ReSTDomain, self.env.get_domain('rst'))
        domain.note_object(self.objtype, name, node_id, location=signode)

        if 'no-index-entry' not in self.options:
            indextext = self.get_index_text(self.objtype, name)
            if indextext:
                self.indexnode['entries'].append(('single', indextext, node_id, '', None))

    def get_index_text(self, objectname: str, name: str) -> str:
        return ''

    def _object_hierarchy_parts(self, sig_node: desc_signature) -> tuple[str, ...]:
        if 'fullname' not in sig_node:
            return ()
        directive_names = []
        for parent in self.env.ref_context.get('rst:directives', ()):
            directive_names += parent.split(':')
        name = sig_node['fullname']
        return tuple(directive_names + name.split(':'))

    def _toc_entry_name(self, sig_node: desc_signature) -> str:
        if not sig_node.get('_toc_parts'):
            return ''

        config = self.env.app.config
        objtype = sig_node.parent.get('objtype')
        *parents, name = sig_node['_toc_parts']
        if objtype == 'directive:option':
            return f':{name}:'
        if config.toc_object_entries_show_parents in {'domain', 'all'}:
            name = ':'.join(sig_node['_toc_parts'])
        if objtype == 'role':
            return f':{name}:'
        if objtype == 'directive':
            return f'.. {name}::'
        return ''


def parse_directive(d: str) -> tuple[str, str]:
    """Parse a directive signature.

    Returns (directive, arguments) string tuple.  If no arguments are given,
    returns (directive, '').
    """
    dir = d.strip()
    if not dir.startswith('.'):
        # Assume it is a directive without syntax
        return (dir, '')
    m = dir_sig_re.match(dir)
    if not m:
        return (dir, '')
    parsed_dir, parsed_args = m.groups()
    if parsed_args.strip():
        return (parsed_dir.strip(), ' ' + parsed_args.strip())
    else:
        return (parsed_dir.strip(), '')


class ReSTDirective(ReSTMarkup):
    """
    Description of a reST directive.
    """
    def handle_signature(self, sig: str, signode: desc_signature) -> str:
        name, args = parse_directive(sig)
        desc_name = f'.. {name}::'
        signode['fullname'] = name.strip()
        signode += addnodes.desc_name(desc_name, desc_name)
        if len(args) > 0:
            signode += addnodes.desc_addname(args, args)
        return name

    def get_index_text(self, objectname: str, name: str) -> str:
        return _('%s (directive)') % name

    def before_content(self) -> None:
        if self.names:
            directives = self.env.ref_context.setdefault('rst:directives', [])
            directives.append(self.names[0])

    def after_content(self) -> None:
        directives = self.env.ref_context.setdefault('rst:directives', [])
        if directives:
            directives.pop()


class ReSTDirectiveOption(ReSTMarkup):
    """
    Description of an option for reST directive.
    """
    option_spec: OptionSpec = ReSTMarkup.option_spec.copy()
    option_spec.update({
        'type': directives.unchanged,
    })

    def handle_signature(self, sig: str, signode: desc_signature) -> str:
        try:
            name, argument = re.split(r'\s*:\s+', sig.strip(), maxsplit=1)
        except ValueError:
            name, argument = sig, None

        desc_name = f':{name}:'
        signode['fullname'] = name.strip()
        signode += addnodes.desc_name(desc_name, desc_name)
        if argument:
            signode += addnodes.desc_annotation(' ' + argument, ' ' + argument)
        if self.options.get('type'):
            text = ' (%s)' % self.options['type']
            signode += addnodes.desc_annotation(text, text)
        return name

    def add_target_and_index(self, name: str, sig: str, signode: desc_signature) -> None:
        domain = cast(ReSTDomain, self.env.get_domain('rst'))

        directive_name = self.current_directive
        if directive_name:
            prefix = '-'.join([self.objtype, directive_name])
            objname = ':'.join([directive_name, name])
        else:
            prefix = self.objtype
            objname = name

        node_id = make_id(self.env, self.state.document, prefix, name)
        signode['ids'].append(node_id)
        self.state.document.note_explicit_target(signode)
        domain.note_object(self.objtype, objname, node_id, location=signode)

        if directive_name:
            key = name[0].upper()
            pair = [_('%s (directive)') % directive_name,
                    _(':%s: (directive option)') % name]
            self.indexnode['entries'].append(('pair', '; '.join(pair), node_id, '', key))
        else:
            key = name[0].upper()
            text = _(':%s: (directive option)') % name
            self.indexnode['entries'].append(('single', text, node_id, '', key))

    @property
    def current_directive(self) -> str:
        directives = self.env.ref_context.get('rst:directives')
        if directives:
            return directives[-1]
        else:
            return ''


class ReSTRole(ReSTMarkup):
    """
    Description of a reST role.
    """
    def handle_signature(self, sig: str, signode: desc_signature) -> str:
        desc_name = f':{sig}:'
        signode['fullname'] = sig.strip()
        signode += addnodes.desc_name(desc_name, desc_name)
        return sig

    def get_index_text(self, objectname: str, name: str) -> str:
        return _('%s (role)') % name


class ReSTDomain(Domain):
    """ReStructuredText domain."""
    name = 'rst'
    label = 'reStructuredText'

    object_types = {
        'directive':        ObjType(_('directive'),        'dir'),
        'directive:option': ObjType(_('directive-option'), 'dir'),
        'role':             ObjType(_('role'),             'role'),
    }
    directives = {
        'directive': ReSTDirective,
        'directive:option': ReSTDirectiveOption,
        'role':      ReSTRole,
    }
    roles = {
        'dir':  XRefRole(),
        'role': XRefRole(),
    }
    initial_data: dict[str, dict[tuple[str, str], str]] = {
        'objects': {},  # fullname -> docname, objtype
    }

    @property
    def objects(self) -> dict[tuple[str, str], tuple[str, str]]:
        return self.data.setdefault('objects', {})  # (objtype, fullname) -> (docname, node_id)

    def note_object(self, objtype: str, name: str, node_id: str, location: Any = None) -> None:
        if (objtype, name) in self.objects:
            docname, node_id = self.objects[objtype, name]
            logger.warning(__('duplicate description of %s %s, other instance in %s') %
                           (objtype, name, docname), location=location)

        self.objects[objtype, name] = (self.env.docname, node_id)

    def clear_doc(self, docname: str) -> None:
        for (typ, name), (doc, _node_id) in list(self.objects.items()):
            if doc == docname:
                del self.objects[typ, name]

    def merge_domaindata(self, docnames: list[str], otherdata: dict[str, Any]) -> None:
        # XXX check duplicates
        for (typ, name), (doc, node_id) in otherdata['objects'].items():
            if doc in docnames:
                self.objects[typ, name] = (doc, node_id)

    def resolve_xref(self, env: BuildEnvironment, fromdocname: str, builder: Builder,
                     typ: str, target: str, node: pending_xref, contnode: Element,
                     ) -> Element | None:
        objtypes = self.objtypes_for_role(typ)
        if not objtypes:
            return None
        for objtype in objtypes:
            result = self.objects.get((objtype, target))
            if result:
                todocname, node_id = result
                return make_refnode(builder, fromdocname, todocname, node_id,
                                    contnode, target + ' ' + objtype)
        return None

    def resolve_any_xref(self, env: BuildEnvironment, fromdocname: str, builder: Builder,
                         target: str, node: pending_xref, contnode: Element,
                         ) -> list[tuple[str, Element]]:
        results: list[tuple[str, Element]] = []
        for objtype in self.object_types:
            result = self.objects.get((objtype, target))
            if result:
                todocname, node_id = result
                results.append(
                    ('rst:' + self.role_for_objtype(objtype),  # type: ignore[operator]
                     make_refnode(builder, fromdocname, todocname, node_id,
                                  contnode, target + ' ' + objtype)))
        return results

    def get_objects(self) -> Iterator[tuple[str, str, str, str, str, int]]:
        for (typ, name), (docname, node_id) in self.data['objects'].items():
            yield name, name, typ, docname, node_id, 1


def setup(app: Sphinx) -> dict[str, Any]:
    app.add_domain(ReSTDomain)

    return {
        'version': 'builtin',
        'env_version': 2,
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
