"""The standard domain."""

from __future__ import annotations

import re
from copy import copy
from typing import TYPE_CHECKING, Any, Callable, Final, cast

from docutils import nodes
from docutils.nodes import Element, Node, system_message
from docutils.parsers.rst import Directive, directives
from docutils.statemachine import StringList

from sphinx import addnodes
from sphinx.addnodes import desc_signature, pending_xref
from sphinx.directives import ObjectDescription
from sphinx.domains import Domain, ObjType, TitleGetter
from sphinx.locale import _, __
from sphinx.roles import EmphasizedLiteral, XRefRole
from sphinx.util import docname_join, logging, ws_re
from sphinx.util.docutils import SphinxDirective
from sphinx.util.nodes import clean_astext, make_id, make_refnode

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

    from sphinx.application import Sphinx
    from sphinx.builders import Builder
    from sphinx.environment import BuildEnvironment
    from sphinx.util.typing import OptionSpec, RoleFunction

logger = logging.getLogger(__name__)

# RE for option descriptions
option_desc_re = re.compile(r'((?:/|--|-|\+)?[^\s=]+)(=?\s*.*)')
# RE for grammar tokens
token_re = re.compile(r'`((~?\w*:)?\w+)`', re.U)

samp_role = EmphasizedLiteral()


class GenericObject(ObjectDescription[str]):
    """
    A generic x-ref directive registered with Sphinx.add_object_type().
    """
    indextemplate: str = ''
    parse_node: Callable[[BuildEnvironment, str, desc_signature], str] | None = None

    def handle_signature(self, sig: str, signode: desc_signature) -> str:
        if self.parse_node:
            name = self.parse_node(self.env, sig, signode)
        else:
            signode.clear()
            signode += addnodes.desc_name(sig, sig)
            # normalize whitespace like XRefRole does
            name = ws_re.sub(' ', sig)
        return name

    def add_target_and_index(self, name: str, sig: str, signode: desc_signature) -> None:
        node_id = make_id(self.env, self.state.document, self.objtype, name)
        signode['ids'].append(node_id)
        self.state.document.note_explicit_target(signode)

        if self.indextemplate:
            colon = self.indextemplate.find(':')
            if colon != -1:
                indextype = self.indextemplate[:colon].strip()
                indexentry = self.indextemplate[colon + 1:].strip() % (name,)
            else:
                indextype = 'single'
                indexentry = self.indextemplate % (name,)
            self.indexnode['entries'].append((indextype, indexentry, node_id, '', None))

        std = cast(StandardDomain, self.env.get_domain('std'))
        std.note_object(self.objtype, name, node_id, location=signode)


class EnvVar(GenericObject):
    indextemplate = _('environment variable; %s')


class EnvVarXRefRole(XRefRole):
    """
    Cross-referencing role for environment variables (adds an index entry).
    """

    def result_nodes(self, document: nodes.document, env: BuildEnvironment, node: Element,
                     is_ref: bool) -> tuple[list[Node], list[system_message]]:
        if not is_ref:
            return [node], []
        varname = node['reftarget']
        tgtid = 'index-%s' % env.new_serialno('index')
        indexnode = addnodes.index()
        indexnode['entries'] = [
            ('single', varname, tgtid, '', None),
            ('single', _('environment variable; %s') % varname, tgtid, '', None),
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
    option_spec: OptionSpec = {}

    def run(self) -> list[Node]:
        # normalize whitespace in fullname like XRefRole does
        fullname = ws_re.sub(' ', self.arguments[0].strip())
        node_id = make_id(self.env, self.state.document, self.name, fullname)
        node = nodes.target('', '', ids=[node_id])
        self.set_source_info(node)
        self.state.document.note_explicit_target(node)
        ret: list[Node] = [node]
        if self.indextemplate:
            indexentry = self.indextemplate % (fullname,)
            indextype = 'single'
            colon = indexentry.find(':')
            if colon != -1:
                indextype = indexentry[:colon].strip()
                indexentry = indexentry[colon + 1:].strip()
            inode = addnodes.index(entries=[(indextype, indexentry, node_id, '', None)])
            ret.insert(0, inode)
        name = self.name
        if ':' in self.name:
            _, name = self.name.split(':', 1)

        std = cast(StandardDomain, self.env.get_domain('std'))
        std.note_object(name, fullname, node_id, location=node)

        return ret


class Cmdoption(ObjectDescription[str]):
    """
    Description of a command-line option (.. option).
    """

    def handle_signature(self, sig: str, signode: desc_signature) -> str:
        """Transform an option description into RST nodes."""
        count = 0
        firstname = ''
        for potential_option in sig.split(', '):
            potential_option = potential_option.strip()
            m = option_desc_re.match(potential_option)
            if not m:
                logger.warning(__('Malformed option description %r, should '
                                  'look like "opt", "-opt args", "--opt args", '
                                  '"/opt args" or "+opt args"'), potential_option,
                               location=signode)
                continue
            optname, args = m.groups()
            if optname[-1] == '[' and args[-1] == ']':
                # optional value surrounded by brackets (ex. foo[=bar])
                optname = optname[:-1]
                args = '[' + args

            if count:
                if self.env.config.option_emphasise_placeholders:
                    signode += addnodes.desc_sig_punctuation(',', ',')
                    signode += addnodes.desc_sig_space()
                else:
                    signode += addnodes.desc_addname(', ', ', ')
            signode += addnodes.desc_name(optname, optname)
            if self.env.config.option_emphasise_placeholders:
                add_end_bracket = False
                if args:
                    if args[0] == '[' and args[-1] == ']':
                        add_end_bracket = True
                        signode += addnodes.desc_sig_punctuation('[', '[')
                        args = args[1:-1]
                    elif args[0] == ' ':
                        signode += addnodes.desc_sig_space()
                        args = args.strip()
                    elif args[0] == '=':
                        signode += addnodes.desc_sig_punctuation('=', '=')
                        args = args[1:]
                    for part in samp_role.parse(args):
                        if isinstance(part, nodes.Text):
                            signode += nodes.Text(part.astext())
                        else:
                            signode += part
                if add_end_bracket:
                    signode += addnodes.desc_sig_punctuation(']', ']')
            else:
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

    def add_target_and_index(self, firstname: str, sig: str, signode: desc_signature) -> None:
        currprogram = self.env.ref_context.get('std:program')
        for optname in signode.get('allnames', []):
            prefixes = ['cmdoption']
            if currprogram:
                prefixes.append(currprogram)
            if not optname.startswith(('-', '/')):
                prefixes.append('arg')
            prefix = '-'.join(prefixes)
            node_id = make_id(self.env, self.state.document, prefix, optname)
            signode['ids'].append(node_id)

        self.state.document.note_explicit_target(signode)

        domain = self.env.domains['std']
        for optname in signode.get('allnames', []):
            domain.add_program_option(currprogram, optname,
                                      self.env.docname, signode['ids'][0])

        # create an index entry
        if currprogram:
            descr = _('%s command line option') % currprogram
        else:
            descr = _('command line option')
        for option in signode.get('allnames', []):
            entry = '; '.join([descr, option])
            self.indexnode['entries'].append(('pair', entry, signode['ids'][0], '', None))


class Program(SphinxDirective):
    """
    Directive to name the program for which options are documented.
    """

    has_content = False
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = True
    option_spec: OptionSpec = {}

    def run(self) -> list[Node]:
        program = ws_re.sub('-', self.arguments[0].strip())
        if program == 'None':
            self.env.ref_context.pop('std:program', None)
        else:
            self.env.ref_context['std:program'] = program
        return []


class OptionXRefRole(XRefRole):
    def process_link(self, env: BuildEnvironment, refnode: Element, has_explicit_title: bool,
                     title: str, target: str) -> tuple[str, str]:
        refnode['std:program'] = env.ref_context.get('std:program')
        return title, target


def split_term_classifiers(line: str) -> list[str | None]:
    # split line into a term and classifiers. if no classifier, None is used..
    parts: list[str | None] = re.split(' +: +', line) + [None]
    return parts


def make_glossary_term(env: BuildEnvironment, textnodes: Iterable[Node], index_key: str,
                       source: str, lineno: int, node_id: str | None, document: nodes.document,
                       ) -> nodes.term:
    # get a text-only representation of the term and register it
    # as a cross-reference target
    term = nodes.term('', '', *textnodes)
    term.source = source
    term.line = lineno
    termtext = term.astext()

    if node_id:
        # node_id is given from outside (mainly i18n module), use it forcedly
        term['ids'].append(node_id)
    else:
        node_id = make_id(env, document, 'term', termtext)
        term['ids'].append(node_id)
        document.note_explicit_target(term)

    std = cast(StandardDomain, env.get_domain('std'))
    std._note_term(termtext, node_id, location=term)

    # add an index entry too
    indexnode = addnodes.index()
    indexnode['entries'] = [('single', termtext, node_id, 'main', index_key)]
    indexnode.source, indexnode.line = term.source, term.line
    term.append(indexnode)

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
    option_spec: OptionSpec = {
        'sorted': directives.flag,
    }

    def run(self) -> list[Node]:
        node = addnodes.glossary()
        node.document = self.state.document
        node['sorted'] = ('sorted' in self.options)

        # This directive implements a custom format of the reST definition list
        # that allows multiple lines of terms before the definition.  This is
        # easy to parse since we know that the contents of the glossary *must
        # be* a definition list.

        # first, collect single entries
        entries: list[tuple[list[tuple[str, str, int]], StringList]] = []
        in_definition = True
        in_comment = False
        was_empty = True
        messages: list[Node] = []
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
                    in_comment = True
                    continue
                in_comment = False

                # first term of definition
                if in_definition:
                    if not was_empty:
                        messages.append(self.state.reporter.warning(
                            _('glossary term must be preceded by empty line'),
                            source=source, line=lineno))
                    entries.append(([(line, source, lineno)], StringList()))
                    in_definition = False
                # second term and following
                else:
                    if was_empty:
                        messages.append(self.state.reporter.warning(
                            _('glossary terms must not be separated by empty lines'),
                            source=source, line=lineno))
                    if entries:
                        entries[-1][0].append((line, source, lineno))
                    else:
                        messages.append(self.state.reporter.warning(
                            _('glossary seems to be misformatted, check indentation'),
                            source=source, line=lineno))
            elif in_comment:
                pass
            else:
                if not in_definition:
                    # first line of definition, determines indentation
                    in_definition = True
                    indent_len = len(line) - len(line.lstrip())
                if entries:
                    entries[-1][1].append(line[indent_len:], source, lineno)
                else:
                    messages.append(self.state.reporter.warning(
                        _('glossary seems to be misformatted, check indentation'),
                        source=source, line=lineno))
            was_empty = False

        # now, parse all the entries into a big definition list
        items: list[nodes.definition_list_item] = []
        for terms, definition in entries:
            termnodes: list[Node] = []
            system_messages: list[Node] = []
            for line, source, lineno in terms:
                parts = split_term_classifiers(line)
                # parse the term with inline markup
                # classifiers (parts[1:]) will not be shown on doctree
                textnodes, sysmsg = self.state.inline_text(parts[0],  # type: ignore[arg-type]
                                                           lineno)

                # use first classifier as a index key
                term = make_glossary_term(self.env, textnodes,
                                          parts[1], source, lineno,  # type: ignore[arg-type]
                                          node_id=None, document=self.state.document)
                term.rawsource = line
                system_messages.extend(sysmsg)
                termnodes.append(term)

            termnodes.extend(system_messages)

            defnode = nodes.definition()
            if definition:
                self.state.nested_parse(definition, definition.items[0][1],
                                        defnode)
            termnodes.append(defnode)
            items.append(nodes.definition_list_item('', *termnodes))

        dlist = nodes.definition_list('', *items)
        dlist['classes'].append('glossary')
        node += dlist
        return messages + [node]


def token_xrefs(text: str, productionGroup: str = '') -> list[Node]:
    if len(productionGroup) != 0:
        productionGroup += ':'
    retnodes: list[Node] = []
    pos = 0
    for m in token_re.finditer(text):
        if m.start() > pos:
            txt = text[pos:m.start()]
            retnodes.append(nodes.Text(txt))
        token = m.group(1)
        if ':' in token:
            if token[0] == '~':
                _, title = token.split(':')
                target = token[1:]
            elif token[0] == ':':
                title = token[1:]
                target = title
            else:
                title = token
                target = token
        else:
            title = token
            target = productionGroup + token
        refnode = pending_xref(title, reftype='token', refdomain='std',
                               reftarget=target)
        refnode += nodes.literal(token, title, classes=['xref'])
        retnodes.append(refnode)
        pos = m.end()
    if pos < len(text):
        retnodes.append(nodes.Text(text[pos:]))
    return retnodes


class ProductionList(SphinxDirective):
    """
    Directive to list grammar productions.
    """

    has_content = False
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = True
    option_spec: OptionSpec = {}

    def run(self) -> list[Node]:
        domain = cast(StandardDomain, self.env.get_domain('std'))
        node: Element = addnodes.productionlist()
        self.set_source_info(node)
        # The backslash handling is from ObjectDescription.get_signatures
        nl_escape_re = re.compile(r'\\\n')
        lines = nl_escape_re.sub('', self.arguments[0]).split('\n')

        productionGroup = ""
        first_rule_seen = False
        for rule in lines:
            if not first_rule_seen and ':' not in rule:
                productionGroup = rule.strip()
                continue
            first_rule_seen = True
            try:
                name, tokens = rule.split(':', 1)
            except ValueError:
                break
            subnode = addnodes.production(rule)
            name = name.strip()
            subnode['tokenname'] = name
            if subnode['tokenname']:
                prefix = 'grammar-token-%s' % productionGroup
                node_id = make_id(self.env, self.state.document, prefix, name)
                subnode['ids'].append(node_id)
                self.state.document.note_implicit_target(subnode, subnode)

                if len(productionGroup) != 0:
                    objName = f"{productionGroup}:{name}"
                else:
                    objName = name
                domain.note_object('token', objName, node_id, location=node)
            subnode.extend(token_xrefs(tokens, productionGroup))
            node.append(subnode)
        return [node]


class TokenXRefRole(XRefRole):
    def process_link(self, env: BuildEnvironment, refnode: Element, has_explicit_title: bool,
                     title: str, target: str) -> tuple[str, str]:
        target = target.lstrip('~')  # a title-specific thing
        if not self.has_explicit_title and title[0] == '~':
            if ':' in title:
                _, title = title.split(':')
            else:
                title = title[1:]
        return title, target


class StandardDomain(Domain):
    """
    Domain for all objects that don't fit into another domain or are added
    via the application interface.
    """

    name = 'std'
    label = 'Default'

    object_types: dict[str, ObjType] = {
        'term': ObjType(_('glossary term'), 'term', searchprio=-1),
        'token': ObjType(_('grammar token'), 'token', searchprio=-1),
        'label': ObjType(_('reference label'), 'ref', 'keyword',
                         searchprio=-1),
        'envvar': ObjType(_('environment variable'), 'envvar'),
        'cmdoption': ObjType(_('program option'), 'option'),
        'doc': ObjType(_('document'), 'doc', searchprio=-1),
    }

    directives: dict[str, type[Directive]] = {
        'program': Program,
        'cmdoption': Cmdoption,  # old name for backwards compatibility
        'option': Cmdoption,
        'envvar': EnvVar,
        'glossary': Glossary,
        'productionlist': ProductionList,
    }
    roles: dict[str, RoleFunction | XRefRole] = {
        'option':  OptionXRefRole(warn_dangling=True),
        'envvar':  EnvVarXRefRole(),
        # links to tokens in grammar productions
        'token':   TokenXRefRole(),
        # links to terms in glossary
        'term':    XRefRole(innernodeclass=nodes.inline,
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
    }

    initial_data: Final = {  # type: ignore[misc]
        'progoptions': {},      # (program, name) -> docname, labelid
        'objects': {},          # (type, name) -> docname, labelid
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

    _virtual_doc_names: dict[str, tuple[str, str]] = {  # labelname -> docname, sectionname
        'genindex': ('genindex', _('Index')),
        'modindex': ('py-modindex', _('Module Index')),
        'search': ('search', _('Search Page')),
    }

    dangling_warnings = {
        'term': 'term not in glossary: %(target)r',
        'numref':  'undefined label: %(target)r',
        'keyword': 'unknown keyword: %(target)r',
        'doc': 'unknown document: %(target)r',
        'option': 'unknown option: %(target)r',
    }

    # node_class -> (figtype, title_getter)
    enumerable_nodes: dict[type[Node], tuple[str, TitleGetter | None]] = {
        nodes.figure: ('figure', None),
        nodes.table: ('table', None),
        nodes.container: ('code-block', None),
    }

    def __init__(self, env: BuildEnvironment) -> None:
        super().__init__(env)

        # set up enumerable nodes
        self.enumerable_nodes = copy(self.enumerable_nodes)  # create a copy for this instance
        for node, settings in env.app.registry.enumerable_nodes.items():
            self.enumerable_nodes[node] = settings

    def note_hyperlink_target(self, name: str, docname: str, node_id: str,
                              title: str = '') -> None:
        """Add a hyperlink target for cross reference.

        .. warning::

           This is only for internal use.  Please don't use this from your extension.
           ``document.note_explicit_target()`` or ``note_implicit_target()`` are recommended to
           add a hyperlink target to the document.

           This only adds a hyperlink target to the StandardDomain.  And this does not add a
           node_id to node.  Therefore, it is very fragile to calling this without
           understanding hyperlink target framework in both docutils and Sphinx.

        .. versionadded:: 3.0
        """
        if name in self.anonlabels and self.anonlabels[name] != (docname, node_id):
            logger.warning(__('duplicate label %s, other instance in %s'),
                           name, self.env.doc2path(self.anonlabels[name][0]))

        self.anonlabels[name] = (docname, node_id)
        if title:
            self.labels[name] = (docname, node_id, title)

    @property
    def objects(self) -> dict[tuple[str, str], tuple[str, str]]:
        return self.data.setdefault('objects', {})  # (objtype, name) -> docname, labelid

    def note_object(self, objtype: str, name: str, labelid: str, location: Any = None,
                    ) -> None:
        """Note a generic object for cross reference.

        .. versionadded:: 3.0
        """
        if (objtype, name) in self.objects:
            docname = self.objects[objtype, name][0]
            logger.warning(__('duplicate %s description of %s, other instance in %s'),
                           objtype, name, docname, location=location)
        self.objects[objtype, name] = (self.env.docname, labelid)

    @property
    def _terms(self) -> dict[str, tuple[str, str]]:
        """.. note:: Will be removed soon. internal use only."""
        return self.data.setdefault('terms', {})  # (name) -> docname, labelid

    def _note_term(self, term: str, labelid: str, location: Any = None) -> None:
        """Note a term for cross reference.

        .. note:: Will be removed soon. internal use only.
        """
        self.note_object('term', term, labelid, location)

        self._terms[term.lower()] = (self.env.docname, labelid)

    @property
    def progoptions(self) -> dict[tuple[str | None, str], tuple[str, str]]:
        return self.data.setdefault('progoptions', {})  # (program, name) -> docname, labelid

    @property
    def labels(self) -> dict[str, tuple[str, str, str]]:
        return self.data.setdefault('labels', {})  # labelname -> docname, labelid, sectionname

    @property
    def anonlabels(self) -> dict[str, tuple[str, str]]:
        return self.data.setdefault('anonlabels', {})  # labelname -> docname, labelid

    def clear_doc(self, docname: str) -> None:
        key: Any = None
        for key, (fn, _l) in list(self.progoptions.items()):
            if fn == docname:
                del self.progoptions[key]
        for key, (fn, _l) in list(self.objects.items()):
            if fn == docname:
                del self.objects[key]
        for key, (fn, _l) in list(self._terms.items()):
            if fn == docname:
                del self._terms[key]
        for key, (fn, _l, _l) in list(self.labels.items()):
            if fn == docname:
                del self.labels[key]
        for key, (fn, _l) in list(self.anonlabels.items()):
            if fn == docname:
                del self.anonlabels[key]

    def merge_domaindata(self, docnames: list[str], otherdata: dict[str, Any]) -> None:
        # XXX duplicates?
        for key, data in otherdata['progoptions'].items():
            if data[0] in docnames:
                self.progoptions[key] = data
        for key, data in otherdata['objects'].items():
            if data[0] in docnames:
                self.objects[key] = data
        for key, data in otherdata['terms'].items():
            if data[0] in docnames:
                self._terms[key] = data
        for key, data in otherdata['labels'].items():
            if data[0] in docnames:
                self.labels[key] = data
        for key, data in otherdata['anonlabels'].items():
            if data[0] in docnames:
                self.anonlabels[key] = data

    def process_doc(
        self, env: BuildEnvironment, docname: str, document: nodes.document,
    ) -> None:
        for name, explicit in document.nametypes.items():
            if not explicit:
                continue
            labelid = document.nameids[name]
            if labelid is None:
                continue
            node = document.ids[labelid]
            if isinstance(node, nodes.target) and 'refid' in node:
                # indirect hyperlink targets
                node = document.ids.get(node['refid'])  # type: ignore[assignment]
                labelid = node['names'][0]
            if (node.tagname == 'footnote' or
                    'refuri' in node or
                    node.tagname.startswith('desc_')):
                # ignore footnote labels, labels automatically generated from a
                # link and object descriptions
                continue
            if name in self.labels:
                logger.warning(__('duplicate label %s, other instance in %s'),
                               name, env.doc2path(self.labels[name][0]),
                               location=node)
            self.anonlabels[name] = docname, labelid
            if node.tagname == 'section':
                title = cast(nodes.title, node[0])
                sectname = clean_astext(title)
            elif node.tagname == 'rubric':
                sectname = clean_astext(node)
            elif self.is_enumerable_node(node):
                sectname = self.get_numfig_title(node) or ''
                if not sectname:
                    continue
            else:
                if (isinstance(node, (nodes.definition_list,
                                      nodes.field_list)) and
                        node.children):
                    node = cast(nodes.Element, node.children[0])
                if isinstance(node, (nodes.field, nodes.definition_list_item)):
                    node = cast(nodes.Element, node.children[0])
                if isinstance(node, (nodes.term, nodes.field_name)):
                    sectname = clean_astext(node)
                else:
                    toctree = next(node.findall(addnodes.toctree), None)
                    if toctree and toctree.get('caption'):
                        sectname = toctree['caption']
                    else:
                        # anonymous-only labels
                        continue
            self.labels[name] = docname, labelid, sectname

    def add_program_option(self, program: str | None, name: str,
                           docname: str, labelid: str) -> None:
        # prefer first command option entry
        if (program, name) not in self.progoptions:
            self.progoptions[program, name] = (docname, labelid)

    def build_reference_node(self, fromdocname: str, builder: Builder, docname: str,
                             labelid: str, sectname: str, rolename: str, **options: Any,
                             ) -> Element:
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
            contnode = pending_xref('')
            contnode['refdocname'] = docname
            contnode['refsectname'] = sectname
            newnode['refuri'] = builder.get_relative_uri(
                fromdocname, docname)
            if labelid:
                newnode['refuri'] += '#' + labelid
        newnode.append(innernode)
        return newnode

    def resolve_xref(self, env: BuildEnvironment, fromdocname: str, builder: Builder,
                     typ: str, target: str, node: pending_xref, contnode: Element,
                     ) -> Element | None:
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
        elif typ == 'term':
            resolver = self._resolve_term_xref
        else:
            resolver = self._resolve_obj_xref

        return resolver(env, fromdocname, builder, typ, target, node, contnode)

    def _resolve_ref_xref(self, env: BuildEnvironment, fromdocname: str,
                          builder: Builder, typ: str, target: str, node: pending_xref,
                          contnode: Element) -> Element | None:
        if node['refexplicit']:
            # reference to anonymous label; the reference uses
            # the supplied link caption
            docname, labelid = self.anonlabels.get(target, ('', ''))
            sectname = node.astext()
        else:
            # reference to named label; the final node will
            # contain the section name after the label
            docname, labelid, sectname = self.labels.get(target, ('', '', ''))
        if not docname:
            return None

        return self.build_reference_node(fromdocname, builder,
                                         docname, labelid, sectname, 'ref')

    def _resolve_numref_xref(self, env: BuildEnvironment, fromdocname: str,
                             builder: Builder, typ: str, target: str,
                             node: pending_xref, contnode: Element) -> Element | None:
        if target in self.labels:
            docname, labelid, figname = self.labels.get(target, ('', '', ''))
        else:
            docname, labelid = self.anonlabels.get(target, ('', ''))
            figname = None

        if not docname:
            return None

        target_node = env.get_doctree(docname).ids.get(labelid)
        assert target_node is not None
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
            logger.warning(__("Failed to create a cross reference. Any number is not "
                              "assigned: %s"),
                           labelid, location=node)
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

    def _resolve_keyword_xref(self, env: BuildEnvironment, fromdocname: str,
                              builder: Builder, typ: str, target: str,
                              node: pending_xref, contnode: Element) -> Element | None:
        # keywords are oddballs: they are referenced by named labels
        docname, labelid, _ = self.labels.get(target, ('', '', ''))
        if not docname:
            return None
        return make_refnode(builder, fromdocname, docname,
                            labelid, contnode)

    def _resolve_doc_xref(self, env: BuildEnvironment, fromdocname: str,
                          builder: Builder, typ: str, target: str,
                          node: pending_xref, contnode: Element) -> Element | None:
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

    def _resolve_option_xref(self, env: BuildEnvironment, fromdocname: str,
                             builder: Builder, typ: str, target: str,
                             node: pending_xref, contnode: Element) -> Element | None:
        progname = node.get('std:program')
        target = target.strip()
        docname, labelid = self.progoptions.get((progname, target), ('', ''))
        if not docname:
            # Support also reference that contain an option value:
            # * :option:`-foo=bar`
            # * :option:`-foo[=bar]`
            # * :option:`-foo bar`
            for needle in {'=', '[=', ' '}:
                if needle in target:
                    stem, _, _ = target.partition(needle)
                    docname, labelid = self.progoptions.get((progname, stem), ('', ''))
                    if docname:
                        break
        if not docname:
            commands = []
            while ws_re.search(target):
                subcommand, target = ws_re.split(target, 1)
                commands.append(subcommand)
                progname = "-".join(commands)

                docname, labelid = self.progoptions.get((progname, target), ('', ''))
                if docname:
                    break
            else:
                return None

        return make_refnode(builder, fromdocname, docname,
                            labelid, contnode)

    def _resolve_term_xref(self, env: BuildEnvironment, fromdocname: str,
                           builder: Builder, typ: str, target: str,
                           node: pending_xref, contnode: Element) -> Element | None:
        result = self._resolve_obj_xref(env, fromdocname, builder, typ,
                                        target, node, contnode)
        if result:
            return result
        else:
            # fallback to case insensitive match
            if target.lower() in self._terms:
                docname, labelid = self._terms[target.lower()]
                return make_refnode(builder, fromdocname, docname, labelid, contnode)
            else:
                return None

    def _resolve_obj_xref(self, env: BuildEnvironment, fromdocname: str,
                          builder: Builder, typ: str, target: str,
                          node: pending_xref, contnode: Element) -> Element | None:
        objtypes = self.objtypes_for_role(typ) or []
        for objtype in objtypes:
            if (objtype, target) in self.objects:
                docname, labelid = self.objects[objtype, target]
                break
        else:
            docname, labelid = '', ''
        if not docname:
            return None
        return make_refnode(builder, fromdocname, docname,
                            labelid, contnode)

    def resolve_any_xref(self, env: BuildEnvironment, fromdocname: str,
                         builder: Builder, target: str, node: pending_xref,
                         contnode: Element) -> list[tuple[str, Element]]:
        results: list[tuple[str, Element]] = []
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
            if key in self.objects:
                docname, labelid = self.objects[key]
                role = 'std:' + self.role_for_objtype(objtype)  # type: ignore[operator]
                results.append((role, make_refnode(builder, fromdocname, docname,
                                                   labelid, contnode)))
        return results

    def get_objects(self) -> Iterator[tuple[str, str, str, str, str, int]]:
        # handle the special 'doc' reference here
        for doc in self.env.all_docs:
            yield (doc, clean_astext(self.env.titles[doc]), 'doc', doc, '', -1)
        for (prog, option), info in self.progoptions.items():
            if prog:
                fullname = ".".join([prog, option])
                yield (fullname, fullname, 'cmdoption', info[0], info[1], 1)
            else:
                yield (option, option, 'cmdoption', info[0], info[1], 1)
        for (type, name), info in self.objects.items():
            yield (name, name, type, info[0], info[1],
                   self.object_types[type].attrs['searchprio'])
        for name, (docname, labelid, sectionname) in self.labels.items():
            yield (name, sectionname, 'label', docname, labelid, -1)
        # add anonymous-only labels as well
        non_anon_labels = set(self.labels)
        for name, (docname, labelid) in self.anonlabels.items():
            if name not in non_anon_labels:
                yield (name, name, 'label', docname, labelid, -1)

    def get_type_name(self, type: ObjType, primary: bool = False) -> str:
        # never prepend "Default"
        return type.lname

    def is_enumerable_node(self, node: Node) -> bool:
        return node.__class__ in self.enumerable_nodes

    def get_numfig_title(self, node: Node) -> str | None:
        """Get the title of enumerable nodes to refer them using its title"""
        if self.is_enumerable_node(node):
            elem = cast(Element, node)
            _, title_getter = self.enumerable_nodes.get(elem.__class__, (None, None))
            if title_getter:
                return title_getter(elem)
            else:
                for subnode in elem:
                    if isinstance(subnode, (nodes.caption, nodes.title)):
                        return clean_astext(subnode)

        return None

    def get_enumerable_node_type(self, node: Node) -> str | None:
        """Get type of enumerable nodes."""
        def has_child(node: Element, cls: type) -> bool:
            return any(isinstance(child, cls) for child in node)

        if isinstance(node, nodes.section):
            return 'section'
        elif (isinstance(node, nodes.container) and
              'literal_block' in node and
              has_child(node, nodes.literal_block)):
            # given node is a code-block having caption
            return 'code-block'
        else:
            figtype, _ = self.enumerable_nodes.get(node.__class__, (None, None))
            return figtype

    def get_fignumber(
        self,
        env: BuildEnvironment,
        builder: Builder,
        figtype: str,
        docname: str,
        target_node: Element,
    ) -> tuple[int, ...] | None:
        if figtype == 'section':
            if builder.name == 'latex':
                return ()
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
            except (KeyError, IndexError) as exc:
                # target_node is found, but fignumber is not assigned.
                # Maybe it is defined in orphaned document.
                raise ValueError from exc

    def get_full_qualified_name(self, node: Element) -> str | None:
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


def warn_missing_reference(app: Sphinx, domain: Domain, node: pending_xref,
                           ) -> bool | None:
    if (domain and domain.name != 'std') or node['reftype'] != 'ref':
        return None
    else:
        target = node['reftarget']
        if target not in domain.anonlabels:  # type: ignore[attr-defined]
            msg = __('undefined label: %r')
        else:
            msg = __('Failed to create a cross reference. A title or caption not found: %r')

        logger.warning(msg % target, location=node, type='ref', subtype=node['reftype'])
        return True


def setup(app: Sphinx) -> dict[str, Any]:
    app.add_domain(StandardDomain)
    app.connect('warn-missing-reference', warn_missing_reference)

    return {
        'version': 'builtin',
        'env_version': 2,
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
