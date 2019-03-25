# -*- coding: utf-8 -*-
"""
    sphinx.domains.std
    ~~~~~~~~~~~~~~~~~~

    The standard domain.

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re
import unicodedata
import warnings
from copy import copy

from docutils import nodes
from docutils.parsers.rst import directives
from docutils.statemachine import ViewList
from six import iteritems

from sphinx import addnodes
from sphinx.deprecation import RemovedInSphinx30Warning
from sphinx.directives import ObjectDescription
from sphinx.domains import Domain, ObjType
from sphinx.locale import _, __
from sphinx.roles import XRefRole
from sphinx.util import ws_re, logging, docname_join
from sphinx.util.docutils import SphinxDirective
from sphinx.util.nodes import clean_astext, make_refnode

if False:
    # For type annotation
    from typing import Any, Callable, Dict, Iterator, List, Tuple, Type, Union  # NOQA
    from docutils.parsers.rst import Directive  # NOQA
    from sphinx.application import Sphinx  # NOQA
    from sphinx.builders import Builder  # NOQA
    from sphinx.environment import BuildEnvironment  # NOQA
    from sphinx.util.typing import RoleFunction  # NOQA

logger = logging.getLogger(__name__)


# RE for option descriptions
option_desc_re = re.compile(r'((?:/|--|-|\+)?[^\s=]+)(=?\s*.*)')
# RE for grammar tokens
token_re = re.compile(r'`(\w+)`', re.U)


class GenericObject(ObjectDescription):
    """
    A generic x-ref directive registered with Sphinx.add_object_type().
    """
    indextemplate = ''  # type: unicode
    parse_node = None  # type: Callable[[GenericObject, BuildEnvironment, unicode, addnodes.desc_signature], unicode]  # NOQA

    def handle_signature(self, sig, signode):
        # type: (unicode, addnodes.desc_signature) -> unicode
        if self.parse_node:
            name = self.parse_node(self.env, sig, signode)
        else:
            signode.clear()
            signode += addnodes.desc_name(sig, sig)
            # normalize whitespace like XRefRole does
            name = ws_re.sub('', sig)
        return name

    def add_target_and_index(self, name, sig, signode):
        # type: (unicode, unicode, addnodes.desc_signature) -> None
        targetname = '%s-%s' % (self.objtype, name)
        signode['ids'].append(targetname)
        self.state.document.note_explicit_target(signode)
        if self.indextemplate:
            colon = self.indextemplate.find(':')
            if colon != -1:
                indextype = self.indextemplate[:colon].strip()
                indexentry = self.indextemplate[colon + 1:].strip() % (name,)
            else:
                indextype = 'single'
                indexentry = self.indextemplate % (name,)
            self.indexnode['entries'].append((indextype, indexentry,
                                              targetname, '', None))
        self.env.domaindata['std']['objects'][self.objtype, name] = \
            self.env.docname, targetname


class EnvVar(GenericObject):
    indextemplate = _('environment variable; %s')


class EnvVarXRefRole(XRefRole):
    """
    Cross-referencing role for environment variables (adds an index entry).
    """

    def result_nodes(self, document, env, node, is_ref):
        # type: (nodes.Node, BuildEnvironment, nodes.Node, bool) -> Tuple[List[nodes.Node], List[nodes.Node]]  # NOQA
        if not is_ref:
            return [node], []
        varname = node['reftarget']
        tgtid = 'index-%s' % env.new_serialno('index')
        indexnode = addnodes.index()
        indexnode['entries'] = [
            ('single', varname, tgtid, '', None),
            ('single', _('environment variable; %s') % varname, tgtid, '', None)
        ]
        targetnode = nodes.target('', '', ids=[tgtid])
        document.note_explicit_target(targetnode)
        return [indexnode, targetnode, node], []


class Target(SphinxDirective):
    """
    Generic target for user-defined cross-reference types.
    """
    indextemplate = ''

    has_content = False
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = True
    option_spec = {}  # type: Dict

    def run(self):
        # type: () -> List[nodes.Node]
        # normalize whitespace in fullname like XRefRole does
        fullname = ws_re.sub(' ', self.arguments[0].strip())
        targetname = '%s-%s' % (self.name, fullname)
        node = nodes.target('', '', ids=[targetname])
        self.state.document.note_explicit_target(node)
        ret = [node]
        if self.indextemplate:
            indexentry = self.indextemplate % (fullname,)
            indextype = 'single'
            colon = indexentry.find(':')
            if colon != -1:
                indextype = indexentry[:colon].strip()
                indexentry = indexentry[colon + 1:].strip()
            inode = addnodes.index(entries=[(indextype, indexentry,
                                             targetname, '', None)])
            ret.insert(0, inode)
        name = self.name
        if ':' in self.name:
            _, name = self.name.split(':', 1)
        self.env.domaindata['std']['objects'][name, fullname] = \
            self.env.docname, targetname
        return ret


class Cmdoption(ObjectDescription):
    """
    Description of a command-line option (.. option).
    """

    def handle_signature(self, sig, signode):
        # type: (unicode, addnodes.desc_signature) -> unicode
        """Transform an option description into RST nodes."""
        count = 0
        firstname = ''  # type: unicode
        for potential_option in sig.split(', '):
            potential_option = potential_option.strip()
            m = option_desc_re.match(potential_option)
            if not m:
                logger.warning(__('Malformed option description %r, should '
                                  'look like "opt", "-opt args", "--opt args", '
                                  '"/opt args" or "+opt args"'), potential_option,
                               location=(self.env.docname, self.lineno))
                continue
            optname, args = m.groups()
            if count:
                signode += addnodes.desc_addname(', ', ', ')
            signode += addnodes.desc_name(optname, optname)
            signode += addnodes.desc_addname(args, args)
            if not count:
                firstname = optname
                signode['allnames'] = [optname]
            else:
                signode['allnames'].append(optname)
            count += 1
        if not firstname:
            raise ValueError
        return firstname

    def add_target_and_index(self, firstname, sig, signode):
        # type: (unicode, unicode, addnodes.desc_signature) -> None
        currprogram = self.env.ref_context.get('std:program')
        for optname in signode.get('allnames', []):
            targetname = optname.replace('/', '-')
            if not targetname.startswith('-'):
                targetname = '-arg-' + targetname
            if currprogram:
                targetname = '-' + currprogram + targetname
            targetname = 'cmdoption' + targetname
            signode['names'].append(targetname)

        self.state.document.note_explicit_target(signode)
        for optname in signode.get('allnames', []):
            self.env.domaindata['std']['progoptions'][currprogram, optname] = \
                self.env.docname, signode['ids'][0]
            # create only one index entry for the whole option
            if optname == firstname:
                self.indexnode['entries'].append(
                    ('pair', _('%scommand line option; %s') %
                     ((currprogram and currprogram + ' ' or ''), sig),
                     signode['ids'][0], '', None))


class Program(SphinxDirective):
    """
    Directive to name the program for which options are documented.
    """

    has_content = False
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = True
    option_spec = {}  # type: Dict

    def run(self):
        # type: () -> List[nodes.Node]
        program = ws_re.sub('-', self.arguments[0].strip())
        if program == 'None':
            self.env.ref_context.pop('std:program', None)
        else:
            self.env.ref_context['std:program'] = program
        return []


class OptionXRefRole(XRefRole):
    def process_link(self, env, refnode, has_explicit_title, title, target):
        # type: (BuildEnvironment, nodes.Node, bool, unicode, unicode) -> Tuple[unicode, unicode]  # NOQA
        refnode['std:program'] = env.ref_context.get('std:program')
        return title, target


def split_term_classifiers(line):
    # type: (unicode) -> List[Union[unicode, None]]
    # split line into a term and classifiers. if no classifier, None is used..
    parts = re.split(' +: +', line) + [None]
    return parts


def make_glossary_term(env, textnodes, index_key, source, lineno, new_id=None):
    # type: (BuildEnvironment, List[nodes.Node], unicode, unicode, int, unicode) -> nodes.term
    # get a text-only representation of the term and register it
    # as a cross-reference target
    term = nodes.term('', '', *textnodes)
    term.source = source
    term.line = lineno

    gloss_entries = env.temp_data.setdefault('gloss_entries', set())
    objects = env.domaindata['std']['objects']

    termtext = term.astext()
    if new_id is None:
        new_id = nodes.make_id('term-' + termtext)
    if new_id in gloss_entries:
        new_id = 'term-' + str(len(gloss_entries))
    gloss_entries.add(new_id)
    objects['term', termtext.lower()] = env.docname, new_id

    # add an index entry too
    indexnode = addnodes.index()
    indexnode['entries'] = [('single', termtext, new_id, 'main', index_key)]
    indexnode.source, indexnode.line = term.source, term.line
    term.append(indexnode)
    term['ids'].append(new_id)
    term['names'].append(new_id)

    return term


class Glossary(SphinxDirective):
    """
    Directive to create a glossary with cross-reference targets for :term:
    roles.
    """

    has_content = True
    required_arguments = 0
    optional_arguments = 0
    final_argument_whitespace = False
    option_spec = {
        'sorted': directives.flag,
    }

    def run(self):
        # type: () -> List[nodes.Node]
        node = addnodes.glossary()
        node.document = self.state.document

        # This directive implements a custom format of the reST definition list
        # that allows multiple lines of terms before the definition.  This is
        # easy to parse since we know that the contents of the glossary *must
        # be* a definition list.

        # first, collect single entries
        entries = []  # type: List[Tuple[List[Tuple[unicode, unicode, int]], ViewList]]
        in_definition = True
        was_empty = True
        messages = []
        for line, (source, lineno) in zip(self.content, self.content.items):
            # empty line -> add to last definition
            if not line:
                if in_definition and entries:
                    entries[-1][1].append('', source, lineno)
                was_empty = True
                continue
            # unindented line -> a term
            if line and not line[0].isspace():
                # enable comments
                if line.startswith('.. '):
                    continue
                # first term of definition
                if in_definition:
                    if not was_empty:
                        messages.append(self.state.reporter.system_message(
                            2, 'glossary term must be preceded by empty line',
                            source=source, line=lineno))
                    entries.append(([(line, source, lineno)], ViewList()))
                    in_definition = False
                # second term and following
                else:
                    if was_empty:
                        messages.append(self.state.reporter.system_message(
                            2, 'glossary terms must not be separated by empty '
                            'lines', source=source, line=lineno))
                    if entries:
                        entries[-1][0].append((line, source, lineno))
                    else:
                        messages.append(self.state.reporter.system_message(
                            2, 'glossary seems to be misformatted, check '
                            'indentation', source=source, line=lineno))
            else:
                if not in_definition:
                    # first line of definition, determines indentation
                    in_definition = True
                    indent_len = len(line) - len(line.lstrip())
                if entries:
                    entries[-1][1].append(line[indent_len:], source, lineno)
                else:
                    messages.append(self.state.reporter.system_message(
                        2, 'glossary seems to be misformatted, check '
                        'indentation', source=source, line=lineno))
            was_empty = False

        # now, parse all the entries into a big definition list
        items = []
        for terms, definition in entries:
            termtexts = []
            termnodes = []
            system_messages = []  # type: List[unicode]
            for line, source, lineno in terms:
                parts = split_term_classifiers(line)
                # parse the term with inline markup
                # classifiers (parts[1:]) will not be shown on doctree
                textnodes, sysmsg = self.state.inline_text(parts[0], lineno)

                # use first classifier as a index key
                term = make_glossary_term(self.env, textnodes, parts[1], source, lineno)
                term.rawsource = line
                system_messages.extend(sysmsg)
                termtexts.append(term.astext())
                termnodes.append(term)

            termnodes.extend(system_messages)

            defnode = nodes.definition()
            if definition:
                self.state.nested_parse(definition, definition.items[0][1],
                                        defnode)
            termnodes.append(defnode)
            items.append((termtexts,
                          nodes.definition_list_item('', *termnodes)))

        if 'sorted' in self.options:
            items.sort(key=lambda x:
                       unicodedata.normalize('NFD', x[0][0].lower()))

        dlist = nodes.definition_list()
        dlist['classes'].append('glossary')
        dlist.extend(item[1] for item in items)
        node += dlist
        return messages + [node]


def token_xrefs(text):
    # type: (unicode) -> List[nodes.Node]
    retnodes = []
    pos = 0
    for m in token_re.finditer(text):
        if m.start() > pos:
            txt = text[pos:m.start()]
            retnodes.append(nodes.Text(txt, txt))
        refnode = addnodes.pending_xref(
            m.group(1), reftype='token', refdomain='std', reftarget=m.group(1))
        refnode += nodes.literal(m.group(1), m.group(1), classes=['xref'])
        retnodes.append(refnode)
        pos = m.end()
    if pos < len(text):
        retnodes.append(nodes.Text(text[pos:], text[pos:]))
    return retnodes


class ProductionList(SphinxDirective):
    """
    Directive to list grammar productions.
    """

    has_content = False
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = True
    option_spec = {}  # type: Dict

    def run(self):
        # type: () -> List[nodes.Node]
        objects = self.env.domaindata['std']['objects']
        node = addnodes.productionlist()
        messages = []  # type: List[nodes.Node]
        i = 0

        for rule in self.arguments[0].split('\n'):
            if i == 0 and ':' not in rule:
                # production group
                continue
            i += 1
            try:
                name, tokens = rule.split(':', 1)
            except ValueError:
                break
            subnode = addnodes.production()
            subnode['tokenname'] = name.strip()
            if subnode['tokenname']:
                idname = nodes.make_id('grammar-token-%s' % subnode['tokenname'])
                if idname not in self.state.document.ids:
                    subnode['ids'].append(idname)
                self.state.document.note_implicit_target(subnode, subnode)
                objects['token', subnode['tokenname']] = self.env.docname, idname
            subnode.extend(token_xrefs(tokens))
            node.append(subnode)
        return [node] + messages


class StandardDomain(Domain):
    """
    Domain for all objects that don't fit into another domain or are added
    via the application interface.
    """

    name = 'std'
    label = 'Default'

    object_types = {
        'term': ObjType(_('glossary term'), 'term', searchprio=-1),
        'token': ObjType(_('grammar token'), 'token', searchprio=-1),
        'label': ObjType(_('reference label'), 'ref', 'keyword',
                         searchprio=-1),
        'envvar': ObjType(_('environment variable'), 'envvar'),
        'cmdoption': ObjType(_('program option'), 'option'),
        'doc': ObjType(_('document'), 'doc', searchprio=-1)
    }  # type: Dict[unicode, ObjType]

    directives = {
        'program': Program,
        'cmdoption': Cmdoption,  # old name for backwards compatibility
        'option': Cmdoption,
        'envvar': EnvVar,
        'glossary': Glossary,
        'productionlist': ProductionList,
    }  # type: Dict[unicode, Type[Directive]]
    roles = {
        'option':  OptionXRefRole(warn_dangling=True),
        'envvar':  EnvVarXRefRole(),
        # links to tokens in grammar productions
        'token':   XRefRole(),
        # links to terms in glossary
        'term':    XRefRole(lowercase=True, innernodeclass=nodes.inline,
                            warn_dangling=True),
        # links to headings or arbitrary labels
        'ref':     XRefRole(lowercase=True, innernodeclass=nodes.inline,
                            warn_dangling=True),
        # links to labels of numbered figures, tables and code-blocks
        'numref':  XRefRole(lowercase=True,
                            warn_dangling=True),
        # links to labels, without a different title
        'keyword': XRefRole(warn_dangling=True),
        # links to documents
        'doc':     XRefRole(warn_dangling=True, innernodeclass=nodes.inline),
    }  # type: Dict[unicode, Union[RoleFunction, XRefRole]]

    initial_data = {
        'progoptions': {},      # (program, name) -> docname, labelid
        'objects': {},          # (type, name) -> docname, labelid
        'citations': {},        # citation_name -> docname, labelid, lineno
        'citation_refs': {},    # citation_name -> list of docnames
        'labels': {             # labelname -> docname, labelid, sectionname
            'genindex': ('genindex', '', _('Index')),
            'modindex': ('py-modindex', '', _('Module Index')),
            'search':   ('search', '', _('Search Page')),
        },
        'anonlabels': {         # labelname -> docname, labelid
            'genindex': ('genindex', ''),
            'modindex': ('py-modindex', ''),
            'search':   ('search', ''),
        },
    }

    dangling_warnings = {
        'term': 'term not in glossary: %(target)s',
        'ref':  'undefined label: %(target)s (if the link has no caption '
                'the label must precede a section header)',
        'numref':  'undefined label: %(target)s',
        'keyword': 'unknown keyword: %(target)s',
        'doc': 'unknown document: %(target)s',
        'option': 'unknown option: %(target)s',
        'citation': 'citation not found: %(target)s',
    }

    enumerable_nodes = {  # node_class -> (figtype, title_getter)
        nodes.figure: ('figure', None),
        nodes.table: ('table', None),
        nodes.container: ('code-block', None),
    }  # type: Dict[nodes.Node, Tuple[unicode, Callable]]

    def __init__(self, env):
        # type: (BuildEnvironment) -> None
        super(StandardDomain, self).__init__(env)

        # set up enumerable nodes
        self.enumerable_nodes = copy(self.enumerable_nodes)  # create a copy for this instance
        for node, settings in iteritems(env.app.registry.enumerable_nodes):
            self.enumerable_nodes[node] = settings

    def clear_doc(self, docname):
        # type: (unicode) -> None
        for key, (fn, _l) in list(self.data['progoptions'].items()):
            if fn == docname:
                del self.data['progoptions'][key]
        for key, (fn, _l) in list(self.data['objects'].items()):
            if fn == docname:
                del self.data['objects'][key]
        for key, (fn, _l, lineno) in list(self.data['citations'].items()):
            if fn == docname:
                del self.data['citations'][key]
        for key, docnames in list(self.data['citation_refs'].items()):
            if docnames == [docname]:
                del self.data['citation_refs'][key]
            elif docname in docnames:
                docnames.remove(docname)
        for key, (fn, _l, _l) in list(self.data['labels'].items()):
            if fn == docname:
                del self.data['labels'][key]
        for key, (fn, _l) in list(self.data['anonlabels'].items()):
            if fn == docname:
                del self.data['anonlabels'][key]

    def merge_domaindata(self, docnames, otherdata):
        # type: (List[unicode], Dict) -> None
        # XXX duplicates?
        for key, data in otherdata['progoptions'].items():
            if data[0] in docnames:
                self.data['progoptions'][key] = data
        for key, data in otherdata['objects'].items():
            if data[0] in docnames:
                self.data['objects'][key] = data
        for key, data in otherdata['citations'].items():
            if data[0] in docnames:
                self.data['citations'][key] = data
        for key, data in otherdata['citation_refs'].items():
            citation_refs = self.data['citation_refs'].setdefault(key, [])
            for docname in data:
                if docname in docnames:
                    citation_refs.append(docname)
        for key, data in otherdata['labels'].items():
            if data[0] in docnames:
                self.data['labels'][key] = data
        for key, data in otherdata['anonlabels'].items():
            if data[0] in docnames:
                self.data['anonlabels'][key] = data

    def process_doc(self, env, docname, document):
        # type: (BuildEnvironment, unicode, nodes.Node) -> None
        self.note_citations(env, docname, document)
        self.note_citation_refs(env, docname, document)
        self.note_labels(env, docname, document)

    def note_citations(self, env, docname, document):
        # type: (BuildEnvironment, unicode, nodes.Node) -> None
        for node in document.traverse(nodes.citation):
            node['docname'] = docname
            label = node[0].astext()
            if label in self.data['citations']:
                path = env.doc2path(self.data['citations'][label][0])
                logger.warning(__('duplicate citation %s, other instance in %s'), label, path,
                               location=node, type='ref', subtype='citation')
            self.data['citations'][label] = (docname, node['ids'][0], node.line)

    def note_citation_refs(self, env, docname, document):
        # type: (BuildEnvironment, unicode, nodes.Node) -> None
        for node in document.traverse(addnodes.pending_xref):
            if node['refdomain'] == 'std' and node['reftype'] == 'citation':
                label = node['reftarget']
                citation_refs = self.data['citation_refs'].setdefault(label, [])
                citation_refs.append(docname)

    def note_labels(self, env, docname, document):
        # type: (BuildEnvironment, unicode, nodes.Node) -> None
        labels, anonlabels = self.data['labels'], self.data['anonlabels']
        for name, explicit in iteritems(document.nametypes):
            if not explicit:
                continue
            labelid = document.nameids[name]
            if labelid is None:
                continue
            node = document.ids[labelid]
            if node.tagname == 'target' and 'refid' in node:  # indirect hyperlink targets
                node = document.ids.get(node['refid'])
                labelid = node['names'][0]
            if (node.tagname == 'footnote' or
                    'refuri' in node or
                    node.tagname.startswith('desc_')):
                # ignore footnote labels, labels automatically generated from a
                # link and object descriptions
                continue
            if name in labels:
                logger.warning(__('duplicate label %s, other instance in %s'),
                               name, env.doc2path(labels[name][0]),
                               location=node)
            anonlabels[name] = docname, labelid
            if node.tagname in ('section', 'rubric'):
                sectname = clean_astext(node[0])  # node[0] == title node
            elif self.is_enumerable_node(node):
                sectname = self.get_numfig_title(node)
                if not sectname:
                    continue
            elif node.traverse(addnodes.toctree):
                n = node.traverse(addnodes.toctree)[0]
                if n.get('caption'):
                    sectname = n['caption']
                else:
                    continue
            else:
                # anonymous-only labels
                continue
            labels[name] = docname, labelid, sectname

    def check_consistency(self):
        # type: () -> None
        for name, (docname, labelid, lineno) in iteritems(self.data['citations']):
            if name not in self.data['citation_refs']:
                logger.warning(__('Citation [%s] is not referenced.'), name,
                               type='ref', subtype='citation',
                               location=(docname, lineno))

    def build_reference_node(self, fromdocname, builder, docname, labelid,
                             sectname, rolename, **options):
        # type: (unicode, Builder, unicode, unicode, unicode, unicode, Any) -> nodes.Node
        nodeclass = options.pop('nodeclass', nodes.reference)
        newnode = nodeclass('', '', internal=True, **options)
        innernode = nodes.inline(sectname, sectname)
        if innernode.get('classes') is not None:
            innernode['classes'].append('std')
            innernode['classes'].append('std-' + rolename)
        if docname == fromdocname:
            newnode['refid'] = labelid
        else:
            # set more info in contnode; in case the
            # get_relative_uri call raises NoUri,
            # the builder will then have to resolve these
            contnode = addnodes.pending_xref('')
            contnode['refdocname'] = docname
            contnode['refsectname'] = sectname
            newnode['refuri'] = builder.get_relative_uri(
                fromdocname, docname)
            if labelid:
                newnode['refuri'] += '#' + labelid
        newnode.append(innernode)
        return newnode

    def resolve_xref(self, env, fromdocname, builder, typ, target, node, contnode):
        # type: (BuildEnvironment, unicode, Builder, unicode, unicode, nodes.Node, nodes.Node) -> nodes.Node  # NOQA
        if typ == 'ref':
            resolver = self._resolve_ref_xref
        elif typ == 'numref':
            resolver = self._resolve_numref_xref
        elif typ == 'keyword':
            resolver = self._resolve_keyword_xref
        elif typ == 'doc':
            resolver = self._resolve_doc_xref
        elif typ == 'option':
            resolver = self._resolve_option_xref
        elif typ == 'citation':
            resolver = self._resolve_citation_xref
        else:
            resolver = self._resolve_obj_xref

        return resolver(env, fromdocname, builder, typ, target, node, contnode)

    def _resolve_ref_xref(self, env, fromdocname, builder, typ, target, node, contnode):
        # type: (BuildEnvironment, unicode, Builder, unicode, unicode, nodes.Node, nodes.Node) -> nodes.Node  # NOQA
        if node['refexplicit']:
            # reference to anonymous label; the reference uses
            # the supplied link caption
            docname, labelid = self.data['anonlabels'].get(target, ('', ''))
            sectname = node.astext()
        else:
            # reference to named label; the final node will
            # contain the section name after the label
            docname, labelid, sectname = self.data['labels'].get(target,
                                                                 ('', '', ''))
        if not docname:
            return None

        return self.build_reference_node(fromdocname, builder,
                                         docname, labelid, sectname, 'ref')

    def _resolve_numref_xref(self, env, fromdocname, builder, typ, target, node, contnode):
        # type: (BuildEnvironment, unicode, Builder, unicode, unicode, nodes.Node, nodes.Node) -> nodes.Node  # NOQA
        if target in self.data['labels']:
            docname, labelid, figname = self.data['labels'].get(target, ('', '', ''))
        else:
            docname, labelid = self.data['anonlabels'].get(target, ('', ''))
            figname = None

        if not docname:
            return None

        target_node = env.get_doctree(docname).ids.get(labelid)
        figtype = self.get_enumerable_node_type(target_node)
        if figtype is None:
            return None

        if figtype != 'section' and env.config.numfig is False:
            logger.warning(__('numfig is disabled. :numref: is ignored.'), location=node)
            return contnode

        try:
            fignumber = self.get_fignumber(env, builder, figtype, docname, target_node)
            if fignumber is None:
                return contnode
        except ValueError:
            logger.warning(__("no number is assigned for %s: %s"), figtype, labelid,
                           location=node)
            return contnode

        try:
            if node['refexplicit']:
                title = contnode.astext()
            else:
                title = env.config.numfig_format.get(figtype, '')

            if figname is None and '{name}' in title:
                logger.warning(__('the link has no caption: %s'), title, location=node)
                return contnode
            else:
                fignum = '.'.join(map(str, fignumber))
                if '{name}' in title or 'number' in title:
                    # new style format (cf. "Fig.{number}")
                    if figname:
                        newtitle = title.format(name=figname, number=fignum)
                    else:
                        newtitle = title.format(number=fignum)
                else:
                    # old style format (cf. "Fig.%s")
                    newtitle = title % fignum
        except KeyError as exc:
            logger.warning(__('invalid numfig_format: %s (%r)'), title, exc, location=node)
            return contnode
        except TypeError:
            logger.warning(__('invalid numfig_format: %s'), title, location=node)
            return contnode

        return self.build_reference_node(fromdocname, builder,
                                         docname, labelid, newtitle, 'numref',
                                         nodeclass=addnodes.number_reference,
                                         title=title)

    def _resolve_keyword_xref(self, env, fromdocname, builder, typ, target, node, contnode):
        # type: (BuildEnvironment, unicode, Builder, unicode, unicode, nodes.Node, nodes.Node) -> nodes.Node  # NOQA
        # keywords are oddballs: they are referenced by named labels
        docname, labelid, _ = self.data['labels'].get(target, ('', '', ''))
        if not docname:
            return None
        return make_refnode(builder, fromdocname, docname,
                            labelid, contnode)

    def _resolve_doc_xref(self, env, fromdocname, builder, typ, target, node, contnode):
        # type: (BuildEnvironment, unicode, Builder, unicode, unicode, nodes.Node, nodes.Node) -> nodes.Node  # NOQA
        # directly reference to document by source name; can be absolute or relative
        refdoc = node.get('refdoc', fromdocname)
        docname = docname_join(refdoc, node['reftarget'])
        if docname not in env.all_docs:
            return None
        else:
            if node['refexplicit']:
                # reference with explicit title
                caption = node.astext()
            else:
                caption = clean_astext(env.titles[docname])
            innernode = nodes.inline(caption, caption, classes=['doc'])
            return make_refnode(builder, fromdocname, docname, None, innernode)

    def _resolve_option_xref(self, env, fromdocname, builder, typ, target, node, contnode):
        # type: (BuildEnvironment, unicode, Builder, unicode, unicode, nodes.Node, nodes.Node) -> nodes.Node  # NOQA
        progname = node.get('std:program')
        target = target.strip()
        docname, labelid = self.data['progoptions'].get((progname, target), ('', ''))
        if not docname:
            commands = []
            while ws_re.search(target):
                subcommand, target = ws_re.split(target, 1)
                commands.append(subcommand)
                progname = "-".join(commands)

                docname, labelid = self.data['progoptions'].get((progname, target),
                                                                ('', ''))
                if docname:
                    break
            else:
                return None

        return make_refnode(builder, fromdocname, docname,
                            labelid, contnode)

    def _resolve_citation_xref(self, env, fromdocname, builder, typ, target, node, contnode):
        # type: (BuildEnvironment, unicode, Builder, unicode, unicode, nodes.Node, nodes.Node) -> nodes.Node  # NOQA
        from sphinx.environment import NoUri

        docname, labelid, lineno = self.data['citations'].get(target, ('', '', 0))
        if not docname:
            if 'ids' in node:
                # remove ids attribute that annotated at
                # transforms.CitationReference.apply.
                del node['ids'][:]
            return None

        try:
            return make_refnode(builder, fromdocname, docname,
                                labelid, contnode)
        except NoUri:
            # remove the ids we added in the CitationReferences
            # transform since they can't be transfered to
            # the contnode (if it's a Text node)
            if not isinstance(contnode, nodes.Element):
                del node['ids'][:]
            raise

    def _resolve_obj_xref(self, env, fromdocname, builder, typ, target, node, contnode):
        # type: (BuildEnvironment, unicode, Builder, unicode, unicode, nodes.Node, nodes.Node) -> nodes.Node  # NOQA
        objtypes = self.objtypes_for_role(typ) or []
        for objtype in objtypes:
            if (objtype, target) in self.data['objects']:
                docname, labelid = self.data['objects'][objtype, target]
                break
        else:
            docname, labelid = '', ''
        if not docname:
            return None
        return make_refnode(builder, fromdocname, docname,
                            labelid, contnode)

    def resolve_any_xref(self, env, fromdocname, builder, target, node, contnode):
        # type: (BuildEnvironment, unicode, Builder, unicode, nodes.Node, nodes.Node) -> List[Tuple[unicode, nodes.Node]]  # NOQA
        results = []  # type: List[Tuple[unicode, nodes.Node]]
        ltarget = target.lower()  # :ref: lowercases its target automatically
        for role in ('ref', 'option'):  # do not try "keyword"
            res = self.resolve_xref(env, fromdocname, builder, role,
                                    ltarget if role == 'ref' else target,
                                    node, contnode)
            if res:
                results.append(('std:' + role, res))
        # all others
        for objtype in self.object_types:
            key = (objtype, target)
            if objtype == 'term':
                key = (objtype, ltarget)
            if key in self.data['objects']:
                docname, labelid = self.data['objects'][key]
                results.append(('std:' + self.role_for_objtype(objtype),
                                make_refnode(builder, fromdocname, docname,
                                             labelid, contnode)))
        return results

    def get_objects(self):
        # type: () -> Iterator[Tuple[unicode, unicode, unicode, unicode, unicode, int]]
        # handle the special 'doc' reference here
        for doc in self.env.all_docs:
            yield (doc, clean_astext(self.env.titles[doc]), 'doc', doc, '', -1)
        for (prog, option), info in iteritems(self.data['progoptions']):
            if prog:
                fullname = ".".join([prog, option])
                yield (fullname, fullname, 'cmdoption', info[0], info[1], 1)
            else:
                yield (option, option, 'cmdoption', info[0], info[1], 1)
        for (type, name), info in iteritems(self.data['objects']):
            yield (name, name, type, info[0], info[1],
                   self.object_types[type].attrs['searchprio'])
        for name, info in iteritems(self.data['labels']):
            yield (name, info[2], 'label', info[0], info[1], -1)
        # add anonymous-only labels as well
        non_anon_labels = set(self.data['labels'])
        for name, info in iteritems(self.data['anonlabels']):
            if name not in non_anon_labels:
                yield (name, name, 'label', info[0], info[1], -1)

    def get_type_name(self, type, primary=False):
        # type: (ObjType, bool) -> unicode
        # never prepend "Default"
        return type.lname

    def is_enumerable_node(self, node):
        # type: (nodes.Node) -> bool
        return node.__class__ in self.enumerable_nodes

    def get_numfig_title(self, node):
        # type: (nodes.Node) -> unicode
        """Get the title of enumerable nodes to refer them using its title"""
        if self.is_enumerable_node(node):
            _, title_getter = self.enumerable_nodes.get(node.__class__, (None, None))
            if title_getter:
                return title_getter(node)
            else:
                for subnode in node:
                    if subnode.tagname in ('caption', 'title'):
                        return clean_astext(subnode)

        return None

    def get_enumerable_node_type(self, node):
        # type: (nodes.Node) -> unicode
        """Get type of enumerable nodes."""
        def has_child(node, cls):
            # type: (nodes.Node, Type) -> bool
            return any(isinstance(child, cls) for child in node)

        if isinstance(node, nodes.section):
            return 'section'
        elif isinstance(node, nodes.container):
            if node.get('literal_block') and has_child(node, nodes.literal_block):
                return 'code-block'
            else:
                return None
        else:
            figtype, _ = self.enumerable_nodes.get(node.__class__, (None, None))
            return figtype

    def get_figtype(self, node):
        # type: (nodes.Node) -> unicode
        """Get figure type of nodes.

        .. deprecated:: 1.8
        """
        warnings.warn('StandardDomain.get_figtype() is deprecated. '
                      'Please use get_enumerable_node_type() instead.',
                      RemovedInSphinx30Warning, stacklevel=2)
        return self.get_enumerable_node_type(node)

    def get_fignumber(self, env, builder, figtype, docname, target_node):
        # type: (BuildEnvironment, Builder, unicode, unicode, nodes.Node) -> Tuple[int, ...]
        if figtype == 'section':
            if builder.name == 'latex':
                return tuple()
            elif docname not in env.toc_secnumbers:
                raise ValueError  # no number assigned
            else:
                anchorname = '#' + target_node['ids'][0]
                if anchorname not in env.toc_secnumbers[docname]:
                    # try first heading which has no anchor
                    return env.toc_secnumbers[docname].get('')
                else:
                    return env.toc_secnumbers[docname].get(anchorname)
        else:
            try:
                figure_id = target_node['ids'][0]
                return env.toc_fignumbers[docname][figtype][figure_id]
            except (KeyError, IndexError):
                # target_node is found, but fignumber is not assigned.
                # Maybe it is defined in orphaned document.
                raise ValueError

    def get_full_qualified_name(self, node):
        # type: (nodes.Node) -> unicode
        if node.get('reftype') == 'option':
            progname = node.get('std:program')
            command = ws_re.split(node.get('reftarget'))
            if progname:
                command.insert(0, progname)
            option = command.pop()
            if command:
                return '.'.join(['-'.join(command), option])
            else:
                return None
        else:
            return None


def setup(app):
    # type: (Sphinx) -> Dict[unicode, Any]
    app.add_domain(StandardDomain)

    return {
        'version': 'builtin',
        'env_version': 1,
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
